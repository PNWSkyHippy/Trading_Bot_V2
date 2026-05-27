"""
=============================================================
  CLAUDE AUTONOMOUS SIGNAL REVIEWER
  intelligence/claude_reviewer.py

  Sits between the strategy engine and the trade executor.
  Every signal passes through here before execution.

  Three layers:
    1. Morning Briefing  — market context built once at open
    2. Signal Review     — per-signal approve/reject/skip
    3. Pre-execution     — final position size confirmation

  FALLBACK PHILOSOPHY (non-negotiable):
    Missing a trade costs nothing.
    Executing a bad trade autonomously costs real money.
    Therefore: ANY failure, timeout, or ambiguity = SKIP.
    The only path to APPROVE is an explicit, confident response.

  CRYPTO vs STOCK handling:
    Crypto trades run 24/7 — they bypass the stock market hours
    gate entirely. The morning briefing allow_trading flag only
    applies to stocks. Crypto signals go straight to per-signal
    review regardless of time of day or briefing result.

  Default autonomy: Claude annotates and scores signals as an advisory layer.
  Set config.CLAUDE_REVIEWER_MODE="strict" in the scanner path to let Claude
  veto signals again.
=============================================================
"""

import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List

import requests
from dotenv import load_dotenv

import config
from data.database import db

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
CLAUDE_MODEL         = "claude-haiku-4-5-20251001"  # Haiku — fast and cheap for signal review
REVIEW_TIMEOUT_SEC   = 12
BRIEFING_TIMEOUT_SEC = 30
MAX_TOKENS_REVIEW    = 512
MAX_TOKENS_BRIEFING  = 1024
BRIEFING_CACHE_MIN   = 120

# ── Massive.com market snapshot ───────────────────────────────────────────────
MASSIVE_BASE_URL    = "https://api.massive.com"
MASSIVE_BASE        = MASSIVE_BASE_URL              # alias used by _massive_daily_change
MASSIVE_TIMEOUT_SEC = (15, 30)   # (connect_timeout, read_timeout) — server is slow to accept

BRIEFING_BROAD_TICKERS = ["SPY", "QQQ", "IWM", "DIA", "RSP"]

BRIEFING_SECTOR_TICKERS = {
    "Technology":             "XLK",
    "Semiconductors":         "SMH",
    "Financials":             "XLF",
    "Energy":                 "XLE",
    "Healthcare":             "XLV",
    "Industrials":            "XLI",
    "Consumer Discretionary": "XLY",
    "Consumer Staples":       "XLP",
    "Utilities":              "XLU",
}

BRIEFING_RISK_TICKERS = {
    "HighYield":  "HYG",
    "Treasuries": "TLT",
}

# ── Decision constants ────────────────────────────────────────────────────────
APPROVE = "APPROVE"
REJECT  = "REJECT"
SKIP    = "SKIP"


# ===========================================================================
#  DATA CLASSES
# ===========================================================================

@dataclass
class MarketContext:
    """
    Output of the morning briefing — stored and reused all session.
    All fields default to conservative values so a partial briefing
    failure still produces safe defaults.
    """
    timestamp:          datetime  = field(default_factory=datetime.now)
    allow_trading:      bool      = False
    conviction_score:   int       = 0
    market_sentiment:   str       = "UNKNOWN"
    breadth_health:     str       = "UNKNOWN"
    top_risk_score:     int       = 100
    hot_sectors:        List[str] = field(default_factory=list)
    cold_sectors:       List[str] = field(default_factory=list)
    active_themes:      List[str] = field(default_factory=list)
    high_impact_events: List[str] = field(default_factory=list)
    earnings_today:     List[str] = field(default_factory=list)
    max_exposure_pct:   float     = 0.0
    briefing_text:      str       = ""
    error:              bool      = True


@dataclass
class SignalDecision:
    """Output of per-signal review."""
    decision:           str   = SKIP
    confidence:         int   = 0
    reasoning:          str   = ""
    suggested_size_pct: Optional[float] = None
    warnings:           List[str] = field(default_factory=list)
    elapsed_ms:         int   = 0
    error:              bool  = True


# ===========================================================================
#  CLAUDE REVIEWER
# ===========================================================================

