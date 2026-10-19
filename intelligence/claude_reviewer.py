"""
=============================================================
  CLAUDE AUTONOMOUS SIGNAL REVIEWER  (v2 — tiered rebuild)
  intelligence/claude_reviewer.py

  Architecture (tiered cost control):
    1. _RulesFilter   — pure Python, zero API cost, ~95% rejection
    2. review_batch() — 4-5 signals per Claude call (batched)
    3. Morning briefing — scheduled 10 AM ET, cached 2 hours

  FALLBACK PHILOSOPHY (non-negotiable):
    Any failure, timeout, or ambiguous response → SKIP.
    The only path to APPROVE is explicit, confident response.
    Level 2 autonomy: veto power only, cannot initiate trades.

  Target: 15-25 API calls/day at $0.50-2/day.
=============================================================
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import anthropic

import config

logger = logging.getLogger(__name__)

# ── Model & limits ────────────────────────────────────────────────────────────
CLAUDE_MODEL          = "claude-haiku-5-5"
BATCH_SIZE            = 5
REVIEW_TIMEOUT_SEC    = 15
BRIEFING_TIMEOUT_SEC  = 30
MAX_TOKENS_REVIEW     = 512
MAX_TOKENS_BRIEFING   = 1024
BRIEFING_CACHE_MIN    = 120

# ── Decision constants ────────────────────────────────────────────────────────
APPROVE = "APPROVE"
REJECT  = "REJECT"
SKIP    = "SKIP"

# ── Rules pre-filter thresholds ──────────────────────────────────────────────
RULES_MIN_SCORE      = 0.70
RULES_MIN_VOLUME     = 1.2
RULES_MAX_RSI_LONG   = 78
RULES_MIN_RSI_SHORT  = 22
RULES_MAX_ADX_BLOCK  = 20
RULES_MAX_RISK_SCORE = 80

REVIEW_INDICATOR_KEYS = (
    "rsi",
    "adx",
    "volume_ratio",
    "macd_hist",
    "bb_pct",
    "dist_to_mid_pct",
    "btc_15m_move_pct",
    "btc_momentum_active",
    "move_pct",
    "volume_spike",
    "escalation",
    "pattern",
    "bars_since_breakout",
    "distance_from_breakout_pct",
    "breakout_level",
    "sma20_target",
    "market_condition",
    "condition_scalar",
    "timeframe",
    "structural_stop_price",
    "signal_source",
)


# ===========================================================================
#  STATIC SYSTEM PROMPT — kept constant to enable Anthropic prompt caching
# ===========================================================================

_SYSTEM_PROMPT = (
    "You are the signal-review layer of an autonomous day trading bot. "
    "You have VETO power only — you cannot initiate trades. "
    "Respond with ONLY the JSON shape requested by the user prompt. "
    "No markdown, no explanation, no surrounding text. "
    "For signal-review prompts, each array element corresponds to one signal in the order provided. "
    "For each signal-review item output: "
    "{\"symbol\": \"SYM\", \"decision\": \"APPROVE|REJECT|SKIP\", "
    "\"confidence\": 0-100, \"reasoning\": \"one clear sentence\"}. "
    "Decision rules: "
    "APPROVE — genuinely confident this is a good trade given the market context. "
    "REJECT  — specific evidence this trade will lose (e.g. overbought + resistance, "
    "bearish market + long signal, earnings overhang). "
    "SKIP    — uncertain, missing data, or market is ambiguous. "
    "When in doubt: SKIP. Never APPROVE a long in a BEARISH market. "
    "Never APPROVE during high-impact economic events."
)


# ===========================================================================
#  DATA CLASSES
# ===========================================================================

@dataclass
class MarketContext:
    """Morning briefing output — stored and reused all session."""
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
    decision:           str            = SKIP
    confidence:         int            = 0
    reasoning:          str            = ""
    suggested_size_pct: Optional[float] = None
    warnings:           List[str]      = field(default_factory=list)
    elapsed_ms:         int            = 0
    filtered_by_rules:  bool           = False
    error:              bool           = True


# ===========================================================================
#  RULES PRE-FILTER  — pure Python, zero API cost
# ===========================================================================

class _RulesFilter:
    """
    Hard-blocks signals that fail mechanical criteria.
    Runs before any API call. ~95% rejection rate in normal markets.
    Returns (should_skip: bool, reason: str).
    """

    def evaluate(
        self,
        signal,
        market_context: MarketContext,
    ) -> Tuple[bool, str]:
        ind = signal.indicators or {}
        direction = (signal.direction or "").lower()

        # Score gate
        score = _safe_float(getattr(signal, "score", 0.0), 0.0) or 0.0
        if score < RULES_MIN_SCORE:
            return True, f"score {score:.3f} < minimum {RULES_MIN_SCORE}"

        # ADX flat-market block
        adx = _safe_float(ind.get("adx"))
        if adx is not None and adx <= RULES_MAX_ADX_BLOCK:
            return True, f"ADX {adx:.1f} <= {RULES_MAX_ADX_BLOCK} (no trend)"

        # Volume confirmation
        vol = _safe_float(ind.get("volume_ratio"))
        if vol is not None and vol < RULES_MIN_VOLUME:
            return True, f"volume_ratio {vol:.2f} < {RULES_MIN_VOLUME}"

        # RSI extremes
        rsi = _safe_float(ind.get("rsi"))
        if rsi is not None:
            if direction == "long" and rsi > RULES_MAX_RSI_LONG:
                return True, f"RSI {rsi:.1f} overbought for long (>{RULES_MAX_RSI_LONG})"
            if direction == "short" and rsi < RULES_MIN_RSI_SHORT:
                return True, f"RSI {rsi:.1f} oversold for short (<{RULES_MIN_RSI_SHORT})"

        # Earnings hard-block
        symbol = signal.symbol.split("/")[0].split("-")[0].upper()
        if symbol in market_context.earnings_today:
            return True, f"{symbol} reports earnings today"

        # Bearish market + long signal
        if (market_context.market_sentiment == "BEARISH"
                and direction == "long"):
            return True, "bearish market + long signal"

        # High distribution risk
        if market_context.top_risk_score > RULES_MAX_RISK_SCORE:
            return True, f"top_risk_score {market_context.top_risk_score} > {RULES_MAX_RISK_SCORE}"

        return False, ""


def _safe_float(value, default: Optional[float] = None) -> Optional[float]:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _round_for_prompt(value):
    if isinstance(value, float):
        return round(value, 6)
    return value


def _pct_change(current: float, previous: float) -> Optional[float]:
    try:
        if previous == 0:
            return None
        return ((float(current) - float(previous)) / float(previous)) * 100
    except Exception:
        return None


def _summarize_bars(symbol: str, bars) -> Dict:
    close = bars["close"]
    last_close = float(close.iloc[-1])
    first_close = float(close.iloc[0])
    prev_close = float(close.iloc[-2]) if len(close) >= 2 else first_close
    sma20 = float(close.tail(20).mean()) if len(close) >= 20 else None
    return {
        "symbol": symbol,
        "bars": int(len(bars)),
        "last_timestamp": str(bars.index[-1]),
        "last_close": round(last_close, 4),
        "change_from_first_bar_pct": _round_for_prompt(_pct_change(last_close, first_close)),
        "last_bar_change_pct": _round_for_prompt(_pct_change(last_close, prev_close)),
        "above_sma20": None if sma20 is None else bool(last_close > sma20),
    }


def _fetch_alpha_movers() -> Dict:
    if not getattr(config, "ALPHA_VANTAGE_KEY", ""):
        return {"enabled": False, "reason": "missing_alpha_vantage_key"}

    try:
        import urllib.parse
        import urllib.request

        url = "https://www.alphavantage.co/query?" + urllib.parse.urlencode({
            "function": "TOP_GAINERS_LOSERS",
            "apikey": config.ALPHA_VANTAGE_KEY,
        })
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read(200000))

        if "Note" in data:
            return {"enabled": True, "error": "rate_limit", "message": data["Note"][:200]}
        if "Information" in data:
            return {"enabled": True, "error": "api_message", "message": data["Information"][:200]}
        if "Error Message" in data:
            return {"enabled": True, "error": "api_error", "message": data["Error Message"][:200]}

        def _top(rows):
            output = []
            for row in rows[:5]:
                output.append({
                    "ticker": row.get("ticker", ""),
                    "price": row.get("price", ""),
                    "change_pct": row.get("change_percentage", ""),
                    "volume": row.get("volume", ""),
                })
            return output

        return {
            "enabled": True,
            "last_updated": data.get("last_updated", ""),
            "top_gainers": _top(data.get("top_gainers", [])),
            "top_losers": _top(data.get("top_losers", [])),
            "most_active": _top(data.get("most_actively_traded", [])),
        }
    except Exception as exc:
        return {"enabled": True, "error": type(exc).__name__, "message": str(exc)[:200]}


def _build_market_snapshot() -> Dict:
    snapshot = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "equity_index_proxies": [],
        "market_condition": None,
        "alpha_vantage_movers": None,
        "errors": [],
    }

    try:
        from scanners.market_scanner import StockScanner
        from intelligence.condition_detector import condition_detector

        stock_scanner = StockScanner()
        for symbol in ("SPY", "QQQ", "IWM", "DIA"):
            try:
                bars = stock_scanner.get_bars(symbol, timeframe="5Min", limit=100)
                if bars is None or bars.empty:
                    snapshot["errors"].append(f"{symbol}: no 5Min bars")
                    continue
                snapshot["equity_index_proxies"].append(_summarize_bars(symbol, bars))
            except Exception as exc:
                snapshot["errors"].append(f"{symbol}: {type(exc).__name__}: {exc}")

        try:
            report = condition_detector.get_spy_condition(stock_scanner)
            snapshot["market_condition"] = {
                "condition": report.condition.value,
                "should_trade": bool(report.should_trade),
                "reason": report.reason,
                "adx": report.adx,
                "atr_pct": report.atr_pct,
                "bb_width": report.bb_width,
                "position_scalar": report.position_scalar,
            }
        except Exception as exc:
            snapshot["errors"].append(f"condition_detector: {type(exc).__name__}: {exc}")
    except Exception as exc:
        snapshot["errors"].append(f"stock_snapshot: {type(exc).__name__}: {exc}")

    snapshot["alpha_vantage_movers"] = _fetch_alpha_movers()
    return snapshot


def _compact_signal_payload(signal) -> Dict:
    ind = signal.indicators or {}
    payload = {
        "symbol": getattr(signal, "symbol", ""),
        "direction": getattr(signal, "direction", ""),
        "asset_class": getattr(signal, "asset_class", ""),
        "score": round(_safe_float(getattr(signal, "score", None), 0.0) or 0.0, 4),
        "current_price": _round_for_prompt(getattr(signal, "current_price", None)),
        "strategy": ind.get("strategy_name", getattr(signal, "strategy_name", "unknown")),
        "reason": getattr(signal, "reason", "") or ind.get("reason", ""),
        "stop_loss_pct": _round_for_prompt(getattr(signal, "stop_loss_pct", None)),
        "take_profit_pct": _round_for_prompt(getattr(signal, "take_profit_pct", None)),
        "custom_stop_loss": _round_for_prompt(getattr(signal, "custom_stop_loss", None)),
        "custom_take_profit": _round_for_prompt(getattr(signal, "custom_take_profit", None)),
        "indicators": {},
    }
    for key in REVIEW_INDICATOR_KEYS:
        if key in ind and ind[key] is not None:
            payload["indicators"][key] = _round_for_prompt(ind[key])
    return payload


# ===========================================================================
#  CLAUDE REVIEWER  — tiered rebuild
# ===========================================================================

class ClaudeReviewer:
    """
    Tiered signal review: rules pre-filter → batched Claude call.
    All external calls wrapped in conservative fallback (failure = SKIP).
    """

    def __init__(self):
        self._api_key = config.ANTHROPIC_API_KEY or ""
        self.enabled  = bool(self._api_key)

        self._client: Optional[anthropic.Anthropic] = None
        if self.enabled:
            try:
                self._client = anthropic.Anthropic(api_key=self._api_key)
                logger.info("ClaudeReviewer v2: SDK client initialised (%s)", CLAUDE_MODEL)
            except Exception as exc:
                logger.error("ClaudeReviewer: failed to init SDK client: %s", exc)
                self.enabled = False
        else:
            logger.warning(
                "ClaudeReviewer: no API key — reviewer disabled. "
                "All signals will be SKIPPED."
            )

        self._rules = _RulesFilter()
        self._morning_context: Optional[MarketContext] = None
        self._briefing_time:   Optional[datetime]      = None

    # =========================================================================
    #  PUBLIC API
    # =========================================================================

    def get_morning_context(self, force_refresh: bool = False) -> MarketContext:
        """
        Return cached briefing or build a fresh one.
        Cached for BRIEFING_CACHE_MIN minutes.
        Returns conservative MarketContext (allow_trading=False) on any failure.
        """
        if not self.enabled:
            return self._safe_context("Reviewer disabled — API key missing")

        cache_age = (
            (datetime.now() - self._briefing_time).total_seconds() / 60
            if self._briefing_time else float("inf")
        )
        if not force_refresh and self._morning_context and cache_age < BRIEFING_CACHE_MIN:
            logger.debug("ClaudeReviewer: using cached morning briefing (%.0f min old)", cache_age)
            return self._morning_context

        logger.info("ClaudeReviewer: building morning market briefing...")
        ctx = self._run_morning_briefing()
        self._morning_context = ctx
        self._briefing_time   = datetime.now()

        if ctx.error:
            logger.warning("Morning briefing failed — conservative defaults active. %s", ctx.briefing_text[:80])
        else:
            logger.info(
                "Morning briefing: conviction=%d sentiment=%s allow=%s risk=%d",
                ctx.conviction_score, ctx.market_sentiment, ctx.allow_trading, ctx.top_risk_score,
            )
        return ctx

    def review_signal(self, signal, market_context: MarketContext) -> SignalDecision:
        """
        Review a single signal. Runs rules filter then a one-signal batch call.
        Convenience wrapper around review_batch().
        """
        results = self.review_batch([signal], market_context)
        return results.get(signal.symbol, _skip("review_batch returned no result"))

    def review_batch(
        self,
        signals: list,
        market_context: MarketContext,
    ) -> Dict[str, SignalDecision]:
        """
        Review up to BATCH_SIZE signals in a single API call.
        Returns {symbol: SignalDecision}.
        Signals that fail the rules filter are SKIP without an API call.
        """
        t0 = time.time()

        if not self.enabled:
            return {s.symbol: _skip("Reviewer disabled") for s in signals}

        if market_context.error:
            return {s.symbol: _skip("Morning briefing failed — conservative skip") for s in signals}

        results: Dict[str, SignalDecision] = {}
        api_candidates = []

        # Phase 1: rules filter (free)
        for sig in signals[:BATCH_SIZE]:
            is_crypto = "/" in sig.symbol or getattr(sig, "asset_class", "") == "crypto"
            if not market_context.allow_trading and not is_crypto:
                results[sig.symbol] = _skip(
                    f"Trading blocked by briefing: conviction={market_context.conviction_score}"
                )
                continue
            blocked, reason = self._rules.evaluate(sig, market_context)
            if blocked:
                d = SignalDecision(
                    decision=REJECT if "earnings" in reason or "bearish" in reason else SKIP,
                    reasoning=f"[rules] {reason}",
                    confidence=95 if "earnings" in reason else 0,
                    filtered_by_rules=True,
                    error=False,
                )
                results[sig.symbol] = d
                logger.debug("Signal %s filtered by rules: %s", sig.symbol, reason)
            else:
                api_candidates.append(sig)

        if not api_candidates:
            elapsed = int((time.time() - t0) * 1000)
            for d in results.values():
                d.elapsed_ms = elapsed
            return results

        # Phase 2: batched Claude call
        logger.info(
            "ClaudeReviewer: sending %d/%d signals to Claude (rules passed)",
            len(api_candidates), len(signals[:BATCH_SIZE])
        )
        batch_results = self._call_batch_review(api_candidates, market_context)
        elapsed = int((time.time() - t0) * 1000)

        for sym, dec in batch_results.items():
            dec.elapsed_ms = elapsed
            results[sym] = dec
            logger.info(
                "Signal review: %s → %s (confidence=%d, %dms) | %s",
                sym, dec.decision, dec.confidence, elapsed, dec.reasoning[:80],
            )

        # Any candidate that didn't come back → conservative SKIP
        for sig in api_candidates:
            if sig.symbol not in results:
                results[sig.symbol] = _skip("No result from batch review")

        return results

    def is_enabled(self) -> bool:
        return self.enabled

    def get_status(self) -> Dict:
        ctx = self._morning_context
        return {
            "enabled":          self.enabled,
            "has_briefing":     ctx is not None,
            "briefing_error":   ctx.error if ctx else True,
            "allow_trading":    ctx.allow_trading if ctx else False,
            "conviction":       ctx.conviction_score if ctx else 0,
            "sentiment":        ctx.market_sentiment if ctx else "UNKNOWN",
            "briefing_age_min": (
                int((datetime.now() - self._briefing_time).total_seconds() / 60)
                if self._briefing_time else None
            ),
        }

    # =========================================================================
    #  MORNING BRIEFING
    # =========================================================================

    def _run_morning_briefing(self) -> MarketContext:
        market_snapshot = _build_market_snapshot()
        prompt = (
            f"Today is {datetime.now().strftime('%A, %B %d, %Y')}. "
            "Assess current US market conditions using ONLY the bot-fetched "
            "market snapshot below. Do not claim that current price action, "
            "breadth, or VIX data is unavailable if the snapshot contains usable "
            "proxy data. If a field is missing, name only that missing field. "
            "Return ONLY this JSON object — "
            "no markdown, no explanation:\n"
            '{"allow_trading": true, "conviction_score": 70, '
            '"market_sentiment": "BULLISH", "breadth_health": "HEALTHY", '
            '"top_risk_score": 30, "hot_sectors": ["Technology"], '
            '"cold_sectors": ["Utilities"], "active_themes": ["AI momentum"], '
            '"high_impact_events": [], "earnings_today": [], '
            '"max_exposure_pct": 60, "summary": "Replace with actual assessment."}'
            "\n\nBOT-FETCHED MARKET SNAPSHOT:\n"
            + json.dumps(market_snapshot, separators=(",", ":"), default=str)
            + "\n\nReplace ALL values with your assessment of that snapshot."
        )
        try:
            text = self._call_claude(prompt, BRIEFING_TIMEOUT_SEC, MAX_TOKENS_BRIEFING)
            if text is None:
                return self._safe_context("API call failed or timed out")

            parsed = _extract_json_object(text)
            if parsed is None:
                return self._safe_context("Could not parse JSON from briefing")

            return MarketContext(
                timestamp          = datetime.now(),
                allow_trading      = bool(parsed.get("allow_trading", False)),
                conviction_score   = int(parsed.get("conviction_score", 0)),
                market_sentiment   = str(parsed.get("market_sentiment", "UNKNOWN")),
                breadth_health     = str(parsed.get("breadth_health", "UNKNOWN")),
                top_risk_score     = int(parsed.get("top_risk_score", 100)),
                hot_sectors        = list(parsed.get("hot_sectors", [])),
                cold_sectors       = list(parsed.get("cold_sectors", [])),
                active_themes      = list(parsed.get("active_themes", [])),
                high_impact_events = list(parsed.get("high_impact_events", [])),
                earnings_today     = [s.upper() for s in parsed.get("earnings_today", [])],
                max_exposure_pct   = float(parsed.get("max_exposure_pct", 0)),
                briefing_text      = str(parsed.get("summary", text[:200])),
                error              = False,
            )
        except Exception as exc:
            logger.error("Morning briefing exception: %s", exc, exc_info=True)
            return self._safe_context(f"Exception: {exc}")

    # =========================================================================
    #  BATCH REVIEW
    # =========================================================================

    def _call_batch_review(
        self,
        signals: list,
        ctx: MarketContext,
    ) -> Dict[str, SignalDecision]:
        """
        Build a compact multi-signal prompt, call Claude once, parse JSON array.
        Returns {symbol: SignalDecision}. Falls back to SKIP on any error.
        """
        signal_payloads = [_compact_signal_payload(sig) for sig in signals]

        user_prompt = (
            f"MARKET CONTEXT:\n"
            f"sentiment={ctx.market_sentiment} conviction={ctx.conviction_score}/100 "
            f"breadth={ctx.breadth_health} risk={ctx.top_risk_score}/100\n"
            f"hot_sectors={ctx.hot_sectors[:3]} cold_sectors={ctx.cold_sectors[:3]}\n"
            f"events={ctx.high_impact_events or 'none'}\n\n"
            f"SIGNALS TO REVIEW ({len(signals)}), in order:\n"
            + json.dumps(signal_payloads, separators=(",", ":"), default=str)
            + f"\n\nReturn a JSON array with {len(signals)} elements, one per signal above."
        )

        try:
            text = self._call_claude(user_prompt, REVIEW_TIMEOUT_SEC, MAX_TOKENS_REVIEW)
        except Exception as exc:
            logger.error("Batch review call failed: %s", exc)
            return {s.symbol: _skip(f"API exception: {exc}") for s in signals}

        if text is None:
            return {s.symbol: _skip("API timeout or failure") for s in signals}

        parsed_array = _extract_json_array(text)
        if parsed_array is None or not isinstance(parsed_array, list):
            logger.warning("Could not parse JSON array from batch review: %s", text[:200])
            return {s.symbol: _skip("Could not parse batch response") for s in signals}

        results: Dict[str, SignalDecision] = {}
        for i, item in enumerate(parsed_array):
            if i >= len(signals):
                break
            sig = signals[i]
            if not isinstance(item, dict):
                results[sig.symbol] = _skip("Malformed response item")
                continue

            raw_dec = str(item.get("decision", SKIP)).upper()
            if raw_dec not in (APPROVE, REJECT, SKIP):
                raw_dec = SKIP

            # Safety overrides (belt-and-suspenders after rules filter)
            if raw_dec == APPROVE:
                if ctx.market_sentiment == "BEARISH" and sig.direction.lower() == "long":
                    raw_dec = REJECT
                    item["reasoning"] = "Safety override: bearish market + long rejected"
                elif ctx.top_risk_score > RULES_MAX_RISK_SCORE:
                    raw_dec = SKIP
                    item["reasoning"] = f"Safety override: risk score {ctx.top_risk_score}"

            results[sig.symbol] = SignalDecision(
                decision   = raw_dec,
                confidence = int(item.get("confidence", 0)),
                reasoning  = str(item.get("reasoning", "")),
                error      = False,
            )

        return results

    # =========================================================================
    #  CLAUDE SDK WRAPPER
    # =========================================================================

    def _call_claude(self, user_prompt: str, timeout: int, max_tokens: int) -> Optional[str]:
        """
        Single Claude API call using the official SDK.
        Returns None on any failure — caller handles the conservative fallback.
        Static system prompt sent with cache_control to enable prompt caching.
        """
        if not self._client:
            return None
        try:
            t0 = time.time()
            msg = self._client.messages.create(
                model      = CLAUDE_MODEL,
                max_tokens = max_tokens,
                system     = [
                    {
                        "type": "text",
                        "text": _SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages   = [{"role": "user", "content": user_prompt}],
                timeout    = timeout,
            )
            elapsed = time.time() - t0
            text = msg.content[0].text
            logger.debug("Claude API (%.1fs): %s...", elapsed, text[:80])
            return text
        except anthropic.APITimeoutError:
            logger.warning("Claude API timed out after %ds", timeout)
        except anthropic.APIConnectionError:
            logger.warning("Claude API connection error")
        except anthropic.APIStatusError as exc:
            logger.error("Claude API status %d: %s", exc.status_code, exc.message)
        except Exception as exc:
            logger.error("Claude API unexpected error: %s", exc)
        return None

    # =========================================================================
    #  HELPERS
    # =========================================================================

    def _safe_context(self, reason: str) -> MarketContext:
        return MarketContext(
            allow_trading    = False,
            conviction_score = 0,
            market_sentiment = "UNKNOWN",
            top_risk_score   = 100,
            max_exposure_pct = 0.0,
            briefing_text    = reason,
            error            = True,
        )


# ===========================================================================
#  MODULE-LEVEL HELPERS
# ===========================================================================

def _skip(reason: str) -> SignalDecision:
    return SignalDecision(decision=SKIP, reasoning=reason, error=False)


def _extract_json_object(text: str) -> Optional[Dict]:
    """Extract the first JSON object from a Claude response."""
    import re
    # Try to find {...} spanning multiple lines
    matches = re.findall(r'\{[^{}]*\}', text, re.DOTALL)
    for m in matches:
        try:
            parsed = json.loads(m)
            if any(k in parsed for k in ("allow_trading", "decision", "conviction_score")):
                return parsed
        except json.JSONDecodeError:
            continue
    # Fallback: full text
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None


def _extract_json_array(text: str) -> Optional[list]:
    """Extract a JSON array from a Claude response."""
    import re
    # Strip markdown code fences if present
    text = re.sub(r"```[a-z]*\n?", "", text).strip()
    # Find [...] block
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ── Singleton ────────────────────────────────────────────────────────────────
claude_reviewer = ClaudeReviewer()
