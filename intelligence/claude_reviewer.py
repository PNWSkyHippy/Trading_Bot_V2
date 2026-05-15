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

  Level 2 autonomy: Claude can VETO signals but cannot
  INITIATE trades. Bot mechanical execution runs underneath.
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
MASSIVE_TIMEOUT_SEC = (15, 30)   # (connect_timeout, read_timeout) — server is slow to accept
MARKET_BASKET       = ["SPY", "QQQ", "IWM", "DIA"]
SECTOR_ETFS         = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU"]

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
                    "All signals will be SKIPPED (conservative fallback). "
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
        Build a deterministic Massive.com market snapshot first, then feed it
        to Claude.  Claude interprets the supplied facts — it does NOT invent
        market data.  Returns conservative MarketContext on ANY failure.
        """
        # ── Step 1: real market data ─────────────────────────────────────────
        snapshot = self._build_market_snapshot()
        self._market_snapshot = snapshot   # expose for get_status()

        quality_note = (
            "The snapshot data quality is GOOD — base your assessment on these numbers."
            if snapshot["data_quality_ok"] else
            "WARNING: Market data quality is POOR or incomplete — be CONSERVATIVE."
        )

        # ── Step 2: recent bot performance (real stats only) ─────────────────
        bot_stats_block = ""
        try:
            summaries = db.get_daily_summaries(5) or []
            if summaries:
                lines = []
                for s in summaries[-3:]:   # last 3 days
                    lines.append(
                        f"  {s.get('date','?')}: "
                        f"P&L={s.get('pnl',0):+.2f}  "
                        f"trades={s.get('trades',0)}  "
                        f"win_rate={s.get('win_rate',0):.0f}%"
                    )
                bot_stats_block = "BOT RECENT PERFORMANCE (last 3 days):\n" + "\n".join(lines)
        except Exception:
            pass

        prompt = f"""You are a trading bot morning briefing system.
Today is {datetime.now().strftime('%A, %B %d, %Y %H:%M')}.

IMPORTANT RULES:
- Do NOT invent market data, earnings, or events.
- Use ONLY the snapshot below as your factual basis.
- If snapshot data_quality_ok is false, default to conservative settings.
- earnings_today and high_impact_events must remain [] (no real source wired yet).

{quality_note}

MARKET SNAPSHOT (computed from Massive.com data):
  SPY day change  : {snapshot.get('spy_day_change_pct', 'N/A')}%
  QQQ day change  : {snapshot.get('qqq_day_change_pct', 'N/A')}%
  IWM day change  : {snapshot.get('iwm_day_change_pct', 'N/A')}%
  DIA day change  : {snapshot.get('dia_day_change_pct', 'N/A')}%
  SPY 5d change   : {snapshot.get('spy_5d_change_pct', 'N/A')}%
  QQQ 5d change   : {snapshot.get('qqq_5d_change_pct', 'N/A')}%
  IWM 5d change   : {snapshot.get('iwm_5d_change_pct', 'N/A')}%
  DIA 5d change   : {snapshot.get('dia_5d_change_pct', 'N/A')}%
  Breadth up      : {snapshot.get('breadth_up_count', 'N/A')}/4
  Breadth down    : {snapshot.get('breadth_down_count', 'N/A')}/4
  Strongest sector: {snapshot.get('strongest_sector', 'N/A')}
  Weakest sector  : {snapshot.get('weakest_sector', 'N/A')}
  Sector changes  : {json.dumps(snapshot.get('sector_changes', {}))}
  Regime guess    : {snapshot.get('market_regime_guess', 'unknown')}
  Snapshot summary: {snapshot.get('snapshot_summary', '')}

{bot_stats_block}

Interpret the snapshot above and respond with ONLY this JSON (no markdown, no explanation):
{{"allow_trading": true, "conviction_score": 70, "market_sentiment": "BULLISH", \
"breadth_health": "HEALTHY", "top_risk_score": 30, "hot_sectors": ["Technology"], \
"cold_sectors": ["Utilities"], "active_themes": ["momentum"], "high_impact_events": [], \
"earnings_today": [], "max_exposure_pct": 60, "summary": "One sentence grounded in the snapshot."}}

