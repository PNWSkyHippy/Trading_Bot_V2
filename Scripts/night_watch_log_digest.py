from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "night_watch"
ARCHIVE_DIR = OUT_DIR / "archive"
LATEST_JSON = OUT_DIR / "latest_digest.json"
LATEST_MD = OUT_DIR / "latest_digest.md"
LOG_PATHS = [
    ROOT / "logs" / "bot.log",
    ROOT / "logs" / "scanner_signals.log",
    ROOT / "scanner.log",
    ROOT / "logs" / "watchdog_ibkr.log",
    ROOT / "logs" / "web_dashboard_stderr.log",
    ROOT / "logs" / "web_dashboard_stdout.log",
]
DB_PATH = ROOT / "data" / "trading_bot.db"

DEFAULT_TAIL_BYTES = 5_000_000
MAX_EXAMPLES_PER_BUCKET = 8


PATTERNS = {
    "critical_error": re.compile(
        r"\b(CRITICAL|ERROR|Traceback|Exception|Unhandled|crash)\b",
        re.IGNORECASE,
    ),
    "timeout_connection": re.compile(
        r"\b(timeout|timed out|connection refused|connection reset|unreachable)\b",
        re.IGNORECASE,
    ),
    "zero_volume_baseline": re.compile(
        r"(No volume baseline available|volume_spike[=: ]+0(?:\.0+)?|vol=0\.00x)",
        re.IGNORECASE,
    ),
    "sender_rejected": re.compile(r"\[SENDER\] REJECTED (.+)", re.IGNORECASE),
    "checklist_rejected": re.compile(
        r"CHECKLIST REJECTED\s+([A-Z0-9_./-]+).*?(?:Hard check failed:\s*)?(.+)$",
        re.IGNORECASE,
    ),
    "executor_rejected": re.compile(
        r"(Executor rejected|order rejected|SHORT BLOCKED|Trade rejected)",
        re.IGNORECASE,
    ),
    "position_monitor": re.compile(
        r"(Position monitor started|PM-DBG|PROFIT RATCHET|FAST-FAIL|PARTIAL TP)",
        re.IGNORECASE,
    ),
    "trade_open": re.compile(r"Trade opened:|\[TRADE OPEN\]", re.IGNORECASE),
    "trade_closed": re.compile(r"Trade closed:|\[TRADE CLOSED\]", re.IGNORECASE),
    "manual_command": re.compile(
        r"(close all|close trade|manual close|COMMAND|chat command)",
        re.IGNORECASE,
    ),
    "disabled_activity": re.compile(
        r"(enabled=False|scanner loop idle|Signal suppressed|Bot injection disabled)",
        re.IGNORECASE,
    ),
}

NOISE = [
    re.compile(r"heartbeat", re.IGNORECASE),
    re.compile(r"No signal", re.IGNORECASE),
]


def now_local() -> dt.datetime:
    return dt.datetime.now().astimezone()


def _nth_weekday(year: int, month: int, weekday: int, nth: int) -> dt.date:
    day = dt.date(year, month, 1)
    while day.weekday() != weekday:
        day += dt.timedelta(days=1)
    return day + dt.timedelta(days=7 * (nth - 1))


def _last_weekday(year: int, month: int, weekday: int) -> dt.date:
    if month == 12:
        day = dt.date(year, 12, 31)
    else:
        day = dt.date(year, month + 1, 1) - dt.timedelta(days=1)
    while day.weekday() != weekday:
        day -= dt.timedelta(days=1)
    return day


def _observed_fixed_holiday(year: int, month: int, day: int) -> dt.date:
    holiday = dt.date(year, month, day)
    if holiday.weekday() == 5:
        return holiday - dt.timedelta(days=1)
    if holiday.weekday() == 6:
        return holiday + dt.timedelta(days=1)
    return holiday


def _stock_market_holiday(day: dt.date) -> bool:
    year = day.year
    holidays = {
        _observed_fixed_holiday(year, 1, 1),    # New Year's Day
        _nth_weekday(year, 1, 0, 3),            # MLK Day
        _nth_weekday(year, 2, 0, 3),            # Presidents Day
        _last_weekday(year, 5, 0),              # Memorial Day
        _observed_fixed_holiday(year, 6, 19),   # Juneteenth
        _observed_fixed_holiday(year, 7, 4),    # Independence Day
        _nth_weekday(year, 9, 0, 1),            # Labor Day
        _nth_weekday(year, 11, 3, 4),           # Thanksgiving
        _observed_fixed_holiday(year, 12, 25),  # Christmas
    }

    # Good Friday = two days before Easter Sunday.
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    easter_day = ((h + l - 7 * m + 114) % 31) + 1
    holidays.add(dt.date(year, month, easter_day) - dt.timedelta(days=2))
    return day in holidays


