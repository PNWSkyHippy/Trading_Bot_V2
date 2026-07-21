"""
DecentClone/exploration_api.py
================================
Tiny backend for Astral Drift's HUD exploration fog: per-player, per-map
"which tunnel segments have you flown through" state, persisted server-side
instead of browser localStorage.

Storage is encrypted at rest (Fernet — same primitive already used in this
repo for .env API keys) rather than plain JSON, for two reasons:
  1. Confidentiality isn't really the point (this is fog-of-war progress,
     not a secret) — but an unreadable blob removes the temptation to pop
     the DB open in a SQLite browser and hand-edit "explored" to 100%.
  2. Fernet is authenticated encryption: any byte-level tampering with the
     stored blob fails decryption outright (InvalidToken), so corruption
     and tampering are caught the same way, for free.

Player identity: a client-generated UUID stored in the browser (see
index.html's ASTRAL_PLAYER_ID_KEY), not a real account system. This game
has no auth anywhere else either — this matches its existing trust model
(advisory/hobby project, not handling money or PII).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Dict, Tuple

from cryptography.fernet import Fernet, InvalidToken
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

logger = logging.getLogger("exploration_api")
logging.basicConfig(level=logging.INFO)

DATA_DIR = Path(__file__).with_name("data")
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "exploration.db"
KEY_PATH = DATA_DIR / "exploration_secret.key"

# Hard caps so a malicious/buggy client can't inflate a row (or the DB)
# without bound. Real maps top out in the low thousands of segments.
MAX_SEGMENTS_PER_REQUEST = 4000
MAX_KEY_LEN = 160


def _load_or_create_key() -> bytes:
    if KEY_PATH.exists():
        return KEY_PATH.read_bytes()
    key = Fernet.generate_key()
    KEY_PATH.write_bytes(key)
    logger.info("Generated new exploration encryption key at %s", KEY_PATH)
    return key


_fernet = Fernet(_load_or_create_key())


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS player_exploration (
            player_id TEXT NOT NULL,
            map_id TEXT NOT NULL,
            encrypted_blob BLOB NOT NULL,
            updated_at REAL NOT NULL,
            PRIMARY KEY (player_id, map_id)
        )
        """
    )
    return conn


def _encrypt_segments(segments: Dict[str, Tuple[float, float]]) -> bytes:
    canonical = json.dumps(segments, sort_keys=True, separators=(",", ":"))
    return _fernet.encrypt(canonical.encode("utf-8"))


def _decrypt_segments(blob: bytes, player_id: str, map_id: str) -> Dict[str, Tuple[float, float]]:
    try:
        raw = _fernet.decrypt(blob)
    except InvalidToken:
        # Tampered or corrupted row. Monitoring-only for now (per project
        # decision): log it, treat as empty rather than hard-failing the
        # request — the player just loses that map's fog progress and
        # starts re-revealing it, no crash, no exploit payoff either way.
        logger.warning(
            "Exploration blob failed integrity check — treating as empty "
            "(player_id=%s, map_id=%s)", player_id, map_id,
        )
        return {}
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning(
            "Exploration blob decrypted but was not valid JSON — treating "
            "as empty (player_id=%s, map_id=%s)", player_id, map_id,
        )
        return {}
    return _sanitize_segments(parsed)


def _sanitize_segments(raw: dict) -> Dict[str, Tuple[float, float]]:
    clean: Dict[str, Tuple[float, float]] = {}
    if not isinstance(raw, dict):
        return clean
    for key, value in raw.items():
        if not isinstance(key, str) or len(key) > MAX_KEY_LEN:
            continue
        if not isinstance(value, (list, tuple)) or len(value) < 2:
            continue
        try:
            lo = float(value[0])
            hi = float(value[1])
        except (TypeError, ValueError):
            continue
        if not (lo == lo and hi == hi):  # NaN check
            continue
        lo = max(0.0, min(1.0, lo))
        hi = max(0.0, min(1.0, hi))
        clean[key] = (min(lo, hi), max(lo, hi))
        if len(clean) >= MAX_SEGMENTS_PER_REQUEST:
            break
    return clean


def _merge_segments(
    existing: Dict[str, Tuple[float, float]],
    incoming: Dict[str, Tuple[float, float]],
) -> Dict[str, Tuple[float, float]]:
    """Union-only merge — explored intervals can only grow, never shrink.
    Blocks a tampered/replayed client submission from erasing legitimately
    earned progress."""
    merged = dict(existing)
    for key, (lo, hi) in incoming.items():
        if key in merged:
            old_lo, old_hi = merged[key]
            merged[key] = (min(old_lo, lo), max(old_hi, hi))
        else:
            merged[key] = (lo, hi)
        if len(merged) >= MAX_SEGMENTS_PER_REQUEST:
            break
    return merged


class ExplorationPayload(BaseModel):
    segments: Dict[str, Tuple[float, float]]

    @field_validator("segments")
    @classmethod
    def _cap_size(cls, value):
        if len(value) > MAX_SEGMENTS_PER_REQUEST:
            raise ValueError(f"too many segments (max {MAX_SEGMENTS_PER_REQUEST})")
        return value


app = FastAPI(title="Astral Drift Exploration API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _valid_id(value: str) -> bool:
    return bool(value) and len(value) <= 128


@app.get("/exploration/{player_id}/{map_id}")
def get_exploration(player_id: str, map_id: str):
    if not _valid_id(player_id) or not _valid_id(map_id):
        raise HTTPException(status_code=400, detail="invalid id")
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT encrypted_blob FROM player_exploration WHERE player_id = ? AND map_id = ?",
            (player_id, map_id),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return {"segments": {}}
    segments = _decrypt_segments(row[0], player_id, map_id)
    return {"segments": segments}


@app.post("/exploration/{player_id}/{map_id}")
def post_exploration(player_id: str, map_id: str, payload: ExplorationPayload):
    if not _valid_id(player_id) or not _valid_id(map_id):
        raise HTTPException(status_code=400, detail="invalid id")
    incoming = _sanitize_segments(payload.segments)

    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT encrypted_blob FROM player_exploration WHERE player_id = ? AND map_id = ?",
            (player_id, map_id),
        ).fetchone()
        existing = _decrypt_segments(row[0], player_id, map_id) if row else {}
        merged = _merge_segments(existing, incoming)
        encrypted = _encrypt_segments(merged)
        conn.execute(
            """
            INSERT INTO player_exploration (player_id, map_id, encrypted_blob, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(player_id, map_id) DO UPDATE SET
                encrypted_blob = excluded.encrypted_blob,
                updated_at = excluded.updated_at
            """,
            (player_id, map_id, encrypted, time.time()),
        )
        conn.commit()
    finally:
        conn.close()
    return {"segments": merged}


@app.get("/exploration/health")
def health():
    return {"ok": True}
