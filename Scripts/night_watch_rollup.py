from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "night_watch"
ARCHIVE_DIR = OUT_DIR / "archive"


def parse_generated_at(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value)


def period_bounds(period: str, now: dt.datetime) -> tuple[dt.datetime, dt.datetime, str]:
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        start = start_of_today - dt.timedelta(days=start_of_today.weekday())
        end = start + dt.timedelta(days=7)
        label = f"week_{start:%Y%m%d}"
    elif period == "month":
        start = start_of_today.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        label = f"month_{start:%Y%m}"
    else:
        raise ValueError(f"Unsupported period: {period}")
    return start, end, label


def iter_archived_digests() -> list[dict[str, Any]]:
    digests: list[dict[str, Any]] = []
    for path in sorted(ARCHIVE_DIR.glob("*/*/digest_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_path"] = str(path.relative_to(ROOT))
            data["_generated"] = parse_generated_at(data["generated_at"])
            digests.append(data)
        except Exception as exc:
            digests.append(
                {
                    "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                    "_generated": dt.datetime.min.replace(tzinfo=dt.timezone.utc),
                    "_path": str(path.relative_to(ROOT)),
                    "findings": [
                        {
                            "severity": "HIGH",
                            "title": "Digest archive read failed",
                            "detail": str(exc),
                        }
                    ],
                    "logs": {"counts": {}},
                    "db": {},
                }
            )
    return digests


def build_rollup(period: str, now: dt.datetime) -> dict[str, Any]:
    start, end, label = period_bounds(period, now)
    digests = [
        item for item in iter_archived_digests()
        if start <= item["_generated"] < end
    ]

    finding_counts: Counter[str] = Counter()
    log_counts: Counter[str] = Counter()
    strategy_days: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "days_seen": set(),
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "total_pnl": 0.0,
            "gross_wins": 0.0,
            "gross_losses": 0.0,
        }
    )
    latest_by_day: dict[str, dict[str, Any]] = {}

    for digest in digests:
        day = digest["_generated"].date().isoformat()
        if day not in latest_by_day or digest["_generated"] > latest_by_day[day]["_generated"]:
            latest_by_day[day] = digest

        for finding in digest.get("findings", []):
            key = f"{finding.get('severity', 'UNKNOWN')}:{finding.get('title', 'Untitled')}"
            finding_counts[key] += 1
        for key, value in digest.get("logs", {}).get("counts", {}).items():
            log_counts[key] += int(value or 0)

    # Use the latest digest from each day so daily trade stats do not get multiplied
    # by every 6-hour snapshot.
    for day, digest in latest_by_day.items():
        for row in digest.get("db", {}).get("strategy_stats_today", []):
            name = row.get("strategy_name") or "unknown"
            bucket = strategy_days[name]
            bucket["days_seen"].add(day)
            bucket["trades"] += int(row.get("trades") or 0)
            bucket["wins"] += int(row.get("wins") or 0)
            bucket["losses"] += int(row.get("losses") or 0)
            bucket["total_pnl"] += float(row.get("total_pnl") or 0)
            bucket["gross_wins"] += float(row.get("gross_wins") or 0)
            bucket["gross_losses"] += float(row.get("gross_losses") or 0)

    strategies = []
    for name, bucket in strategy_days.items():
        trades = bucket["trades"]
        gross_losses = bucket["gross_losses"]
        strategies.append(
            {
                "strategy_name": name,
                "days_seen": len(bucket["days_seen"]),
                "trades": trades,
                "wins": bucket["wins"],
                "losses": bucket["losses"],
                "win_rate_pct": round(bucket["wins"] / trades * 100, 1) if trades else 0,
                "total_pnl": round(bucket["total_pnl"], 2),
                "gross_wins": round(bucket["gross_wins"], 2),
                "gross_losses": round(gross_losses, 2),
                "profit_factor": round(bucket["gross_wins"] / gross_losses, 3)
                if gross_losses
                else None,
            }
        )

    strategies.sort(key=lambda row: row["total_pnl"])
    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "period": period,
        "label": label,
        "start": start.isoformat(timespec="seconds"),
        "end_exclusive": end.isoformat(timespec="seconds"),
        "digest_count": len(digests),
        "days_covered": sorted(latest_by_day),
        "finding_counts": dict(finding_counts.most_common()),
        "log_counts": dict(log_counts.most_common()),
        "strategy_stats": strategies,
        "source_files": [item["_path"] for item in digests[-20:]],
    }


def markdown_rollup(report: dict[str, Any]) -> str:
    lines = [
        f"# Night Watch {report['period'].title()} Rollup",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Window: {report['start']} to {report['end_exclusive']} (exclusive)",
        f"- Archived digests included: {report['digest_count']}",
        f"- Days covered: {', '.join(report['days_covered']) or 'none'}",
        "",
        "## Findings",
    ]
    if report["finding_counts"]:
        for key, count in report["finding_counts"].items():
            lines.append(f"- {key}: {count}")
    else:
        lines.append("- No findings in archived digests for this period.")

    lines.extend(["", "## Strategy Stats"])
    if report["strategy_stats"]:
        for row in report["strategy_stats"]:
            lines.append(
                "- {strategy_name}: days={days_seen} trades={trades} wins={wins} "
                "losses={losses} wr={win_rate_pct}% pnl=${total_pnl} pf={profit_factor}".format(
                    **row
                )
            )
    else:
        lines.append("- No daily strategy stats found in this period.")

    lines.extend(["", "## Log Counts"])
    if report["log_counts"]:
        for key, count in report["log_counts"].items():
            lines.append(f"- {key}: {count}")
    else:
        lines.append("- No log counts found.")

    lines.extend(["", "## Recent Source Files"])
    for path in report["source_files"]:
        lines.append(f"- {path}")
    if not report["source_files"]:
        lines.append("- None.")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build weekly/monthly rollups from archived night-watch digests."
    )
    parser.add_argument("--period", choices=["week", "month"], required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    args = parser.parse_args()

    now = dt.datetime.now().astimezone()
    report = build_rollup(args.period, now)
    json_out = args.json_out or OUT_DIR / f"{args.period}_rollup_latest.json"
    md_out = args.md_out or OUT_DIR / f"{args.period}_rollup_latest.md"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    md_out.write_text(markdown_rollup(report), encoding="utf-8")
    print(f"Night watch {args.period} rollup JSON: {json_out}")
    print(f"Night watch {args.period} rollup MD:   {md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
