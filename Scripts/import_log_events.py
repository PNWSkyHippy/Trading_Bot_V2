from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "trading_bot.db"
DEFAULT_LOGS = [
    ROOT / "logs" / "bot.log",
    ROOT / "logs" / "scanner_signals.log",
    ROOT / "scanner.log",
    ROOT / "logs" / "watchdog_ibkr.log",
    ROOT / "logs" / "web_dashboard_stderr.log",
    ROOT / "logs" / "web_dashboard_stdout.log",
]

DEFAULT_TERMS = (
    r"BREAKOUT DIRECTION DECISION|BREAKOUT CONTRARIAN|BREAKOUT ADAPTIVE|"
    r"BREAKOUT LOSS-CAP|BREAKOUT FAST-FAIL|PROFIT RATCHET|SCANNER PARTIAL|"
    r"STOP LOSS|TRAILING_STOP|TRAILING STOP|CHECKLIST REJECTED|"
    r"No volume baseline|SHORT BLOCKED|Trade rejected|Executor rejected|"
    r"Trade opened:|\[TRADE OPEN\]|\[TRADE CLOSED\]|Traceback|ERROR|CRITICAL"
)

TS_PATTERNS = [
    re.compile(
        r"(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?)"
    ),
    re.compile(r"^(?P<ts>\d{2}:\d{2}:\d{2})\s+"),
]
SEVERITY_RE = re.compile(r"\[(?P<sev>DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL)\]|\b(?P<sev2>ERROR|CRITICAL|WARNING|WARN)\b")
PAIR_SYMBOL_RE = re.compile(r"\b(?P<sym>[A-Z0-9]{2,16}/USD)\b")
LABELED_SYMBOL_RE = re.compile(
    r"(?:symbol=|Trade opened:|\[TRADE OPEN\]|\[TRADE CLOSED\])\s*(?P<sym>[A-Z0-9./-]{2,20})",
    re.I,
)
STRATEGY_RE = re.compile(r"\b(?P<strat>[a-z][a-z0-9_]*(?:scanner|breakout|fakeout|master|vef|orb|strategy)?)\b")

EVENT_PATTERNS = [
    ("direction_decision", re.compile(r"BREAKOUT DIRECTION DECISION", re.I)),
    ("contrarian_flip", re.compile(r"BREAKOUT CONTRARIAN", re.I)),
    ("adaptive_direction", re.compile(r"BREAKOUT ADAPTIVE", re.I)),
    ("breakout_loss_cap", re.compile(r"BREAKOUT LOSS-CAP", re.I)),
    ("breakout_fast_fail", re.compile(r"BREAKOUT FAST-FAIL", re.I)),
    ("profit_ratchet", re.compile(r"PROFIT RATCHET", re.I)),
    ("scanner_partial", re.compile(r"SCANNER PARTIAL|PARTIAL TP", re.I)),
    ("stop_loss", re.compile(r"STOP LOSS", re.I)),
    ("trailing_stop", re.compile(r"TRAILING[_ ]STOP", re.I)),
    ("checklist_rejected", re.compile(r"CHECKLIST REJECTED", re.I)),
    ("missing_volume", re.compile(r"No volume baseline|volume_spike[=: ]+0", re.I)),
    ("short_blocked", re.compile(r"SHORT BLOCKED", re.I)),
    ("trade_rejected", re.compile(r"Trade rejected|Executor rejected", re.I)),
    ("trade_open", re.compile(r"Trade opened:|\[TRADE OPEN\]", re.I)),
    ("trade_closed", re.compile(r"\[TRADE CLOSED\]|Trade closed:", re.I)),
    ("error", re.compile(r"Traceback|ERROR|CRITICAL|Exception", re.I)),
]