class ClaudeReviewer:
    """
    Autonomous signal review layer using Claude as the intelligence engine.
    Wraps every external call in conservative fallback logic.
    """

    def __init__(self):
        load_dotenv(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
        )
        self._api_key         = config.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY", "")
        self._morning_context: Optional[MarketContext] = None
        self._briefing_time:  Optional[datetime]       = None
        self._market_snapshot: Optional[Dict]          = None
        self._briefing_lock   = threading.Lock()        # prevents concurrent builds

        # ── Massive.com market data session ──────────────────────────────────
        self._massive_key     = self._load_massive_key()
        self._massive_session = self._build_massive_session()
        # Check master enable flag — set CLAUDE_REVIEWER_ENABLED=False in config to
        # disable all API calls without removing the API key from .env
        reviewer_flag = getattr(config, "CLAUDE_REVIEWER_ENABLED", True)
        self.enabled  = bool(self._api_key) and reviewer_flag
        if not reviewer_flag:
            logger.info(
                "ClaudeReviewer: CLAUDE_REVIEWER_ENABLED=False in config — "
                "reviewer disabled. All signals proceed to execution without review."
            )

        if not self.enabled:
            if not self._api_key:
                logger.warning(
                    "ClaudeReviewer: No API key found — reviewer disabled. "
                    "Signals proceed through mechanical execution only. "
                    "Add ANTHROPIC_API_KEY to .env to enable."
                )
            # else: flag=False already logged above — no duplicate warning
        else:
            logger.info("ClaudeReviewer: API key found — reviewer enabled.")

    # =========================================================================
    #  PUBLIC API
    # =========================================================================

    def get_morning_context(self, force_refresh: bool = False) -> MarketContext:
        """
        Build or return cached morning market context.
        NOTE: This is only meaningful for stock trading. Crypto signals
        bypass the allow_trading gate entirely — see review_signal().
        """
        if not self.enabled:
            return self._safe_context("Reviewer disabled — API key missing")

        if (not force_refresh
                and self._morning_context
                and self._briefing_time
                and (datetime.now() - self._briefing_time).total_seconds() < BRIEFING_CACHE_MIN * 60):
            logger.debug("Using cached morning briefing")
            return self._morning_context

        # Lock prevents a second caller from starting a parallel build while the
        # first is still fetching Massive data (which can block 60-80s on backoff).
        with self._briefing_lock:
            # Re-check cache inside the lock — another thread may have just finished
            if (not force_refresh
                    and self._morning_context
                    and self._briefing_time
                    and (datetime.now() - self._briefing_time).total_seconds() < BRIEFING_CACHE_MIN * 60):
                logger.debug("Using cached morning briefing (built while waiting for lock)")
                return self._morning_context

            logger.info("ClaudeReviewer: Building morning market briefing...")
            context = self._run_morning_briefing()
            self._morning_context = context
            self._briefing_time   = datetime.now()
            self._write_briefing_file(context)

        if context.error:
            logger.warning(
                f"Morning briefing failed — stock trading conservatively blocked. "
                f"Crypto trading unaffected. Reason: {context.briefing_text[:100]}"
            )
        else:
            logger.info(
                f"Morning briefing complete: conviction={context.conviction_score} "
                f"sentiment={context.market_sentiment} "
                f"allow_trading={context.allow_trading} "
                f"top_risk={context.top_risk_score}"
            )

        return context

    def review_signal(self, signal, market_context: MarketContext) -> SignalDecision:
        """
        Review a single trading signal. Returns APPROVE, REJECT, or SKIP.

        KEY BEHAVIOUR:
          - Crypto signals (asset_class == 'crypto') run 24/7 and BYPASS
            the allow_trading gate. They go straight to per-signal review.
          - Stock signals respect the morning briefing allow_trading flag.
          - Both asset classes still go through individual signal review.
        """
        start_ms   = int(time.time() * 1000)
        is_crypto  = getattr(signal, "asset_class", "").lower() == "crypto"

        # ── Gate 1: Reviewer must be enabled ─────────────────────────────
        if not self.enabled:
            # Reviewer intentionally disabled — pass through to execution
            return SignalDecision(
                decision=APPROVE,
                reasoning="Reviewer disabled — signal passes through",
                confidence=50,
                error=False,
                elapsed_ms=0
            )

        # ── Gate 2: Morning context error — only blocks stocks ────────────
        # Crypto bypasses this gate entirely — it trades 24/7
        if not is_crypto:
            if market_context.error:
                return SignalDecision(
                    decision=SKIP,
                    reasoning="Morning briefing failed — conservative skip for stocks",
                    error=True,
                    elapsed_ms=int(time.time()*1000) - start_ms
                )

            # ── Gate 3: Stock market trading hours gate ───────────────────
            if not market_context.allow_trading:
                return SignalDecision(
                    decision=SKIP,
                    reasoning=(
                        f"Stock trading blocked by morning briefing: "
                        f"conviction={market_context.conviction_score}, "
                        f"sentiment={market_context.market_sentiment}"
                    ),
                    error=False,
                    elapsed_ms=int(time.time()*1000) - start_ms
                )

        # ── Gate 4: Never trade symbols reporting earnings today ──────────
        # Applies to both stocks and crypto (e.g. exchange tokens)
        symbol = signal.symbol.split("/")[0].split("-")[0]
        if symbol in market_context.earnings_today:
            return SignalDecision(
                decision=REJECT,
                reasoning=f"{symbol} reports earnings today — never trade through earnings",
                confidence=100,
                error=False,
                elapsed_ms=int(time.time()*1000) - start_ms
            )

        # ── Gate 5: Cold sector warning (soft — log only, don't block) ────
        warnings = []
        if not is_crypto and market_context.cold_sectors:
            warnings.append(
                f"Note: cold sectors today: {', '.join(market_context.cold_sectors[:3])}"
            )

        if is_crypto:
            logger.debug(
                f"Crypto signal {signal.symbol} — bypassing market hours gate, "
                f"proceeding to signal review"
            )

        # ── Gate 6: Per-signal Claude review ─────────────────────────────
        decision = self._call_signal_review(signal, market_context, warnings)
        decision.elapsed_ms = int(time.time()*1000) - start_ms

        logger.info(
            f"Signal review: {signal.symbol} {signal.direction} "
            f"[{'CRYPTO' if is_crypto else 'STOCK'}] → "
            f"{decision.decision} (confidence={decision.confidence}, "
            f"{decision.elapsed_ms}ms) | {decision.reasoning[:80]}"
        )

        return decision

    def is_enabled(self) -> bool:
        return self.enabled

    # =========================================================================
    #  MORNING BRIEFING
    # =========================================================================

    def _run_morning_briefing(self) -> MarketContext:
        """
        Build a morning briefing from real market data, then let Claude
        classify it conservatively into our MarketContext schema.
        Claude interprets supplied facts — it does NOT invent market data.
        """
        capital_rec = None
        capital     = 0
        try:
            capital_rec = db.get_latest_capital()
            capital     = capital_rec["total_capital"] if capital_rec else 0
        except Exception:
            pass

        snapshot = self._build_market_snapshot()
        self._market_snapshot = snapshot   # expose for get_status() / signal review

        if not snapshot or not snapshot.get("broad"):
            return self._safe_context("Market snapshot unavailable — no data returned")

        snapshot_text = self._market_snapshot_text(snapshot)

        prompt = f"""You are a trading bot morning briefing system.

CRITICAL RULES:
- Use ONLY the structured market data provided below.
- Do NOT use outside knowledge, memory, or assumed live news.
- Do NOT invent earnings, events, sectors, or headlines.
- If earnings/event data is not explicitly provided, return empty arrays [].
- If the snapshot is mixed or unclear, be conservative.
- Your job is to classify the provided data, not to guess the world.

TODAY:
- date: {datetime.now().strftime('%A, %B %d, %Y')}
- current_capital: {capital}

STRUCTURED MARKET DATA:
{snapshot_text}

RETURN ONLY THIS JSON OBJECT:
{{
  "allow_trading": true,
  "conviction_score": 70,
  "market_sentiment": "BULLISH",
  "breadth_health": "HEALTHY",
  "top_risk_score": 30,
  "hot_sectors": ["Technology"],
  "cold_sectors": ["Utilities"],
  "active_themes": ["AI"],
  "high_impact_events": [],
  "earnings_today": [],
  "max_exposure_pct": 60,
  "summary": "One short summary sentence based only on the provided data."
}}

FIELD RULES:
- market_sentiment must be one of: BULLISH, BEARISH, NEUTRAL, UNKNOWN
- breadth_health must be one of: HEALTHY, MIXED, WEAK, UNKNOWN
- conviction_score must be 0-100
- top_risk_score must be 0-100
- max_exposure_pct must be 0-100
- high_impact_events MUST be [] unless explicit event data is provided
- earnings_today MUST be [] unless explicit earnings data is provided

Return ONLY JSON. No markdown. No prose. No code fences."""

        try:
            response = self._call_claude(
                prompt    = prompt,
                timeout   = BRIEFING_TIMEOUT_SEC,
                max_tokens= MAX_TOKENS_BRIEFING
            )
            if response is None:
                return self._safe_context("Claude briefing call failed or timed out")

            parsed = self._extract_json(response)
            if parsed is None:
                return self._safe_context("Could not parse JSON from morning briefing response")

            return MarketContext(
                timestamp          = datetime.now(),
                allow_trading      = bool(parsed.get("allow_trading", False)),
                conviction_score   = int(parsed.get("conviction_score", 0)),
                market_sentiment   = str(parsed.get("market_sentiment", "UNKNOWN")).upper(),
                breadth_health     = str(parsed.get("breadth_health", "UNKNOWN")).upper(),
                top_risk_score     = int(parsed.get("top_risk_score", 100)),
                hot_sectors        = list(parsed.get("hot_sectors", [])),
                cold_sectors       = list(parsed.get("cold_sectors", [])),
                active_themes      = list(parsed.get("active_themes", [])),
                high_impact_events = list(parsed.get("high_impact_events", [])),
                earnings_today     = [s.upper() for s in parsed.get("earnings_today", [])],
                max_exposure_pct   = float(parsed.get("max_exposure_pct", 0)),
                briefing_text      = str(parsed.get("summary", response[:200])),
                error              = False,
            )
        except Exception as e:
            logger.error(f"Morning briefing exception: {e}", exc_info=True)
            return self._safe_context(f"Morning briefing exception: {e}")

    # =========================================================================
    #  MASSIVE.COM MARKET SNAPSHOT
    # =========================================================================

    def _load_massive_key(self) -> str:
        """
        Load Massive.com API key.
        Priority: config attribute → env var → scanner_config.json.
        Keys may be Fernet-encrypted (start with 'gAAAAA') — decrypted automatically.
        """
        def _maybe_decrypt(raw: str) -> str:
            """Strip whitespace; decrypt Fernet token if present."""
            val = (raw or "").strip()
            if not val:
                return ""
            if not val.startswith("gAAAAA"):
                return val  # plaintext
            try:
                from cryptography.fernet import Fernet
                import keyring
                fernet_raw = keyring.get_password("trading_bot_v2", "fernet_key")
                if not fernet_raw:
                    logger.warning("Massive key is encrypted but Fernet key not in Credential Manager")
                    return ""
                return Fernet(fernet_raw.encode()).decrypt(val.encode()).decode().strip()
            except Exception as e:
                logger.warning(f"Failed to decrypt Massive API key: {e}")
                return ""

        # 1. config.py attribute — already decrypted by config._decrypt()
        key = getattr(config, "MASSIVE_API_KEY", "") or ""
        if key:
            return key
        # 2. environment variable
        key = os.getenv("MASSIVE_API_KEY", "")
        if key:
            return _maybe_decrypt(key)
        # 3. scanner_config.json — canonical location; may be encrypted
        try:
            cfg_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), '..', 'scanner_config.json'
            )
            with open(cfg_path, "r") as f:
                data = json.load(f)
            raw = data.get("massive_api_key", "")
            return _maybe_decrypt(raw)
        except Exception:
            return ""

    def _build_massive_session(self) -> Optional[requests.Session]:
        if not self._massive_key:
            logger.info("ClaudeReviewer: No Massive API key — market snapshot will be empty")
            return None
        sess = requests.Session()
        sess.headers.update({
            "Authorization": f"Bearer {self._massive_key}",
            "Accept":        "application/json",
        })
        logger.info("ClaudeReviewer: Massive.com session initialised for market snapshots")
        return sess

    def _fetch_massive_bars(self, symbol: str,
                            multiplier: int = 1,
                            timespan: str   = "day",
                            lookback_days: int = 7) -> List[Dict]:
        """
        Fetch aggregate bars from Massive.com.
        Returns list of dicts: {open, high, low, close, volume, date_str}
        sorted ascending.  Returns [] on any failure.

        Rate limit: Massive free tier is ~5 req/min.  We sleep 13s before
        every call so 4 basket symbols take ~52s total and stay under the cap.
        On 429 we back off 65s and retry once before giving up.
        """
        if not self._massive_session:
            return []
        # 13s between requests keeps 4 basket symbols under the 5/min free cap
        time.sleep(13)
        return self._do_massive_fetch(symbol, multiplier, timespan, lookback_days)

    def _do_massive_fetch(self, symbol: str,
                          multiplier: int,
                          timespan: str,
                          lookback_days: int,
                          _retry: bool = True) -> List[Dict]:
        """Inner fetch — separated so retry can call without re-sleeping."""
        try:
            to_date   = datetime.now().strftime("%Y-%m-%d")
            from_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
            url = (
                f"{MASSIVE_BASE_URL}/v2/aggs/ticker/{symbol}"
                f"/range/{multiplier}/{timespan}/{from_date}/{to_date}"
            )
            resp = self._massive_session.get(
                url,
                params={"adjusted": "true", "sort": "asc", "limit": 50},
                timeout=MASSIVE_TIMEOUT_SEC,
            )
            if resp.status_code == 429:
                if _retry:
                    logger.warning(f"[Massive] {symbol} 429 — backing off 65s then retrying once")
                    time.sleep(65)
                    return self._do_massive_fetch(symbol, multiplier, timespan,
                                                  lookback_days, _retry=False)
                logger.warning(f"[Massive] {symbol} 429 on retry — giving up")
                return []
            if resp.status_code == 403:
                logger.warning(f"[Massive] 403 Not Authorized for {symbol} — check API key/plan")
                return []
            if resp.status_code != 200:
                logger.warning(f"[Massive] {symbol} HTTP {resp.status_code} — body: {resp.text[:120]}")
                return []
            data = resp.json()
            results = data.get("results", [])
            if not results:
                logger.warning(f"[Massive] {symbol} returned 200 but no results — status={data.get('status')} count={data.get('resultsCount',0)}")
            bars = []
            for r in results:
                bars.append({
                    "open":     float(r["o"]),
                    "high":     float(r["h"]),
                    "low":      float(r["l"]),
                    "close":    float(r["c"]),
                    "volume":   float(r.get("v", 0)),
                    "date_str": datetime.fromtimestamp(r["t"] / 1000).strftime("%Y-%m-%d"),
                })
            return bars
        except Exception as e:
            logger.warning(f"[Massive] fetch error {symbol}: {e}")
            return []

    def _massive_daily_change(self, symbol: str, use_massive: bool = True) -> Optional[Dict]:
        """
        Fetch latest daily aggregate data for one symbol.

        use_massive=True  -> try Massive.com first, then fall back to yfinance
        use_massive=False -> skip Massive entirely, use yfinance only

        Returns:
            {symbol, close, prev_close, change_pct, volume}
            or None on total failure.
        """
        # ── Try Massive first only when explicitly allowed ───────────────────
        if use_massive and self._massive_session and self._massive_key:
            try:
                to_date   = datetime.now().strftime("%Y-%m-%d")
                from_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
                url = (
                    f"{MASSIVE_BASE}/v2/aggs/ticker/{symbol}"
                    f"/range/1/day/{from_date}/{to_date}"
                )
                resp = self._massive_session.get(
                    url,
                    params={"adjusted": "true", "sort": "asc", "limit": 10},
                    timeout=MASSIVE_TIMEOUT_SEC,
                )

                if resp.status_code == 429:
                    logger.warning(
                        f"[Massive] {symbol} 429 in morning snapshot — "
                        f"falling back to yfinance"
                    )
                elif resp.status_code == 200:
                    results = (resp.json() or {}).get("results", [])
                    if len(results) >= 2:
                        last       = results[-1]
                        prev       = results[-2]
                        close      = float(last["c"])
                        prev_close = float(prev["c"])
                        volume     = float(last.get("v", 0) or 0)
                        change_pct = ((close - prev_close) / prev_close * 100.0) if prev_close else 0.0
                        return {
                            "symbol":     symbol,
                            "close":      round(close, 4),
                            "prev_close": round(prev_close, 4),
                            "change_pct": round(change_pct, 3),
                            "volume":     volume,
                        }
                    logger.debug(f"[Massive] {symbol} returned <2 bars — falling back to yfinance")
                else:
                    logger.debug(
                        f"[Massive] {symbol} HTTP {resp.status_code} — falling back to yfinance"
                    )
            except Exception as e:
                logger.debug(f"[Massive] {symbol} error ({e}) — falling back to yfinance")

        # ── Fallback / direct path: yfinance ────────────────────────────────
        try:
            bars = self._fetch_yfinance_day_bars(symbol, lookback_days=7)
            if len(bars) >= 2:
                close      = bars[-1]["close"]
                prev_close = bars[-2]["close"]
                volume     = bars[-1].get("volume", 0)
                change_pct = ((close - prev_close) / prev_close * 100.0) if prev_close else 0.0
                return {
                    "symbol":     symbol,
                    "close":      round(close, 4),
                    "prev_close": round(prev_close, 4),
                    "change_pct": round(change_pct, 3),
                    "volume":     volume,
                }
        except Exception as e:
            logger.debug(f"[yfinance] {symbol} error: {e}")

        return None

    def _fetch_yfinance_day_bars(self, symbol: str, lookback_days: int = 7) -> List[Dict]:
        """
        Fetch daily bars via yfinance — used for sector ETFs so Massive quota
        is reserved for the 4 main indices only.
        Returns same dict shape as _fetch_massive_bars (open/high/low/close/volume/date_str).
        """
        try:
            import yfinance as yf
            raw = yf.download(symbol, period=f"{lookback_days + 5}d",
                              interval="1d", progress=False, auto_adjust=True)
            if raw.empty:
                return []
            # Flatten MultiIndex columns (yfinance 0.2.x single-symbol quirk)
            if hasattr(raw.columns, "levels"):
                raw.columns = [c[0] if isinstance(c, tuple) else c for c in raw.columns]
            bars = []
            for ts, row in raw.iterrows():
                try:
                    bars.append({
                        "open":     float(row["Open"]),
                        "high":     float(row["High"]),
                        "low":      float(row["Low"]),
                        "close":    float(row["Close"]),
                        "volume":   float(row.get("Volume", 0)),
                        "date_str": str(ts)[:10],
                    })
                except Exception:
                    continue
            return sorted(bars, key=lambda b: b["date_str"])
        except Exception as e:
            logger.warning(f"[yfinance] fetch error {symbol}: {e}")
            return []

    def _day_change_pct(self, bars: List[Dict]) -> Optional[float]:
        """Day change = latest close vs previous close (last 2 daily bars)."""
        if len(bars) < 2:
            return None
        try:
            prev  = bars[-2]["close"]
            today = bars[-1]["close"]
            if prev <= 0:
                return None
            return round((today - prev) / prev * 100, 2)
        except Exception:
            return None

    def _fiveday_change_pct(self, bars: List[Dict]) -> Optional[float]:
        """5d change = latest close vs earliest close in the fetched window."""
        if len(bars) < 2:
            return None
        try:
            earliest = bars[0]["close"]
            latest   = bars[-1]["close"]
            if earliest <= 0:
                return None
            return round((latest - earliest) / earliest * 100, 2)
        except Exception:
            return None

    def _build_market_snapshot(self) -> Optional[Dict]:
        """
        Build a structured US market snapshot using ETF daily change data.

        Source routing:
          - Broad ETFs (SPY/QQQ/IWM/DIA/RSP): Massive preferred, yfinance fallback
          - Sector ETFs: yfinance only
          - Risk/defensive proxies: yfinance only

        This keeps Massive usage low (5 calls vs 16) while preserving the key
        broad-market read. Returns None if no broad data could be fetched.
        """
        snapshot: Dict = {
            "broad":   {},
            "sectors": {},
            "risk":    {},
            "derived": {},
        }

        # ── Broad market ETFs: Massive preferred ─────────────────────────────
        # Stagger calls by 13s to stay under the free-tier 5 req/min cap.
        # Without this, 5 rapid-fire requests at startup trigger 429 on all of them.
        for i, sym in enumerate(BRIEFING_BROAD_TICKERS):
            if i > 0 and self._massive_session:
                time.sleep(13)
            row = self._massive_daily_change(sym, use_massive=True)
            if row:
                snapshot["broad"][sym] = row

        # ── Sector ETFs: yfinance only (avoid burning Massive quota) ─────────
        for sector_name, sym in BRIEFING_SECTOR_TICKERS.items():
            row = self._massive_daily_change(sym, use_massive=False)
            if row:
                snapshot["sectors"][sector_name] = row

        # ── Risk / defensive proxies: yfinance only ───────────────────────────
        for risk_name, sym in BRIEFING_RISK_TICKERS.items():
            row = self._massive_daily_change(sym, use_massive=False)
            if row:
                snapshot["risk"][risk_name] = row

        # Fail cleanly if we couldn't get any broad data
        if not snapshot["broad"]:
            logger.warning("[SNAPSHOT] No broad market data available — snapshot empty")
            return None

        # ── Derived metrics (rule-based, no AI) ───────────────────────────────
        broad_changes  = [v["change_pct"] for v in snapshot["broad"].values()]
        sector_changes = {
            name: row["change_pct"]
            for name, row in snapshot["sectors"].items()
        }

        broad_avg        = sum(broad_changes) / len(broad_changes) if broad_changes else 0.0
        positive_sectors = sum(1 for v in sector_changes.values() if v > 0)
        negative_sectors = sum(1 for v in sector_changes.values() if v < 0)

        sorted_sectors = sorted(sector_changes.items(), key=lambda x: x[1], reverse=True)
        hot_sectors    = [name for name, _ in sorted_sectors[:3]]
        cold_sectors   = [name for name, _ in sorted_sectors[-3:]]

        spy = snapshot["broad"].get("SPY", {}).get("change_pct")
        rsp = snapshot["broad"].get("RSP", {}).get("change_pct")
        breadth_proxy = round(rsp - spy, 3) if (rsp is not None and spy is not None) else None

        hyg = snapshot["risk"].get("HighYield",  {}).get("change_pct")
        tlt = snapshot["risk"].get("Treasuries", {}).get("change_pct")

        snapshot["derived"] = {
            "broad_avg_pct":              round(broad_avg, 3),
            "positive_sectors":           positive_sectors,
            "negative_sectors":           negative_sectors,
            "breadth_proxy_rsp_minus_spy": breadth_proxy,
            "hot_sectors":                hot_sectors,
            "cold_sectors":               cold_sectors,
            "risk_on_proxy_hyg":          hyg,
            "defensive_proxy_tlt":        tlt,
        }

        # ── Log summary ───────────────────────────────────────────────────────
        qqq = snapshot["broad"].get("QQQ", {}).get("change_pct")
        parts = []
        if spy is not None:
            parts.append(f"SPY {spy:+.2f}%")
        if qqq is not None:
            parts.append(f"QQQ {qqq:+.2f}%")
        parts.append(f"{positive_sectors}/{len(sector_changes)} sectors green")
        if hot_sectors:
            parts.append(f"lead={hot_sectors[0]}")
        if cold_sectors:
            parts.append(f"lag={cold_sectors[-1]}")
        logger.info(f"[SNAPSHOT] {' | '.join(parts) if parts else 'No data.'}")

        return snapshot

    def _market_snapshot_text(self, snapshot: Dict) -> str:
        """
        Compact human-readable block fed to Claude in the morning briefing.
        Converts the structured snapshot dict into labelled lines.
        """
        lines = []

        if snapshot.get("broad"):
            lines.append("BROAD ETFs:")
            for sym, row in snapshot["broad"].items():
                lines.append(
                    f"  - {sym}: close={row['close']}, change={row['change_pct']:+.2f}%"
                )

        if snapshot.get("sectors"):
            lines.append("SECTOR ETFs:")
            for name, row in snapshot["sectors"].items():
                lines.append(
                    f"  - {name} ({row['symbol']}): {row['change_pct']:+.2f}%"
                )

        if snapshot.get("risk"):
            lines.append("RISK / DEFENSIVE PROXIES:")
            for name, row in snapshot["risk"].items():
                lines.append(
                    f"  - {name} ({row['symbol']}): {row['change_pct']:+.2f}%"
                )

        d = snapshot.get("derived", {})
        if d:
            lines.append("DERIVED MARKET METRICS:")
            lines.append(f"  - broad_avg_pct: {d.get('broad_avg_pct')}")
            lines.append(f"  - positive_sectors: {d.get('positive_sectors')}")
            lines.append(f"  - negative_sectors: {d.get('negative_sectors')}")
            lines.append(f"  - breadth_proxy_rsp_minus_spy: {d.get('breadth_proxy_rsp_minus_spy')}")
            lines.append(f"  - hot_sectors: {', '.join(d.get('hot_sectors', [])) or 'none'}")
            lines.append(f"  - cold_sectors: {', '.join(d.get('cold_sectors', [])) or 'none'}")
            lines.append(f"  - risk_on_proxy_hyg: {d.get('risk_on_proxy_hyg')}")
            lines.append(f"  - defensive_proxy_tlt: {d.get('defensive_proxy_tlt')}")

        return "\n".join(lines)

    # =========================================================================
    #  SIGNAL REVIEW
    # =========================================================================

    def _call_signal_review(self, signal, context: MarketContext,
                             warnings: List[str]) -> SignalDecision:
        """
        Ask Claude to approve, reject, or skip a specific trading signal.
        Returns SKIP on ANY failure — never defaults to APPROVE.
        """
        indicators = signal.indicators or {}
        strategy   = indicators.get("strategy_name", "unknown")
        is_crypto  = getattr(signal, "asset_class", "").lower() == "crypto"

        # Build a crypto-aware context note for the prompt
        asset_note = (
            "NOTE: This is a CRYPTOCURRENCY signal. Crypto trades 24/7 — "
            "do NOT factor in stock market hours when reviewing this signal. "
            "Evaluate purely on technical merit and crypto market conditions."
            if is_crypto else
            "This is a STOCK signal during regular market hours."
        )

        # Include raw snapshot facts if available (gives Claude grounded numbers
        # rather than just the interpreted morning-briefing sentiment string)
        snap = self._market_snapshot or {}
        snap_block = ""
        if snap and snap.get("broad"):
            broad   = snap["broad"]
            derived = snap.get("derived", {})
            def _fmt(d, key, default="N/A"):
                v = d.get(key)
                return f"{v:+.2f}" if isinstance(v, (int, float)) else str(default)
            hot  = derived.get("hot_sectors",  [])
            cold = derived.get("cold_sectors", [])
            snap_block = (
                f"\nRAW MARKET FACTS (from market snapshot):\n"
                f"  SPY {_fmt(broad.get('SPY', {}), 'change_pct')}%  "
                f"QQQ {_fmt(broad.get('QQQ', {}), 'change_pct')}%  "
                f"IWM {_fmt(broad.get('IWM', {}), 'change_pct')}%  "
                f"DIA {_fmt(broad.get('DIA', {}), 'change_pct')}%\n"
                f"  Sectors: {derived.get('positive_sectors', 'N/A')} up / "
                f"{derived.get('negative_sectors', 'N/A')} down  "
                f"Hot: {', '.join(hot[:2]) or 'N/A'}  "
                f"Cold: {', '.join(cold[-2:]) or 'N/A'}"
            )

        prompt = f"""You are reviewing a trading signal for an autonomous day trading bot.

{asset_note}

MARKET CONTEXT:
- Sentiment: {context.market_sentiment}
- Conviction: {context.conviction_score}/100
- Breadth: {context.breadth_health}
- Distribution risk: {context.top_risk_score}/100
- Hot sectors: {', '.join(context.hot_sectors) or 'none'}
- Active themes: {', '.join(context.active_themes) or 'none'}
- High impact events: {', '.join(context.high_impact_events) or 'none'}
- Summary: {context.briefing_text}
{snap_block}

SIGNAL:
- Symbol:    {signal.symbol}
- Direction: {signal.direction.upper()}
- Strategy:  {strategy}
- Score:     {signal.score:.3f} (min: {config.MIN_SIGNAL_CONFIDENCE})
- Price:     ${signal.current_price:.4f}
- Asset:     {signal.asset_class}

INDICATORS:
- RSI:          {indicators.get('rsi', 'N/A')}
- MACD hist:    {indicators.get('macd_hist', 'N/A')}
- Volume ratio: {indicators.get('volume_ratio', 'N/A')}
- BB%:          {indicators.get('bb_pct', 'N/A')}

RISK:
- Stop loss:   {config.DEFAULT_STOP_LOSS_PCT}%
- Take profit: {config.DEFAULT_TAKE_PROFIT_PCT}%
- Position:    {config.MAX_POSITION_PCT}% of capital

WARNINGS: {'; '.join(warnings) if warnings else 'none'}

Respond in this EXACT JSON format:
{{"decision": "APPROVE" or "REJECT" or "SKIP", "confidence": 0-100, "reasoning": "one clear sentence", "suggested_size_pct": null or number, "warnings": []}}

RULES:
- APPROVE only if genuinely confident
- REJECT if specific reasons to believe trade will lose
- SKIP if uncertain or missing data
- For crypto: evaluate on technical merit only, ignore stock market hours
- Never APPROVE if market_sentiment is BEARISH and direction is long (stocks only)
- When in doubt: SKIP"""

        try:
            response = self._call_claude(
                prompt    = prompt,
                timeout   = REVIEW_TIMEOUT_SEC,
                max_tokens= MAX_TOKENS_REVIEW
            )

            if response is None:
                return SignalDecision(
                    decision=SKIP,
                    reasoning="API timeout or failure — conservative skip",
                    error=True
                )

            parsed = self._extract_json(response)
            if parsed is None:
                return SignalDecision(
                    decision=SKIP,
                    reasoning="Could not parse Claude response — conservative skip",
                    error=True
                )

            raw_decision = str(parsed.get("decision", "SKIP")).upper()
            if raw_decision not in (APPROVE, REJECT, SKIP):
                return SignalDecision(
                    decision=SKIP,
                    reasoning=f"Unrecognised decision '{raw_decision}' — conservative skip",
                    error=True
                )

            # Safety overrides — stocks only
            if raw_decision == APPROVE and not is_crypto:
                if context.market_sentiment == "BEARISH" and signal.direction == "long":
                    return SignalDecision(
                        decision=REJECT,
                        reasoning="Safety override: bearish market + long stock signal rejected",
                        confidence=90,
                        error=False
                    )
                if context.top_risk_score > 80:
                    return SignalDecision(
                        decision=SKIP,
                        reasoning=f"Safety override: distribution risk {context.top_risk_score}/100 too high",
                        confidence=80,
                        error=False
                    )

            return SignalDecision(
                decision           = raw_decision,
                confidence         = int(parsed.get("confidence", 0)),
                reasoning          = str(parsed.get("reasoning", "")),
                suggested_size_pct = parsed.get("suggested_size_pct"),
                warnings           = list(parsed.get("warnings", [])),
                error              = False,
            )

        except Exception as e:
            logger.error(f"Signal review exception for {signal.symbol}: {e}")
            return SignalDecision(
                decision=SKIP,
                reasoning=f"Exception during review — conservative skip: {e}",
                error=True
            )

    # =========================================================================
    #  CLAUDE API WRAPPER
    # =========================================================================

    def _call_claude(self, prompt: str, timeout: int,
                     max_tokens: int) -> Optional[str]:
        if not self._api_key:
            logger.warning("Claude API call attempted with no API key")
            return None

        try:
            start    = time.time()
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":         self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json",
                },
                json={
                    "model":      CLAUDE_MODEL,
                    "max_tokens": max_tokens,
                    "messages":   [{"role": "user", "content": prompt}],
                },
                timeout=timeout
            )
            elapsed = time.time() - start

            if elapsed > timeout * 0.9:
                logger.warning(
                    f"Claude response was slow ({elapsed:.1f}s) — "
                    f"approaching timeout ({timeout}s)"
                )

            response.raise_for_status()
            data = response.json()
            text = data["content"][0]["text"]
            logger.debug(f"Claude API response ({elapsed:.1f}s): {text[:100]}...")
            return text

        except requests.exceptions.Timeout:
            logger.warning(f"Claude API timed out after {timeout}s — returning None")
            return None
        except requests.exceptions.ConnectionError:
            logger.warning("Claude API connection error — returning None")
            return None
        except requests.exceptions.HTTPError as e:
            try:
                error_body = e.response.json()
                logger.error(f"Claude API HTTP error body: {error_body}")
            except Exception:
                logger.error(f"Claude API HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"Claude API unexpected error: {e}")
            return None

    # =========================================================================
    #  HELPERS
    # =========================================================================

    def _extract_json(self, text: str) -> Optional[Dict]:
        """
        Extract and parse JSON from Claude's response.
        Prefer full-body parse first; fall back to first object match.
        """
        # Try full-body parse first (Claude often returns clean JSON with no prose)
        try:
            parsed = json.loads(text.strip())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Fall back to extracting the first {...} block (handles markdown fences etc.)
        matches = re.findall(r'\{.*\}', text, re.DOTALL)
        for match in matches:
            try:
                parsed = json.loads(match)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

        logger.warning(f"No valid JSON found in Claude response: {text[:200]}")
        return None

    def _write_briefing_file(self, context: MarketContext) -> None:
        """
        Write the morning briefing to a human-readable text file so it can
        be read back by Claude (Haiku) when asked about today's market view.
        File: logs/morning_briefing.txt — overwritten each time briefing runs.
        """
        try:
            logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            path = os.path.join(logs_dir, 'morning_briefing.txt')

            ts = context.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            status = "ERROR — conservative defaults applied" if context.error else "OK"

            lines = [
                f"=======================================================",
                f"  MORNING BRIEFING  -  {ts}",
                f"  Status: {status}",
                f"=======================================================",
                f"",
                f"TRADING GATE",
                f"  Stock trading allowed : {'YES' if context.allow_trading else 'NO - blocked'}",
                f"  Max exposure          : {context.max_exposure_pct:.0f}% of portfolio",
                f"  Conviction score      : {context.conviction_score}/100",
                f"",
                f"MARKET CONDITIONS",
                f"  Sentiment             : {context.market_sentiment}",
                f"  Breadth health        : {context.breadth_health}",
                f"  Top risk score        : {context.top_risk_score}/100",
                f"",
                f"SECTORS",
                f"  Hot (favour longs)    : {', '.join(context.hot_sectors) if context.hot_sectors else 'none'}",
                f"  Cold (avoid/short)    : {', '.join(context.cold_sectors) if context.cold_sectors else 'none'}",
                f"",
                f"THEMES & CATALYSTS",
                f"  Active themes         : {', '.join(context.active_themes) if context.active_themes else 'none'}",
                f"  High-impact events    : {', '.join(context.high_impact_events) if context.high_impact_events else 'none'}",
                f"  Earnings today        : {', '.join(context.earnings_today) if context.earnings_today else 'none'}",
                f"",
                f"NARRATIVE SUMMARY",
                f"-------------------------------------------------------",
                context.briefing_text if context.briefing_text else "(no summary generated)",
                f"",
                f"=======================================================",
            ]

            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            logger.debug(f"Morning briefing written to {path}")

        except Exception as e:
            logger.warning(f"Could not write morning briefing file: {e}")

    def _safe_context(self, reason: str) -> MarketContext:
        """
        Return a conservative MarketContext for error cases.
        allow_trading=False blocks stocks but crypto bypasses this anyway.
        """
        return MarketContext(
            allow_trading    = False,
            conviction_score = 0,
            market_sentiment = "UNKNOWN",
            top_risk_score   = 100,
            max_exposure_pct = 0.0,
            briefing_text    = reason,
            error            = True,
        )

    def get_status(self) -> Dict:
        snap    = self._market_snapshot or {}
        broad   = snap.get("broad",   {})
        derived = snap.get("derived", {})
        hot     = derived.get("hot_sectors",  [])
        cold    = derived.get("cold_sectors", [])

        # Build a quick human-readable snapshot summary
        spy_pct = broad.get("SPY", {}).get("change_pct")
        qqq_pct = broad.get("QQQ", {}).get("change_pct")
        pos_sec = derived.get("positive_sectors")
        snap_summary = ""
        if spy_pct is not None:
            snap_summary += f"SPY {spy_pct:+.2f}%"
        if qqq_pct is not None:
            snap_summary += f"  QQQ {qqq_pct:+.2f}%"
        if pos_sec is not None:
            snap_summary += f"  {pos_sec}/{len(snap.get('sectors', {}))} sectors green"

        return {
            "enabled":          self.enabled,
            "has_briefing":     self._morning_context is not None,
            "briefing_error":   self._morning_context.error if self._morning_context else True,
            "allow_trading":    self._morning_context.allow_trading if self._morning_context else False,
            "conviction":       self._morning_context.conviction_score if self._morning_context else 0,
            "sentiment":        self._morning_context.market_sentiment if self._morning_context else "UNKNOWN",
            "briefing_age_min": (
                int((datetime.now() - self._briefing_time).total_seconds() / 60)
                if self._briefing_time else None
            ),
            # ── Market snapshot (visible in dashboard) ───────────────────────
            "massive_key_set":     bool(self._massive_key),
            "snapshot_quality_ok": bool(broad),
            "snapshot_summary":    snap_summary.strip(),
            "spy_day_pct":         spy_pct,
            "qqq_day_pct":         qqq_pct,
            "breadth_up":          derived.get("positive_sectors"),
            "strongest_sector":    hot[0]   if hot  else "N/A",
            "weakest_sector":      cold[-1] if cold else "N/A",
        }


# ── Singleton ────────────────────────────────────────────────────────────────
claude_reviewer = ClaudeReviewer()
