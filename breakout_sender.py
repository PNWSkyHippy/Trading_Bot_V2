"""
breakout_sender.py  (hardened v2)
==================================
Sends validated BreakoutScanner signals to the Trading Bot V2 API server.

Changes from v1:
  - Payload now includes candle OHLC (required by hardened receiver wick check)
  - Tries to extract OHLC from signal.history if not passed as candle_data
  - volume_spike now uses signal.volume_spike (real ratio vs average)
  - Unicode arrows replaced with ASCII for Windows cp1252 compatibility
  - Structured response logging (failure_class aware)
  - TTL-aware: sends UTC ISO timestamp so receiver can compute signal age

Config keys (scanner_config.json):
    bot_api_url         str   e.g. "http://localhost:8181"
    bot_api_key         str   must match BOT_API_KEY in bot's config.py
    bot_min_escalation  int   minimum escalation to send (default: 2)
    bot_enabled         bool  master switch (default: true)
"""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)

DEFAULT_BOT_URL        = "http://localhost:8181"
DEFAULT_MIN_ESCALATION = 2
SEND_TIMEOUT_SEC       = 5
MAX_RETRIES            = 1
RETRY_DELAY_SEC        = 1


class BreakoutSender:
    """
    Sends breakout signals to the Trading Bot API.
    Non-blocking — all sends fire in a background thread.
    """

    def __init__(self, config: dict):
        self._url      = config.get("bot_api_url",        DEFAULT_BOT_URL).rstrip("/")
        self._key      = config.get("bot_api_key",        "")
        self._min_esc  = config.get("bot_min_escalation", DEFAULT_MIN_ESCALATION)
        self._enabled  = config.get("bot_enabled",        True)
        self._session  = requests.Session() if REQUESTS_AVAILABLE else None
        self._last_sent: Dict[str, float] = {}
        self._dedup_sec = 30

        if not REQUESTS_AVAILABLE:
            logger.warning("[SENDER] requests not installed — bot injection disabled")
        elif not self._key:
            logger.warning("[SENDER] bot_api_key not set — bot injection disabled")
        elif self._enabled:
            logger.info(
                f"[SENDER] Bot injection enabled -> {self._url} "
                f"(min escalation: {self._min_esc})"
            )

    @property
    def ready(self) -> bool:
        return REQUESTS_AVAILABLE and bool(self._key) and self._enabled

    def should_send(self, signal, escalation: int) -> bool:
        if not self.ready:
            return False
        if escalation < self._min_esc:
            return False
        last = self._last_sent.get(signal.symbol, 0)
        if time.time() - last < self._dedup_sec:
            return False
        return True

    def send_signal(self, signal, escalation: int, candle_data: dict = None):
        """
        Non-blocking send in background thread.

        signal:      BreakoutSignal from BreakoutScanner
        escalation:  0-3
        candle_data: optional dict {open, high, low, close, rsi, sma200, structural_stop}
                     If not passed, sender will try to extract from signal.history.
        """
        if not self.should_send(signal, escalation):
            return

        self._last_sent[signal.symbol] = time.time()
        payload = self._build_payload(signal, escalation, candle_data)

        t = threading.Thread(
            target=self._send_with_retry,
            args=(payload,),
            daemon=True,
            name=f"sender-{signal.symbol}",
        )
        t.start()

    def _build_payload(self, signal, escalation: int, candle_data: dict = None) -> dict:
        """
        Build the API payload. Tries to populate candle OHLC from:
          1. candle_data dict (explicitly passed)
          2. signal.history (last N bars stored on the signal object)
          3. None (receiver will reject on wick check — scanner needs upgrading)
        """
        cd = candle_data or {}

        direction   = getattr(signal, "direction", "long")
        asset_class = "crypto" if "/" in signal.symbol else "stock"
        broker      = getattr(signal, "broker", "KRAKEN").lower()

        # Try to extract candle OHLC from signal history if not provided
        if not cd and hasattr(signal, "history") and signal.history:
            try:
                last_bar = signal.history[-1]
                cd = {
                    "open":  getattr(last_bar, "open_price", None),
                    "high":  getattr(last_bar, "high",       None),
                    "low":   getattr(last_bar, "low",        None),
                    "close": getattr(last_bar, "price",      None),  # price = close in PriceData
                }
            except Exception:
                pass

        # UTC timestamp for TTL check in receiver
        now_utc = datetime.now(timezone.utc).isoformat()

        payload = {
            # Identity
            "symbol":        signal.symbol,
            "broker":        broker,
            "direction":     direction,
            "asset_class":   asset_class,
            "signal_source": "breakout_scanner",

            # Time
            "timestamp":     now_utc,

            # Price
            "entry_price":   signal.entry_price,
            "current_price": signal.current_price,

            # Move context
            "move_pct":      signal.best_move_pct,
            "best_move_pct": signal.best_move_pct,
            "escalation":    escalation,

            # Quality
            "volume_spike":  getattr(signal, "volume_spike",  0.0),
            "momentum_score":getattr(signal, "momentum_score",0.0),
            "confidence":    getattr(signal, "confidence",    0.7),

            # Candle anatomy (required by hardened wick check)
            "candle_open":  cd.get("open"),
            "candle_high":  cd.get("high"),
            "candle_low":   cd.get("low"),
            "candle_close": cd.get("close"),

            # Optional enrichment
            "rsi":                   cd.get("rsi"),
            "sma200":                cd.get("sma200"),
            "structural_stop_price": cd.get("structural_stop"),
            "market_pct_change":     cd.get("market_pct_change"),
            "pattern":               getattr(signal, "pattern_detected", None),
        }
        return payload

    def _send_with_retry(self, payload: dict):
        """Background thread: send with one retry on timeout."""
        url     = f"{self._url}/api/breakout_signal"
        headers = {"X-Api-Key": self._key, "Content-Type": "application/json"}
        sym     = payload.get("symbol", "?")
        esc     = payload.get("escalation", 0)

        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = self._session.post(
                    url, json=payload, headers=headers,
                    timeout=SEND_TIMEOUT_SEC,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    fc = result.get("failure_class")

                    if result.get("accepted"):
                        logger.info(
                            f"[SENDER] ACCEPTED {sym} esc={esc} "
                            f"trade_id={result.get('trade_id')}"
                        )
                    elif fc == "invalid_payload":
                        logger.warning(
                            f"[SENDER] INVALID PAYLOAD {sym} — "
                            f"{result.get('reason')} (scanner needs to send more fields)"
                        )
                    elif fc == "injection_exception":
                        logger.error(
                            f"[SENDER] INJECTION ERROR {sym} — "
                            f"{result.get('reason')}"
                        )
                    else:
                        logger.info(
                            f"[SENDER] REJECTED {sym} esc={esc} — "
                            f"{result.get('reason')}"
                        )
                    return
                else:
                    logger.warning(
                        f"[SENDER] {sym} HTTP {resp.status_code}: "
                        f"{resp.text[:120]}"
                    )
                    return

            except requests.exceptions.Timeout:
                if attempt < MAX_RETRIES:
                    logger.debug(f"[SENDER] {sym} timeout, retrying...")
                    time.sleep(RETRY_DELAY_SEC)
                else:
                    logger.warning(
                        f"[SENDER] {sym} timed out after {MAX_RETRIES + 1} attempts"
                    )
            except requests.exceptions.ConnectionError:
                logger.debug(f"[SENDER] {sym} bot not reachable at {self._url}")
                return
            except Exception as e:
                logger.warning(f"[SENDER] {sym} send error: {e}")
                return