def _stock_market_window_elapsed() -> tuple[bool, str]:
    try:
        from zoneinfo import ZoneInfo
        now_et = dt.datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        now_et = dt.datetime.now().astimezone()

    if now_et.weekday() >= 5:
        return False, "weekend"
    if _stock_market_holiday(now_et.date()):
        return False, "market holiday"
    if now_et.time() < dt.time(10, 30):
        return False, "before 10:30 ET stock-trade check window"
    return True, "stock market window elapsed"


def tail_text(path: Path, max_bytes: int) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        fh.seek(max(0, size - max_bytes))
        data = fh.read()
    return data.decode("utf-8", errors="replace")


def clean_line(line: str) -> str:
    return line.replace("\x1b", "").strip()[-700:]


def bucket_reason(line: str) -> str:
    lowered = line.lower()
    if "no volume baseline" in lowered or "vol=0.00x" in lowered:
        return "missing_volume_baseline"
    if "upper wick" in lowered:
        return "wick_rejection"
    if "volume spike" in lowered and "below" in lowered:
        return "volume_below_minimum"
    if "existing position" in lowered or "already have an open position" in lowered:
        return "existing_position"
    if "cooldown" in lowered:
        return "cooldown"
    if "not in cooldown" in lowered:
        return "cooldown_pass"
    if "price" in lowered and "below min_price" in lowered:
        return "min_price"
    if "reversed" in lowered or "drift" in lowered:
        return "price_reversed_or_drift"
    if "stale" in lowered or "signal fresh" in lowered:
        return "freshness_or_stale"
    if "quote currency" in lowered:
        return "bad_quote_currency"
    if "daily symbol limit" in lowered:
        return "daily_symbol_limit"
    if "concurrent breakouts" in lowered:
        return "concurrent_limit"
    return "other"


def append_example(examples: dict[str, list[str]], key: str, line: str) -> None:
    if len(examples[key]) < MAX_EXAMPLES_PER_BUCKET:
        examples[key].append(clean_line(line))


def scan_logs(max_bytes: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        "files": [],
        "counts": Counter(),
        "rejection_reasons": Counter(),
        "examples": defaultdict(list),
        "last_seen": {},
        "position_monitor_lines": 0,
        "trade_open_lines": 0,
        "trade_closed_lines": 0,
    }

    for path in LOG_PATHS:
        rel = str(path.relative_to(ROOT))
        if not path.exists():
            result["files"].append({"path": rel, "exists": False})
            result["counts"]["missing_log_file"] += 1
            append_example(result["examples"], "missing_log_file", rel)
            continue

        stat = path.stat()
        text = tail_text(path, max_bytes)
        lines = text.splitlines()
        file_info = {
            "path": rel,
            "exists": True,
            "size_bytes": stat.st_size,
            "last_write": dt.datetime.fromtimestamp(stat.st_mtime)
            .astimezone()
            .isoformat(timespec="seconds"),
            "tail_lines": len(lines),
        }
        result["files"].append(file_info)

        for line in lines:
            if not line or any(p.search(line) for p in NOISE):
                continue
            for name, pattern in PATTERNS.items():
                if pattern.search(line):
                    result["counts"][name] += 1
                    result["last_seen"][name] = clean_line(line)
                    append_example(result["examples"], name, line)

            rejected = PATTERNS["checklist_rejected"].search(line)
            if rejected:
                reason = bucket_reason(rejected.group(2))
                result["rejection_reasons"][reason] += 1
                append_example(result["examples"], f"reject_{reason}", line)

            sender_rej = PATTERNS["sender_rejected"].search(line)
            if sender_rej:
                reason = bucket_reason(sender_rej.group(1))
                result["rejection_reasons"][f"sender_{reason}"] += 1

            if PATTERNS["position_monitor"].search(line):
                result["position_monitor_lines"] += 1
            if PATTERNS["trade_open"].search(line):
                result["trade_open_lines"] += 1
            if PATTERNS["trade_closed"].search(line):
                result["trade_closed_lines"] += 1

    result["counts"] = dict(result["counts"])
    result["rejection_reasons"] = dict(result["rejection_reasons"])
    result["examples"] = {k: v for k, v in result["examples"].items()}
    return result


