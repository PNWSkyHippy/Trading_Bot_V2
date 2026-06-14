"""
Shared DB-backed controls for receiver/event scanners.

These are not StrategyEngine strategies, but they create trades through the
breakout receiver. Keep their enable flags separate so stats and controls do
not collapse into one "breakout_scanner" bucket.
"""

from __future__ import annotations

from typing import Dict, List

from data.database import db


SCANNER_CONTROLS: Dict[str, Dict[str, str]] = {
    "breakout_scanner": {
        "key": "breakout_scanner_enabled",
        "label": "Breakout Scanner",
    },
    "funding_scanner": {
        "key": "scanner_funding_scanner_enabled",
        "label": "Funding Scanner",
    },
    "gap_scanner": {
        "key": "scanner_gap_scanner_enabled",
        "label": "Gap Scanner",
    },
    "nr7_scanner": {
        "key": "scanner_nr7_scanner_enabled",
        "label": "NR7 Scanner",
    },
    "volume_surge": {
        "key": "scanner_volume_surge_enabled",
        "label": "Volume Surge Scanner",
    },
}

SCANNER_NAME_ALIASES = {
    "breakoutscanner": "breakout_scanner",
    "breakout": "breakout_scanner",
    "funding": "funding_scanner",
    "fundingscanner": "funding_scanner",
    "gap": "gap_scanner",
    "gapscanner": "gap_scanner",
    "nr7": "nr7_scanner",
    "nr7scanner": "nr7_scanner",
    "volume": "volume_surge",
    "volume_surge_scanner": "volume_surge",
    "volumesurge": "volume_surge",
}

EVENT_SCANNER_NAME_TO_SOURCE = {
    "FundingScanner": "funding_scanner",
    "GapScanner": "gap_scanner",
    "NR7Scanner": "nr7_scanner",
}


def _state_enabled(value, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {
        "0", "false", "no", "off", "disabled"
    }


def normalize_scanner_name(name: str) -> str:
    raw = str(name or "").strip().lower().replace("-", "_").replace(" ", "_")
    if raw.startswith("strategy_") and raw.endswith("_enabled"):
        raw = raw[len("strategy_"):-len("_enabled")]
    elif raw.startswith("scanner_") and raw.endswith("_enabled"):
        raw = raw[len("scanner_"):-len("_enabled")]
    elif raw.endswith("_enabled"):
        raw = raw[:-len("_enabled")]
    compact = raw.replace("_", "")
    if raw in SCANNER_CONTROLS:
        return raw
    if raw in SCANNER_NAME_ALIASES:
        return SCANNER_NAME_ALIASES[raw]
    return SCANNER_NAME_ALIASES.get(compact, raw)


def scanner_source_from_runtime_name(name: str) -> str:
    return EVENT_SCANNER_NAME_TO_SOURCE.get(str(name or ""), normalize_scanner_name(name))


def scanner_state_key(name: str) -> str:
    source = normalize_scanner_name(name)
    meta = SCANNER_CONTROLS.get(source)
    return meta["key"] if meta else f"scanner_{source}_enabled"


def is_scanner_enabled(name: str, default: bool = True) -> bool:
    key = scanner_state_key(name)
    return _state_enabled(db.get_state(key, default=default), default=default)


def set_scanner_enabled(name: str, enabled: bool) -> str:
    source = normalize_scanner_name(name)
    if source not in SCANNER_CONTROLS:
        known = ", ".join(SCANNER_CONTROLS)
        return f"Scanner '{name}' not found. Available: {known}"
    db.set_state(scanner_state_key(source), bool(enabled))
    state = "enabled" if enabled else "disabled"
    return f"Scanner '{source}' {state}."


def list_scanner_controls() -> List[Dict[str, object]]:
    rows = []
    for source, meta in SCANNER_CONTROLS.items():
        rows.append({
            "name": source,
            "label": meta["label"],
            "key": meta["key"],
            "enabled": is_scanner_enabled(source),
        })
    return rows
