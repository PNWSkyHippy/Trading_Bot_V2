"""
Ron's Market Breakout Scanner
==============================
Scans stocks and crypto for early breakout patterns.

TWO-PHASE DETECTION:
  Phase 1 — WATCHLIST: quiet setup spotted, symbol tracked silently.
  Phase 2 — ALERT:     price actually starts moving in the right direction
                        within the first two scan cycles → THEN alert fires.

Escalating alerts:
  Move >2%  → double beep
  Move >5%  → triple high beep + row flashes orange
  Move >10% → rapid triple beep + row flashes red/white

CSV self-cleaning:
  • Max 500 rows kept
  • DEAD/FADING entries older than 48 h are pruned automatically
  • Each symbol appears only once (latest entry wins)
  • 30-minute per-symbol cooldown before re-alerting

Historical bar data:
  Stocks  → Massive.com REST API (5-min OHLC, no Claude involvement at runtime)
            Falls back to yfinance if massive_api_key is blank.
  Crypto  → Kraken / Coinbase via CCXT (unchanged)

Run:
    python BreakoutScanner.py           # GUI (tkinter) or console fallback
    python BreakoutScanner.py --console # Force console mode
"""

import csv
import json
import logging
import os
import queue
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from datetime import time as dt_time
from enum import Enum
from typing import Any, Dict, List, Optional
from breakout_sender import BreakoutSender


BASE_DIR = Path(__file__).resolve().parent

# ── Optional dependencies ─────────────────────────────────────────────────────
try:
    import requests as _requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import yfinance as yf…