def db_rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def scan_db() -> dict[str, Any]:
    today = dt.date.today().isoformat()
    stock_check_ready, stock_check_reason = _stock_market_window_elapsed()
    if not DB_PATH.exists():
        return {"exists": False, "error": f"missing database {DB_PATH}"}

    try:
        with sqlite3.connect(DB_PATH) as conn:
            open_trades = db_rows(
                conn,
                """
                SELECT symbol, asset_class, direction, strategy_name, broker,
                       entry_time, entry_price, quantity, position_value,
                       stop_loss, take_profit
                FROM trades
                WHERE status='open'
                ORDER BY entry_time DESC
                """,
            )
            strategy_stats = db_rows(
                conn,
                """
                SELECT
                    COALESCE(strategy_name, 'unknown') AS strategy_name,
                    COUNT(*) AS trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) AS losses,
                    ROUND(SUM(COALESCE(pnl, 0)), 2) AS total_pnl,
                    ROUND(SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END), 2) AS gross_wins,
                    ROUND(ABS(SUM(CASE WHEN pnl <= 0 THEN pnl ELSE 0 END)), 2) AS gross_losses
                FROM trades
                WHERE status='closed' AND date(exit_time)=?
                GROUP BY COALESCE(strategy_name, 'unknown')
                ORDER BY total_pnl ASC
                """,
                (today,),
            )
            asset_counts = db_rows(
                conn,
                """
                SELECT asset_class, status, COUNT(*) AS count
                FROM trades
                WHERE date(COALESCE(exit_time, entry_time))=?
                GROUP BY asset_class, status
                """,
                (today,),
            )
            odd_position_sizes = db_rows(
                conn,
                """
                SELECT trade_id, symbol, strategy_name, entry_time, position_value
                FROM trades
                WHERE date(entry_time)=? AND position_value > 2500
                ORDER BY position_value DESC
                LIMIT 20
                """,
                (today,),
            )
            state_flags = db_rows(
                conn,
                """
                SELECT key, value, updated
                FROM bot_state
                WHERE key LIKE '%scanner%enabled%' OR key LIKE 'strategy_%_enabled'
                ORDER BY key
                """,
            )
    except Exception as exc:
        return {"exists": True, "error": str(exc)}

    for row in strategy_stats:
        trades = int(row["trades"] or 0)
        gross_losses = float(row["gross_losses"] or 0)
        gross_wins = float(row["gross_wins"] or 0)
        row["win_rate_pct"] = round((float(row["wins"] or 0) / trades * 100), 1) if trades else 0
        row["profit_factor"] = round(gross_wins / gross_losses, 3) if gross_losses else None

    return {
        "exists": True,
        "today": today,
        "open_trade_count": len(open_trades),
        "open_trades": open_trades[:40],
        "strategy_stats_today": strategy_stats,
        "asset_counts_today": asset_counts,
        "oversized_entries_today": odd_position_sizes,
        "scanner_strategy_flags": state_flags,
        "stock_trade_check_ready": stock_check_ready,
        "stock_trade_check_reason": stock_check_reason,
    }


