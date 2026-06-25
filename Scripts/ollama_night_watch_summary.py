from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IN_JSON = ROOT / "reports" / "night_watch" / "latest_digest.json"
OUT_DIR = ROOT / "reports" / "night_watch"
LATEST_MD = OUT_DIR / "ollama_summary_latest.md"
DEFAULT_MODEL = "llama3:latest"
MAX_DIGEST_CHARS = 2_500


SYSTEM_PROMPT = """You are a local night-watch analyst for Linda's trading bot.

You do not trade. You do not give financial advice. You summarize operational,
logging, monitoring, and software reliability risks from a deterministic digest.

Rules:
- Treat the JSON digest as source of truth for counts.
- Do not invent trades, prices, files, or code changes.
- Separate operational emergencies from ordinary strategy losses.
- Prefer concrete next checks and patch targets.
- If a code patch is needed, describe the likely files/functions, but do not
  write a full diff unless the digest clearly proves the bug.
- Keep the report compact enough to paste into Codex/Claude.
"""


def load_digest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def compact_digest(digest: dict) -> dict:
    logs = digest.get("logs", {})
    db = digest.get("db", {})
    return {
        "generated_at": digest.get("generated_at"),
        "tail_bytes": digest.get("tail_bytes"),
        "findings": digest.get("findings", []),
        "log_counts": logs.get("counts", {}),
        "rejection_reasons": logs.get("rejection_reasons", {}),
        "examples": {
            key: values[:3]
            for key, values in logs.get("examples", {}).items()
            if key in {
                "critical_error",
                "timeout_connection",
                "zero_volume_baseline",
                "trade_open",
                "position_monitor",
                "executor_rejected",
            }
        },
        "strategy_stats_today": db.get("strategy_stats_today", []),
        "open_trade_count": db.get("open_trade_count"),
        "open_trades": db.get("open_trades", [])[:10],
        "asset_counts_today": db.get("asset_counts_today", []),
        "oversized_entries_today": db.get("oversized_entries_today", []),
    }


def build_prompt(digest: dict, max_chars: int) -> str:
    compact = json.dumps(compact_digest(digest), indent=2, default=str)
    if len(compact) > max_chars:
        compact = compact[:max_chars] + "\n...TRUNCATED..."
    return f"""{SYSTEM_PROMPT}

Analyze this deterministic night-watch digest and produce:

1. Executive status: OK / WATCH / ACTION NEEDED
2. Highest priority issues, ordered by operational risk
3. Strategy-performance warnings that may justify disabling or investigating
4. Data-pipeline or logging anomalies that look like bugs
5. Exact next command/check for Linda
6. Small prompt to paste into Codex/Claude if a patch investigation is needed

Digest JSON:
```json
{compact}
```
"""


def installed_ollama_models() -> set[str]:
    exe = shutil.which("ollama")
    if not exe:
        raise RuntimeError("ollama executable not found in PATH")
    proc = subprocess.run(
        [exe, "list"],
        text=True,
        capture_output=True,
        timeout=20,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ollama list failed")
    names: set[str] = set()
    for line in proc.stdout.splitlines()[1:]:
        parts = line.split()
        if not parts:
            continue
        name = parts[0]
        if name.endswith(":cloud"):
            continue
        names.add(name)
        if name.endswith(":latest"):
            names.add(name.removesuffix(":latest"))
    return names


def run_ollama(model: str, prompt: str, timeout: int) -> str:
    exe = shutil.which("ollama")
    if not exe:
        raise RuntimeError("ollama executable not found in PATH")

    local_models = installed_ollama_models()
    if model not in local_models:
        raise RuntimeError(
            f"model {model!r} is not already installed locally; refusing to pull or use cloud"
        )

    proc = subprocess.run(
        [exe, "run", model],
        input=prompt,
        text=True,
        capture_output=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"ollama exited {proc.returncode}")
    return proc.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize the compact night-watch digest with local Ollama."
    )
    parser.add_argument("--input", type=Path, default=IN_JSON)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--max-digest-chars", type=int, default=MAX_DIGEST_CHARS)
    parser.add_argument("--out", type=Path, default=LATEST_MD)
    parser.add_argument("--prompt-out", type=Path, default=OUT_DIR / "ollama_prompt_latest.md")
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Digest not found: {args.input}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    digest = load_digest(args.input)
    prompt = build_prompt(digest, args.max_digest_chars)
    args.prompt_out.write_text(prompt, encoding="utf-8")

    generated_at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        summary = run_ollama(args.model, prompt, args.timeout)
        status = "OK"
    except Exception as exc:
        summary = (
            "Ollama summary failed.\n\n"
            f"Model: {args.model}\n"
            f"Error: {exc}\n\n"
            "The deterministic digest still exists and should be used directly."
        )
        status = "FAILED"

    output = (
        "# Ollama Night Watch Summary\n\n"
        f"- Generated: {generated_at}\n"
        f"- Model: {args.model}\n"
        f"- Status: {status}\n"
        f"- Digest: {args.input}\n\n"
        f"{summary}\n"
    )
    args.out.write_text(output, encoding="utf-8")
    print(f"Ollama night-watch summary: {args.out}")
    return 0 if status == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