Replace values with your assessment based solely on the snapshot. \
Return ONLY the JSON object."""

        try:
            response = self._call_claude(
                prompt    = prompt,
                timeout   = BRIEFING_TIMEOUT_SEC,
                max_tokens= MAX_TOKENS_BRIEFING
            )
            if response is None:
                return self._safe_context("API call failed or timed out")

            parsed = self._extract_json(response)
            if parsed is None:
                return self._safe_context("Could not parse JSON from briefing response")

            # If snapshot quality was bad, enforce conservative cap regardless of Claude answer
            if not snapshot["data_quality_ok"]:
                parsed["allow_trading"]   = False
                parsed["conviction_score"] = min(int(parsed.get("conviction_score", 0)), 30)
                parsed["max_exposure_pct"] = min(float(parsed.get("max_exposure_pct", 0)), 20.0)

            return MarketContext(
                timestamp         = datetime.now(),
                allow_trading     = bool(parsed.get("allow_trading", False)),
                conviction_score  = int(parsed.get("conviction_score", 0)),
                market_sentiment  = str(parsed.get("market_sentiment", "UNKNOWN")),
                breadth_health    = str(parsed.get("breadth_health", "UNKNOWN")),
                top_risk_score    = int(parsed.get("top_risk_score", 100)),
                hot_sectors       = list(parsed.get("hot_sectors", [])),
                cold_sectors      = list(parsed.get("cold_sectors", [])),
                active_themes     = list(parsed.get("active_themes", [])),
                high_impact_events= [],   # no real source wired — always empty
                earnings_today    = [],   # no real source wired — always empty
                max_exposure_pct  = float(parsed.get("max_exposure_pct", 0)),
                briefing_text     = str(parsed.get("summary", response[:200])),
                error             = False,
            )
        except Exception as e:
            logger.error(f"Morning briefing exception: {e}", exc_info=True)
            return self._safe_context(f"Exception: {e}")

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

    def _build_market_snapshot(self) -> Dict:
        """
        Fetch daily bars for market basket + sector ETFs and compute a
        deterministic snapshot dict.  No AI involved — pure arithmetic.
        Falls back to conservative defaults if Massive is unavailable.
        """
        snap: Dict = {
            "spy_day_change_pct":  None,
            "qqq_day_change_pct":  None,
            "iwm_day_change_pct":  None,
            "dia_day_change_pct":  None,
            "spy_5d_change_pct":   None,
            "qqq_5d_change_pct":   None,
            "iwm_5d_change_pct":   None,
            "dia_5d_change_pct":   None,
            "breadth_up_count":    0,
            "breadth_down_count":  0,
            "strongest_sector":    "N/A",
            "weakest_sector":      "N/A",
            "sector_changes":      {},
            "market_regime_guess": "unknown",
            "data_quality_ok":     False,
            "snapshot_summary":    "No market data available.",
        }

        # ── Fetch market basket via yfinance (free, no rate limit) ───────────
        # Massive.com is reserved for future intraday use — daily bars come from
        # yfinance which handles SPY/QQQ/IWM/DIA reliably with no quota issues.
        basket_data: Dict[str, List[Dict]] = {}
        for sym in MARKET_BASKET:
            bars = self._fetch_yfinance_day_bars(sym, lookback_days=10)
            if bars:
                basket_data[sym] = bars

        # ── Compute basket metrics ────────────────────────────────────────────
        basket_day: Dict[str, Optional[float]] = {}
        basket_5d:  Dict[str, Optional[float]] = {}
        for sym in MARKET_BASKET:
            bars = basket_data.get(sym, [])
            basket_day[sym] = self._day_change_pct(bars)
            basket_5d[sym]  = self._fiveday_change_pct(bars)

        snap["spy_day_change_pct"] = basket_day.get("SPY")
        snap["qqq_day_change_pct"] = basket_day.get("QQQ")
        snap["iwm_day_change_pct"] = basket_day.get("IWM")
        snap["dia_day_change_pct"] = basket_day.get("DIA")
        snap["spy_5d_change_pct"]  = basket_5d.get("SPY")
        snap["qqq_5d_change_pct"]  = basket_5d.get("QQQ")
        snap["iwm_5d_change_pct"]  = basket_5d.get("IWM")
        snap["dia_5d_change_pct"]  = basket_5d.get("DIA")

        basket_available = [sym for sym in MARKET_BASKET if basket_day[sym] is not None]
        snap["breadth_up_count"]   = sum(
            1 for sym in basket_available if (basket_day[sym] or 0) > 0
        )
        snap["breadth_down_count"] = sum(
            1 for sym in basket_available if (basket_day[sym] or 0) < 0
        )

        # ── Fetch sector ETFs via yfinance (free, no rate limit) ─────────────
        # Massive quota is reserved for the 4 main basket indices above.
        sector_changes: Dict[str, float] = {}
        for sym in SECTOR_ETFS:
            bars = self._fetch_yfinance_day_bars(sym, lookback_days=7)
            chg = self._day_change_pct(bars) if bars else None
            if chg is not None:
                sector_changes[sym] = chg
        snap["sector_changes"] = sector_changes

        if sector_changes:
            snap["strongest_sector"] = max(sector_changes, key=sector_changes.get)
            snap["weakest_sector"]   = min(sector_changes, key=sector_changes.get)

        # ── Market regime guess (rule-based, no AI) ───────────────────────────
        spy_chg = basket_day.get("SPY")
        qqq_chg = basket_day.get("QQQ")
        up      = snap["breadth_up_count"]
        down    = snap["breadth_down_count"]

        if spy_chg is not None and qqq_chg is not None:
            if spy_chg > 0 and qqq_chg > 0 and up >= 3:
                regime = "risk_on"
            elif spy_chg < 0 and qqq_chg < 0 and down >= 3:
                regime = "risk_off"
            elif spy_chg < -1.0 and qqq_chg < -1.0:
                regime = "bearish"
            elif spy_chg > 1.0 and qqq_chg > 1.0:
                regime = "bullish"
            else:
                regime = "mixed"
        else:
            regime = "unknown"
        snap["market_regime_guess"] = regime

        # ── Data quality ─────────────────────────────────────────────────────
        # OK if we got at least SPY and QQQ data
        snap["data_quality_ok"] = (
            basket_day.get("SPY") is not None and
            basket_day.get("QQQ") is not None
        )

        # ── Human-readable fact summary (no AI) ──────────────────────────────
        parts = []
        if spy_chg is not None:
            parts.append(f"SPY {spy_chg:+.2f}%")
        if qqq_chg is not None:
            parts.append(f"QQQ {qqq_chg:+.2f}%")
        parts.append(f"breadth {up}/{len(basket_available)} up")
        parts.append(f"regime={regime}")
        if snap["strongest_sector"] != "N/A":
            sc = sector_changes.get(snap["strongest_sector"], 0)
            parts.append(f"lead={snap['strongest_sector']}({sc:+.2f}%)")
        if snap["weakest_sector"] != "N/A":
            wc = sector_changes.get(snap["weakest_sector"], 0)
            parts.append(f"lag={snap['weakest_sector']}({wc:+.2f}%)")
        snap["snapshot_summary"] = " | ".join(parts) if parts else "No data."

        logger.info(f"[SNAPSHOT] {snap['snapshot_summary']}")
        return snap

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
        if snap.get("data_quality_ok"):
            snap_block = (
                f"\nRAW MARKET FACTS (from Massive.com):\n"
                f"  SPY {snap.get('spy_day_change_pct', 'N/A'):+}%  "
                f"QQQ {snap.get('qqq_day_change_pct', 'N/A'):+}%  "
                f"IWM {snap.get('iwm_day_change_pct', 'N/A'):+}%  "
                f"DIA {snap.get('dia_day_change_pct', 'N/A'):+}%\n"
                f"  Breadth: {snap.get('breadth_up_count', 'N/A')}/4 up  "
                f"Regime: {snap.get('market_regime_guess', 'unknown')}  "
                f"Lead sector: {snap.get('strongest_sector', 'N/A')}  "
                f"Lag sector: {snap.get('weakest_sector', 'N/A')}"
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
        matches = re.findall(r'\{.*?\}', text, re.DOTALL)
        for match in matches:
            try:
                parsed = json.loads(match)
                if any(k in parsed for k in (
                    "allow_trading", "decision", "conviction_score"
                )):
                    return parsed
            except json.JSONDecodeError:
                continue
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
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
                f"═══════════════════════════════════════════════════════",
                f"  MORNING BRIEFING  —  {ts}",
                f"  Status: {status}",
                f"═══════════════════════════════════════════════════════",
                f"",
                f"TRADING GATE",
                f"  Stock trading allowed : {'YES' if context.allow_trading else 'NO — blocked'}",
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
                f"───────────────────────────────────────────────────────",
                context.briefing_text if context.briefing_text else "(no summary generated)",
                f"",
                f"═══════════════════════════════════════════════════════",
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
        snap = self._market_snapshot or {}
        return {
            "enabled":          self.enabled,
            "has_briefing":     self._morning_context is not None,
            "briefing_error":   self._morning_context.error if self._morning_context else True,
            "allow_trading":    self._morning_context.allow_trading if self._morning_context else False,
            "conviction":       self._morning_context.conviction_score if self._morning_context else 0,
            "sentiment":        self._morning_context.market_sentiment if self._morning_context else "UNKNOWN",
            "briefing_age_min": (
                int((datetime.now() - self._briefing_time).seconds / 60)
                if self._briefing_time else None
            ),
            # ── Market snapshot (visible in dashboard) ───────────────────────
            "massive_key_set":      bool(self._massive_key),
            "snapshot_quality_ok":  snap.get("data_quality_ok", False),
            "snapshot_regime":      snap.get("market_regime_guess", "unknown"),
            "snapshot_summary":     snap.get("snapshot_summary", ""),
            "spy_day_pct":          snap.get("spy_day_change_pct"),
            "qqq_day_pct":          snap.get("qqq_day_change_pct"),
            "breadth_up":           snap.get("breadth_up_count"),
            "strongest_sector":     snap.get("strongest_sector"),
            "weakest_sector":       snap.get("weakest_sector"),
        }


# ── Singleton ────────────────────────────────────────────────────────────────
claude_reviewer = ClaudeReviewer()
