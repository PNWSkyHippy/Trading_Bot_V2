from __future__ import annotations

import argparse
import datetime as dt
import difflib
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "QuarterlyHourlyLohScan.md"
LOG_PATHS = [
    ROOT / "logs" / "bot.log",
    ROOT / "logs" / "scanner_signals.log",
    ROOT / "scanner.log",
    ROOT / "logs" / "watchdog_ibkr.log",
    ROOT / "logs" / "web_dashboard_stderr.log",
    ROOT / "logs" / "web_dashboard_stdout.log",
]
MAX_TAIL_BYTES = 2_000_000
MAX_MATCHES_PER_LOG = 40

ISSUE_PATTERNS = [
    re.compile(r"\bCRITICAL\b", re.IGNORECASE),
    re.compile(r"\bERROR\b", re.IGNORECASE),
    re.compile(r"\bTraceback\b", re.IGNORECASE),
    re.compile(r"\bException\b", re.IGNORECASE),
    re.compile(r"\bfailed\b", re.IGNORECASE),
    re.compile(r"\btimeout\b", re.IGNORECASE),
    re.compile(r"\bunreachable\b", re.IGNORECASE),
    re.compile(r"\bconnection refused\b", re.IGNORECASE),
]

NOISY_PATTERNS = [
    re.compile(r"heartbeat", re.IGNORECASE),
    re.compile(r"no signal", re.IGNORECASE),
    re.compile(r"CHECKLIST REJECTED", re.IGNORECASE),
    re.compile(r"\[SENDER\] REJECTED", re.IGNORECASE),
    re.compile(r"\[REENTRY\].*REJECTED", re.IGNORECASE),
    re.compile(r"Refresh complete \u2014 \d+ ok / \d+ failed", re.IGNORECASE),
]


def local_now() -> dt.datetime:
    return dt.datetime.now().astimezone()


def tail_text(path: Path, max_bytes: int = MAX_TAIL_BYTES) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        fh.seek(max(0, size - max_bytes))
        data = fh.read()
    return data.decode("utf-8", errors="replace")


def scan_log(path: Path) -> dict:
    if not path.exists():
        return {
            "path": path,
            "exists": False,
            "size": 0,
            "mtime": None,
            "matches": [f"MISSING LOG: {path.relative_to(ROOT)}"],
        }

    matches: list[str] = []
    text = tail_text(path)
    for line in text.splitlines():
        if any(pattern.search(line) for pattern in ISSUE_PATTERNS):
            if any(pattern.search(line) for pattern in NOISY_PATTERNS):
                continue
            matches.append(line[-500:])
            if len(matches) >= MAX_MATCHES_PER_LOG:
                break

    stat = path.stat()
    return {
        "path": path,
        "exists": True,
        "size": stat.st_size,
        "mtime": dt.datetime.fromtimestamp(stat.st_mtime).astimezone(),
        "matches": matches,
    }


def unresolved_count(report_path: Path) -> int:
    if not report_path.exists():
        return 0
    text = report_path.read_text(encoding="utf-8", errors="replace")
    return len(re.findall(r"\[UNRESOLVED\]", text, flags=re.IGNORECASE))


def changed_code_files() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--", "*.py", "*.ps1"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=20,
        )
    except Exception as exc:
        return [f"git diff unavailable: {exc}"]
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def build_patch_hint(matches: list[str]) -> str:
    if not matches:
        return "No code patch needed from this scan."

    changed_files = changed_code_files()
    if changed_files:
        if len(changed_files) == 1 and changed_files[0].startswith("git diff unavailable:"):
            return changed_files[0]

        bullet_list = "\n".join(f"- `{path}`" for path in changed_files[:20])
        remainder = len(changed_files) - 20
        more = f"\n- ... and {remainder} more" if remainder > 0 else ""
        return (
            "Existing uncommitted Python/PowerShell changes are present. "
            "Review them before applying any new fix. "
            "The quarterly scan no longer inlines the full diff.\n\n"
            f"{bullet_list}{more}"
        )

    example = [
        "--- a/REPLACE_ME.py",
        "+++ b/REPLACE_ME.py",
        "@@",
        "-# failing code path identified by log scan",
        "+# proposed fix goes here after manual review",
    ]
    return (
        "Potential code issue detected, but no safe automatic patch was generated. "
        "Keep this issue unresolved until a human-reviewed diff is added.\n\n"
        "```diff\n"
        + "\n".join(example)
        + "\n```"
    )


def write_report() -> int:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not REPORT_PATH.exists():
        REPORT_PATH.write_text("# Quarterly Hourly Log Scan\n\n", encoding="utf-8")

    now = local_now()
    scans = [scan_log(path) for path in LOG_PATHS]
    all_matches = [
        f"{scan['path'].relative_to(ROOT)}: {match}"
        for scan in scans
        for match in scan["matches"]
    ]
    status = "ISSUES FOUND" if all_matches else "OK"
    unresolved_before = unresolved_count(REPORT_PATH)

    lines = [
        "",
        f"## {now:%Y-%m-%d %H:%M:%S %Z} - {status}",
        "",
        f"- Scan window: last {MAX_TAIL_BYTES:,} bytes per log file",
        f"- Unresolved issue markers before this scan: {unresolved_before}",
        "",
        "### Log Files",
    ]

    for scan in scans:
        rel = scan["path"].relative_to(ROOT)
        if scan["exists"]:
            mtime = scan["mtime"].strftime("%Y-%m-%d %H:%M:%S %Z")
            lines.append(f"- `{rel}` size={scan['size']:,} last_write={mtime} matches={len(scan['matches'])}")
        else:
            lines.append(f"- `{rel}` missing matches={len(scan['matches'])}")

    lines.extend(["", "### Issues"])
    if all_matches:
        for item in all_matches[:120]:
            lines.append(f"- [UNRESOLVED] `{item}`")
    else:
        lines.append("- None found.")

    lines.extend(["", "### Patch Diff For Approval", build_patch_hint(all_matches), ""])
    with REPORT_PATH.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    return 2 if all_matches else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan trading bot logs and append a markdown report.")
    parser.parse_args()
    return write_report()


if __name__ == "__main__":
    raise SystemExit(main())