def create_log_events_table(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS log_events (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            event_hash     TEXT UNIQUE NOT NULL,
            timestamp      TEXT,
            source_file    TEXT NOT NULL,
            line_no        INTEGER,
            severity       TEXT,
            event_type     TEXT,
            symbol         TEXT,
            strategy_name  TEXT,
            direction      TEXT,
            decision       TEXT,
            policy         TEXT,
            message        TEXT NOT NULL,
            raw_line       TEXT NOT NULL,
            details_json   TEXT,
            imported_at    TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_log_events_timestamp ON log_events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_log_events_type ON log_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_log_events_symbol ON log_events(symbol);
        CREATE INDEX IF NOT EXISTS idx_log_events_strategy ON log_events(strategy_name);
        CREATE INDEX IF NOT EXISTS idx_log_events_decision ON log_events(decision);
        """
    )


def read_tail(path: Path, tail_mb: float | None) -> str:
    if tail_mb is None:
        return path.read_text(encoding="utf-8", errors="ignore")
    max_bytes = int(tail_mb * 1024 * 1024)
    with path.open("rb") as fh:
        if path.stat().st_size > max_bytes:
            fh.seek(-max_bytes, 2)
        return fh.read().decode("utf-8", errors="ignore")


def parse_timestamp(line: str, default_date: dt.date) -> str | None:
    for pattern in TS_PATTERNS:
        match = pattern.search(line)
        if not match:
            continue
        raw = match.group("ts").replace(",", ".")
        try:
            if len(raw) == 8 and raw.count(":") == 2:
                parsed = dt.datetime.combine(
                    default_date, dt.datetime.strptime(raw, "%H:%M:%S").time()
                )
            else:
                parsed = dt.datetime.fromisoformat(raw.replace(" ", "T"))
            return parsed.isoformat(timespec="seconds")
        except ValueError:
            continue
    return None


def classify_event(line: str) -> str:
    for event_type, pattern in EVENT_PATTERNS:
        if pattern.search(line):
            return event_type
    return "matched_log"


def extract_details(line: str) -> dict[str, Any]:
    details: dict[str, Any] = {}
    decision = re.search(r"\bdecision=(FORWARD|CONTRARIAN)\b", line, re.I)
    policy = re.search(r"\bpolicy=([a-z_]+)\b", line, re.I)
    incoming = re.search(r"\bincoming=(LONG|SHORT)\b", line, re.I)
    source = re.search(r"\bsource=([a-z0-9_]+)\b", line, re.I)
    pnl = re.search(r"P&L\s+([+-]?\d+(?:\.\d+)?)%", line, re.I)
    mfe = re.search(r"\bMFE\s+([+-]?\d+(?:\.\d+)?)%", line, re.I)

    if decision:
        details["decision"] = decision.group(1).lower()
    if policy:
        details["policy"] = policy.group(1).lower()
    if incoming:
        details["incoming_direction"] = incoming.group(1).lower()
    if source:
        details["source"] = source.group(1)
    if pnl:
        details["pnl_pct"] = float(pnl.group(1))
    if mfe:
        details["mfe_pct"] = float(mfe.group(1))
    return details


def extract_symbol(line: str) -> str | None:
    pair = PAIR_SYMBOL_RE.search(line)
    if pair:
        return pair.group("sym")
    labeled = LABELED_SYMBOL_RE.search(line)
    if labeled:
        symbol = labeled.group("sym").strip().upper().strip(":,|")
        if symbol not in {"INFO", "ERROR", "WARN", "WARNING", "DEBUG", "CRITICAL"}:
            return symbol
    return None


def parse_line(path: Path, line_no: int, line: str, default_date: dt.date) -> dict[str, Any]:
    details = extract_details(line)
    sev_match = SEVERITY_RE.search(line)
    strategy = None
    for candidate in ("breakout_scanner", "funding_scanner", "gap_scanner"):
        if candidate in line:
            strategy = candidate
            break

    timestamp = parse_timestamp(line, default_date)
    severity = None
    if sev_match:
        severity = (sev_match.group("sev") or sev_match.group("sev2") or "").upper()
        if severity == "WARN":
            severity = "WARNING"

    event_hash = hashlib.sha1(
        f"{path}|{timestamp}|{line.strip()}".encode("utf-8", errors="ignore")
    ).hexdigest()
    direction = details.get("incoming_direction")
    return {
        "event_hash": event_hash,
        "timestamp": timestamp,
        "source_file": str(path.relative_to(ROOT)),
        "line_no": line_no,
        "severity": severity,
        "event_type": classify_event(line),
        "symbol": extract_symbol(line),
        "strategy_name": strategy,
        "direction": direction,
        "decision": details.get("decision"),
        "policy": details.get("policy"),
        "message": line.strip()[:1000],
        "raw_line": line.rstrip("\n")[:4000],
        "details_json": json.dumps(details, sort_keys=True) if details else None,
        "imported_at": dt.datetime.now().isoformat(timespec="seconds"),
    }


def insert_events(conn: sqlite3.Connection, events: list[dict[str, Any]]) -> int:
    inserted = 0
    for event in events:
        before = conn.total_changes
        conn.execute(
            """
            INSERT OR IGNORE INTO log_events (
                event_hash, timestamp, source_file, line_no, severity, event_type,
                symbol, strategy_name, direction, decision, policy, message,
                raw_line, details_json, imported_at
            ) VALUES (
                :event_hash, :timestamp, :source_file, :line_no, :severity,
                :event_type, :symbol, :strategy_name, :direction, :decision,
                :policy, :message, :raw_line, :details_json, :imported_at
            )
            """,
            event,
        )
        if conn.total_changes > before:
            inserted += 1
    return inserted


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import matching log lines into SQLite log_events for DB Browser filtering."
    )
    parser.add_argument(
        "--terms",
        default=DEFAULT_TERMS,
        help="Regex pattern, e.g. 'term1|term2|term3'.",
    )
    parser.add_argument(
        "--log",
        action="append",
        dest="logs",
        help="Log file path. May be repeated. Defaults to common bot logs.",
    )
    parser.add_argument("--tail-mb", type=float, default=25.0)
    parser.add_argument("--clear", action="store_true", help="Clear log_events first.")
    parser.add_argument("--case-sensitive", action="store_true")
    args = parser.parse_args()

    flags = 0 if args.case_sensitive else re.IGNORECASE
    matcher = re.compile(args.terms, flags)
    paths = [Path(p) for p in args.logs] if args.logs else DEFAULT_LOGS

    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}")

    total_seen = 0
    events: list[dict[str, Any]] = []
    default_date = dt.date.today()
    for path in paths:
        path = path if path.is_absolute() else ROOT / path
        if not path.exists():
            continue
        text = read_tail(path, args.tail_mb)
        for idx, line in enumerate(text.splitlines(), start=1):
            if not matcher.search(line):
                continue
            total_seen += 1
            events.append(parse_line(path, idx, line, default_date))

    with sqlite3.connect(DB_PATH) as conn:
        create_log_events_table(conn)
        if args.clear:
            conn.execute("DELETE FROM log_events")
        inserted = insert_events(conn, events)
        conn.commit()

    print(f"Matched lines: {total_seen}")
    print(f"Inserted new log_events rows: {inserted}")
    print(f"Skipped duplicates: {total_seen - inserted}")
    print(f"Table: log_events in {DB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