def build_findings(logs: dict[str, Any], db: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    counts = logs.get("counts", {})

    def add(severity: str, title: str, detail: str, evidence_key: str | None = None):
        finding = {"severity": severity, "title": title, "detail": detail}
        if evidence_key:
            finding["evidence"] = logs.get("examples", {}).get(evidence_key, [])[:5]
        findings.append(finding)

    if counts.get("critical_error", 0):
        add(
            "HIGH",
            "Errors or exceptions in recent logs",
            f"{counts['critical_error']} recent critical/error/exception lines found.",
            "critical_error",
        )
    if counts.get("timeout_connection", 0):
        add(
            "MEDIUM",
            "Timeouts or connection problems",
            f"{counts['timeout_connection']} recent timeout/connection lines found.",
            "timeout_connection",
        )
    if counts.get("zero_volume_baseline", 0):
        add(
            "MEDIUM",
            "Missing or zero volume baseline events",
            f"{counts['zero_volume_baseline']} recent zero-volume/baseline events found.",
            "zero_volume_baseline",
        )
    if logs.get("trade_open_lines", 0) and logs.get("position_monitor_lines", 0) == 0:
        add(
            "HIGH",
            "Trades opened but no position monitor activity seen in scan window",
            "Open trades without monitor logs can mean stops/ratchets are not being managed.",
            "trade_open",
        )
    if db.get("exists") and not db.get("error"):
        stats = db.get("strategy_stats_today", [])
        for row in stats:
            trades = int(row.get("trades") or 0)
            pf = row.get("profit_factor")
            pnl = float(row.get("total_pnl") or 0)
            if trades >= 4 and pnl < -50:
                add(
                    "MEDIUM",
                    f"{row['strategy_name']} is losing today",
                    (
                        f"{trades} trades, win_rate={row['win_rate_pct']}%, "
                        f"pnl=${pnl:.2f}, pf={pf}"
                    ),
                )
            if trades >= 4 and int(row.get("wins") or 0) == 0:
                add(
                    "HIGH",
                    f"{row['strategy_name']} has zero wins today",
                    f"{trades} closed trades and no wins today; consider disabling or investigating.",
                )
        assets = db.get("asset_counts_today", [])
        stock_count = sum(
            int(r.get("count") or 0)
            for r in assets
            if str(r.get("asset_class", "")).lower() == "stock"
        )
        if stock_count == 0 and db.get("stock_trade_check_ready"):
            add(
                "MEDIUM",
                "No stock trades recorded today",
                "DB shows zero stock trades opened/closed today. Check market-hours gate, scanner, reviewer, and broker path.",
            )
        if db.get("oversized_entries_today"):
            add(
                "HIGH",
                "Oversized nominal position entries found",
                f"{len(db['oversized_entries_today'])} entries today exceeded $2,500 nominal position_value.",
            )
    elif db.get("error"):
        add("HIGH", "Database scan failed", db["error"])

    return findings


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Night Watch Digest",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Tail bytes per log: {report['tail_bytes']:,}",
        "",
        "## Findings",
    ]
    findings = report.get("findings", [])
    if not findings:
        lines.append("- No high-signal findings.")
    else:
        for finding in findings:
            lines.append(
                f"- [{finding['severity']}] {finding['title']}: {finding['detail']}"
            )
            for ev in finding.get("evidence", [])[:3]:
                lines.append(f"  - evidence: `{ev}`")

    lines.extend(["", "## Log Counts"])
    for key, value in sorted(report["logs"]["counts"].items()):
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Rejection Reasons"])
    reasons = report["logs"].get("rejection_reasons", {})
    if reasons:
        for key, value in sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- None detected in scan window.")

    lines.extend(["", "## Strategy Stats Today"])
    db = report.get("db", {})
    if db.get("stock_trade_check_ready") is False:
        lines.append(
            f"- Stock no-trade check skipped: {db.get('stock_trade_check_reason')}"
        )
    for row in db.get("strategy_stats_today", []):
        lines.append(
            "- {strategy_name}: trades={trades} wins={wins} losses={losses} "
            "wr={win_rate_pct}% pnl=${total_pnl} pf={profit_factor}".format(**row)
        )
    if not db.get("strategy_stats_today"):
        lines.append("- No closed trades today or DB unavailable.")

    lines.extend(["", "## Open Trades"])
    lines.append(f"- Count: {db.get('open_trade_count', 'unknown')}")
    for row in db.get("open_trades", [])[:15]:
        lines.append(
            "- {symbol} {direction} {strategy_name} value=${position_value} "
            "entry={entry_price} sl={stop_loss} tp={take_profit}".format(**row)
        )

    lines.extend(["", "## Files"])
    for item in report["logs"]["files"]:
        if item.get("exists"):
            lines.append(
                f"- {item['path']} size={item['size_bytes']:,} "
                f"last_write={item['last_write']} tail_lines={item['tail_lines']}"
            )
        else:
            lines.append(f"- {item['path']} missing")

    return "\n".join(lines) + "\n"


def archive_report(report: dict[str, Any], markdown: str) -> tuple[Path, Path]:
    generated = dt.datetime.fromisoformat(report["generated_at"])
    stamp = generated.strftime("%Y%m%d_%H%M%S")
    archive_dir = ARCHIVE_DIR / generated.strftime("%Y") / generated.strftime("%m")
    archive_dir.mkdir(parents=True, exist_ok=True)
    json_path = archive_dir / f"digest_{stamp}.json"
    md_path = archive_dir / f"digest_{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic compact digest from bot logs and DB."
    )
    parser.add_argument("--tail-bytes", type=int, default=DEFAULT_TAIL_BYTES)
    parser.add_argument("--json-out", type=Path, default=LATEST_JSON)
    parser.add_argument("--md-out", type=Path, default=LATEST_MD)
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Also write timestamped digest copies under reports/night_watch/archive.",
    )
    args = parser.parse_args()

    logs = scan_logs(args.tail_bytes)
    db = scan_db()
    report = {
        "generated_at": now_local().isoformat(timespec="seconds"),
        "tail_bytes": args.tail_bytes,
        "logs": logs,
        "db": db,
    }
    report["findings"] = build_findings(logs, db)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    markdown = markdown_report(report)
    args.json_out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    args.md_out.write_text(markdown, encoding="utf-8")

    print(f"Night watch digest JSON: {args.json_out}")
    print(f"Night watch digest MD:   {args.md_out}")
    if args.archive:
        archive_json, archive_md = archive_report(report, markdown)
        print(f"Night watch archive JSON: {archive_json}")
        print(f"Night watch archive MD:   {archive_md}")

    has_high = any(f.get("severity") == "HIGH" for f in report["findings"])
    return 2 if has_high else 0


if __name__ == "__main__":
    raise SystemExit(main())
