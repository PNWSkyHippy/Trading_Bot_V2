"""
=============================================================
  POSITION MONITOR
  Runs every 30 seconds. Watches all open positions for:
  - Stop-loss triggers
  - Take-profit triggers
  - Trailing stop adjustments (with logging)
  - Extended take-profit on continued momentum (with logging)
  - Performance-contingent time stops (NEW):
      < 0.5% profit after 1 hour  → close (going nowhere)
      < 1.5% profit after 3 hours → close (too slow)
  - Early loss identification (NEW):
      If trade is negative AND moving further wrong at 20 min → close
  - Hard time stop (NEW): 3.5 hours regardless of profit
  - Stale position sell-off (3hr ADX/DI trend check)
  - Pivot point break exit (NEW):
      Long  breaks below S1 → close (structure failed)
      Short breaks above R1 → close (structure failed)
  - VWAP cross exit for ORB trades
  - EOD close for all stock positions

  Exit priority order:
    1.  STUCK check
    2.  EOD close (15:45 ET)
    3.  Stop-loss
    4.  ORB VWAP cross exit
    5.  Early loss identification (20 min check)
    6.  Performance-contingent time stop (1hr check)
    7.  Performance-contingent time stop (3hr check)
    8.  Hard time stop (3.5hr)
    9.  Take-profit + momentum rider
    10. Pivot point break
    11. Stale position ADX/DI check (3hr)
    12. Trailing stop update

  Close attempt throttle:
    If a close attempt fails the trade stays open in DB and would
    retry every 30s forever. We track close attempts in bot_state.
    After MAX_CLOSE_ATTEMPTS the trade is flagged STUCK and skipped
    until human intervenes. Dashboard shows STUCK trades.

  Stock positions are only monitored during market hours
  (Mon-Fri 09:30-16:00 ET). Crypto is monitored 24/7.
=============================================================
"""

import logging
import time
import threading
from datetime import datetime, timezone
from typing import List, Dict, Optional

import numpy as np
import pandas as pd

import config
from data.database import db
from core.risk_manager import risk_manager

logger = logging.getLogger(__name__)

# ── Stale position check ─────────────────────────────────────────────────────
STALE_THRESHOLD_SEC = 3 * 60 * 60       # 3 hours before ADX/DI stale check fires

# ADX threshold below which trend is considered stalled
ADX_STALE_THRESHOLD = 25.0

# ── NEW: Time-based exit thresholds ──────────────────────────────────────────
# Performance-contingent: close if profit is below threshold after N hours.
# Prevents capital being locked in trades that never got going.
# NOTE: grid_bot trades are EXEMPT from all time stops (see _check_performance_time_stop)
# Grid strategies need time to oscillate — time stops kill them prematurely.
PERF_CHECK_1HR_SEC     = 2 * 60 * 60    # 2 hours (was 1hr — too aggressive)
PERF_CHECK_1HR_MIN_PCT = 0.3            # need at least 0.3% profit by 2hr (was 0.5%)

PERF_CHECK_3HR_SEC     = 5 * 60 * 60    # 5 hours (was 3hr)
PERF_CHECK_3HR_MIN_PCT = 1.0            # need at least 1.0% profit by 5hr (was 1.5%)

HARD_TIME_STOP_SEC     = 8 * 60 * 60    # 8 hours — hard kill (was 3.5hr)

# Early loss check: if trade is negative AND worsening at 20 minutes, kill it.
# Catches trades where thesis was wrong from the start.
EARLY_LOSS_CHECK_SEC   = 30 * 60        # 30 minutes (was 20min — too tight)
EARLY_LOSS_MIN_PCT     = -0.5           # if worse than -0.5% AND still falling (was -0.3%)

# Pivot point break exit
# Uses last N bars to calculate classic floor trader pivots (PP, S1, S2, R1, R2)
PIVOT_BARS             = 20             # bars to use for pivot calculation

# ── EOD close ────────────────────────────────────────────────────────────────
EOD_CLOSE_HOUR   = 15
EOD_CLOSE_MINUTE = 45

# ── Max close attempts ────────────────────────────────────────────────────────
MAX_CLOSE_ATTEMPTS = 3


def _stock_market_open() -> bool:
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    now_et  = datetime.now(ZoneInfo("America/New_York"))
    weekday = now_et.weekday()
    hour    = now_et.hour
    minute  = now_et.minute

    if weekday > 4:
        return False

    after_open   = hour > 9 or (hour == 9 and minute >= 30)
    before_close = hour < 16
    return after_open and before_close


def _approaching_eod() -> bool:
    """Returns True if it's time to close all stock positions (15:45 ET)."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    now_et  = datetime.now(ZoneInfo("America/New_York"))
    weekday = now_et.weekday()
    if weekday > 4:
        return False

    at_or_after = (
        now_et.hour > EOD_CLOSE_HOUR or
        (now_et.hour == EOD_CLOSE_HOUR and now_et.minute >= EOD_CLOSE_MINUTE)
    )
    before_close = now_et.hour < 16
    return at_or_after and before_close


def _get_position_age_seconds(trade: Dict) -> float:
    """Return how many seconds a position has been open."""
    try:
        entry_raw = trade.get("entry_time", "")
        if not entry_raw:
            return 0.0
        entry_dt = pd.to_datetime(entry_raw)
        if entry_dt.tzinfo is None:
            entry_dt = entry_dt.replace(tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        return (now_utc - entry_dt).total_seconds()
    except Exception:
        return 0.0


class PositionMonitor:
    """
    Continuously monitors all open positions.
    Runs in its own background thread so it never blocks the scanner.
    """

    def __init__(self, db_ref=None, trade_executor=None):
        self._db            = db_ref or db
        self._executor      = trade_executor
        self.running        = False
        self.check_interval = 30
        self._thread        = None

    def _get_executor(self):
        if self._executor:
            return self._executor
        from core.trade_executor import executor
        return executor

    def _get_scanner(self):
        from scanners.market_scanner import scanner
        return scanner

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Position monitor started.")

    def stop(self):
        self.running = False
        logger.info("Position monitor stopped.")

    def _monitor_loop(self):
        while self.running:
            try:
                self.check_positions()
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
            time.sleep(self.check_interval)

    # ------------------------------------------------------------------
    #  CLOSE ATTEMPT THROTTLE
    # ------------------------------------------------------------------

    def _get_close_attempts(self, trade_id: str) -> int:
        return int(self._db.get_state(f"close_attempts_{trade_id}", default=0))

    def _increment_close_attempts(self, trade_id: str, symbol: str) -> int:
        count = self._get_close_attempts(trade_id) + 1
        self._db.set_state(f"close_attempts_{trade_id}", count)
        if count >= MAX_CLOSE_ATTEMPTS:
            self._db.set_state(f"close_stuck_{trade_id}", 1)
            logger.error(
                f"[STUCK] {symbol}: {count} failed close attempts. "
                f"Manual intervention required. Use dashboard Close Now "
                f"button or DB Browser to resolve."
            )
        return count

    def _reset_close_attempts(self, trade_id: str):
        self._db.set_state(f"close_attempts_{trade_id}", 0)
        self._db.set_state(f"close_stuck_{trade_id}", 0)

    def _is_stuck(self, trade_id: str) -> bool:
        return int(self._db.get_state(f"close_stuck_{trade_id}", default=0)) == 1

    def _attempt_close(self, trade: Dict, current_price: float,
                       reason: str) -> bool:
        """
        Wrapper around close_trade that tracks failed attempts.
        After MAX_CLOSE_ATTEMPTS failures, flags trade as STUCK.
        """
        trade_id = trade["trade_id"]
        symbol   = trade["symbol"]

        success = self._get_executor().close_trade(trade, current_price, reason)

        if success:
            self._reset_close_attempts(trade_id)
            return True
        else:
            count = self._increment_close_attempts(trade_id, symbol)
            logger.warning(
                f"Close attempt {count}/{MAX_CLOSE_ATTEMPTS} failed for "
                f"{symbol} | reason={reason}"
            )
            return False

    # ------------------------------------------------------------------
    #  NEW: PERFORMANCE-CONTINGENT TIME STOPS
    # ------------------------------------------------------------------

    def _check_performance_time_stop(
        self, trade: Dict, pnl_pct: float, age_seconds: float
    ) -> Optional[str]:
        """
        Kill trades that aren't performing within expected timeframes.

        Logic:
          - After 20 min: if pnl < -0.3% AND still moving wrong → early exit
          - After 1 hour: if pnl < 0.5% → going nowhere, free up capital
          - After 3 hours: if pnl < 1.5% → too slow for a day trade
          - After 3.5 hours: hard kill regardless of profit

        Returns exit reason string or None if trade should continue.
        """
        symbol    = trade["symbol"]
        direction = trade["direction"]
        trade_id  = trade["trade_id"]
        strategy  = trade.get("strategy_name", "")

        # ── Grid bot exemption: time stops kill grid strategies ────────
        # Grid bot profits from oscillations that can take hours to complete.
        # Applying time stops to grid_bot directly contradicts its thesis.
        if strategy in ("grid_bot", "dca_accumulator"):
            logger.debug(
                f"[TIME STOP EXEMPT] {symbol}: strategy={strategy} "
                f"is exempt from performance time stops"
            )
            return None

        # ── Hard time stop: 3.5 hours ─────────────────────────────────
        if age_seconds >= HARD_TIME_STOP_SEC:
            logger.info(
                f"[HARD TIME STOP] {symbol}: open {age_seconds/3600:.1f}hrs — "
                f"3.5hr max reached | P&L {pnl_pct:+.2f}% | closing"
            )
            return "hard_time_stop"

        # ── 3-hour performance check ──────────────────────────────────
        if age_seconds >= PERF_CHECK_3HR_SEC:
            if pnl_pct < PERF_CHECK_3HR_MIN_PCT:
                logger.info(
                    f"[PERF TIME STOP 3HR] {symbol}: open {age_seconds/3600:.1f}hrs | "
                    f"P&L {pnl_pct:+.2f}% < {PERF_CHECK_3HR_MIN_PCT}% target — closing"
                )
                return "perf_time_stop_3hr"

        # ── 1-hour performance check ──────────────────────────────────
        if age_seconds >= PERF_CHECK_1HR_SEC:
            if pnl_pct < PERF_CHECK_1HR_MIN_PCT:
                logger.info(
                    f"[PERF TIME STOP 1HR] {symbol}: open {age_seconds/3600:.1f}hrs | "
                    f"P&L {pnl_pct:+.2f}% < {PERF_CHECK_1HR_MIN_PCT}% target — closing"
                )
                return "perf_time_stop_1hr"

        return None

    # ------------------------------------------------------------------
    #  NEW: EARLY LOSS IDENTIFICATION (20 MIN CHECK)
    # ------------------------------------------------------------------

    def _check_early_loss(
        self, trade: Dict, current_price: float, pnl_pct: float, age_seconds: float
    ) -> Optional[str]:
        """
        Catch trades where the thesis was wrong from the start.
        At 20 minutes: if trade is negative AND still moving against us → close.
        This limits losses on trades that immediately went the wrong way
        rather than waiting for the full stop loss to be hit.

        Uses last 3 bars to confirm the move is still going against us,
        not just a brief wick.
        """
        symbol    = trade["symbol"]
        direction = trade["direction"]
        trade_id  = trade["trade_id"]

        # Only check in the 20-40 minute window (don't re-check after)
        if age_seconds < EARLY_LOSS_CHECK_SEC:
            return None
        if age_seconds > EARLY_LOSS_CHECK_SEC * 2:  # 40 minutes max window
            return None

        # Already checked this trade at 20 min?
        already_checked = int(
            self._db.get_state(f"early_loss_checked_{trade_id}", default=0)
        )
        if already_checked:
            return None

        # Mark as checked so we don't re-evaluate
        self._db.set_state(f"early_loss_checked_{trade_id}", 1)

        if pnl_pct >= EARLY_LOSS_MIN_PCT:
            # Trade is flat or positive — no early exit needed
            logger.debug(
                f"[EARLY CHECK] {symbol}: P&L {pnl_pct:+.2f}% at 20min — OK"
            )
            return None

        # Trade is negative — check if still moving against us
        bars = self._get_bars(symbol, trade["asset_class"], limit=5)
        if bars is None or len(bars) < 3:
            logger.info(
                f"[EARLY LOSS EXIT] {symbol}: P&L {pnl_pct:+.2f}% at 20min, "
                f"no bar data to confirm — closing on loss threshold"
            )
            return "early_loss_no_data"

        closes = bars["close"].values
        still_wrong = (
            direction == "long"  and closes[-1] < closes[-2] < closes[-3]
        ) or (
            direction == "short" and closes[-1] > closes[-2] > closes[-3]
        )

        if still_wrong:
            logger.info(
                f"[EARLY LOSS EXIT] {symbol}: P&L {pnl_pct:+.2f}% at 20min "
                f"AND still moving wrong direction — thesis failed, closing"
            )
            return "early_loss"
        else:
            logger.info(
                f"[EARLY CHECK] {symbol}: P&L {pnl_pct:+.2f}% at 20min but "
                f"price stabilizing — holding, watching stop loss"
            )
            return None

    # ------------------------------------------------------------------
    #  NEW: PIVOT POINT BREAK EXIT
    # ------------------------------------------------------------------

    def _check_pivot_break(
        self, trade: Dict, current_price: float
    ) -> Optional[str]:
        """
        Classic floor trader pivot points calculated from recent bars.
        PP  = (High + Low + Close) / 3
        S1  = 2*PP - High   (first support)
        S2  = PP - (High - Low)  (second support)
        R1  = 2*PP - Low    (first resistance)
        R2  = PP + (High - Low)  (second resistance)

        Exit logic:
          Long:  if price breaks below S1 → structural support failed → close
          Short: if price breaks above R1 → structural resistance failed → close

        Only fires after 30 minutes (gives trade time to breathe past entry noise).
        """
        symbol    = trade["symbol"]
        direction = trade["direction"]
        trade_id  = trade["trade_id"]

        bars = self._get_bars(symbol, trade["asset_class"], limit=PIVOT_BARS)
        if bars is None or len(bars) < 5:
            return None

        # Calculate pivots from the lookback window (excluding current bar)
        h   = float(bars["high"].iloc[:-1].max())
        l   = float(bars["low"].iloc[:-1].min())
        c   = float(bars["close"].iloc[-2])  # last closed bar

        pp  = (h + l + c) / 3
        s1  = 2 * pp - h
        s2  = pp - (h - l)
        r1  = 2 * pp + l   # corrected: 2*PP - Low
        r1  = 2 * pp - l
        r2  = pp + (h - l)

        logger.debug(
            f"[PIVOT] {symbol}: PP={pp:.4f} S1={s1:.4f} S2={s2:.4f} "
            f"R1={r1:.4f} R2={r2:.4f} | current={current_price:.4f}"
        )

        if direction == "long" and current_price < s1:
            logger.info(
                f"[PIVOT EXIT] {symbol}: LONG broke below S1={s1:.4f} "
                f"(current={current_price:.4f}) — structural support failed, closing"
            )
            return "pivot_break_s1"

        if direction == "short" and current_price > r1:
            logger.info(
                f"[PIVOT EXIT] {symbol}: SHORT broke above R1={r1:.4f} "
                f"(current={current_price:.4f}) — structural resistance failed, closing"
            )
            return "pivot_break_r1"

        return None

    # ------------------------------------------------------------------
    #  ADX / DI HELPERS FOR STALE POSITION CHECK
    # ------------------------------------------------------------------

    def _get_adx_di(self, symbol: str, asset_class: str) -> Optional[Dict]:
        try:
            import pandas_ta as ta
            bars = self._get_bars(symbol, asset_class, limit=50)
            if bars is None or len(bars) < 20:
                return None

            adx_df  = ta.adx(bars["high"], bars["low"], bars["close"], length=14)
            if adx_df is None or adx_df.empty:
                return None

            adx_col = [c for c in adx_df.columns if c.startswith("ADX_")]
            dmp_col = [c for c in adx_df.columns if c.startswith("DMP_")]
            dmn_col = [c for c in adx_df.columns if c.startswith("DMN_")]

            if not adx_col or not dmp_col or not dmn_col:
                return None

            return {
                "adx":      float(adx_df[adx_col[0]].iloc[-1]),
                "plus_di":  float(adx_df[dmp_col[0]].iloc[-1]),
                "minus_di": float(adx_df[dmn_col[0]].iloc[-1]),
            }
        except Exception as e:
            logger.debug(f"ADX/DI fetch error for {symbol}: {e}")
            return None

    def _check_stale_position(self, trade: Dict) -> Optional[str]:
        """
        Stale position sell-off logic:
          If ADX < 25 (trend stalled) → sell immediately
          Else:
            Long  + bearish (-DI > +DI) → sell
            Long  + bullish (+DI > -DI) → hold
            Short + bullish (+DI > -DI) → sell
            Short + bearish (-DI > +DI) → hold
        """
        symbol    = trade["symbol"]
        direction = trade["direction"]

        adx_data = self._get_adx_di(symbol, trade["asset_class"])
        if adx_data is None:
            logger.debug(f"[STALE] {symbol}: could not get ADX data — skipping")
            return None

        adx      = adx_data["adx"]
        plus_di  = adx_data["plus_di"]
        minus_di = adx_data["minus_di"]

        logger.info(
            f"[STALE CHECK] {symbol} {direction.upper()} | "
            f"Open 3+ hrs | ADX={adx:.1f} +DI={plus_di:.1f} -DI={minus_di:.1f}"
        )

        if adx < ADX_STALE_THRESHOLD:
            logger.info(
                f"[STALE EXIT] {symbol}: ADX={adx:.1f} < {ADX_STALE_THRESHOLD} "
                f"(trend stalled) — closing"
            )
            return "stale_no_trend"

        if direction == "long":
            if minus_di > plus_di:
                logger.info(
                    f"[STALE EXIT] {symbol}: LONG but -DI({minus_di:.1f}) > "
                    f"+DI({plus_di:.1f}) (bearish) — closing"
                )
                return "stale_trend_reversed"
            else:
                logger.info(
                    f"[STALE HOLD] {symbol}: LONG and +DI({plus_di:.1f}) > "
                    f"-DI({minus_di:.1f}) (bullish) — holding"
                )
                return None
        else:
            if plus_di > minus_di:
                logger.info(
                    f"[STALE EXIT] {symbol}: SHORT but +DI({plus_di:.1f}) > "
                    f"-DI({minus_di:.1f}) (bullish) — closing"
                )
                return "stale_trend_reversed"
            else:
                logger.info(
                    f"[STALE HOLD] {symbol}: SHORT and -DI({minus_di:.1f}) > "
                    f"+DI({plus_di:.1f}) (bearish) — holding"
                )
                return None

    def _check_vwap_cross_exit(self, trade: Dict, current_price: float) -> bool:
        """VWAP cross exit for ORB trades."""
        try:
            bars = self._get_bars(trade["symbol"], trade["asset_class"], limit=50)
            if bars is None or len(bars) < 5:
                return False

            typical = (bars["high"] + bars["low"] + bars["close"]) / 3
            cum_tpv = (typical * bars["volume"]).cumsum()
            cum_vol = bars["volume"].cumsum()
            vwap    = (cum_tpv / cum_vol.replace(0, float("nan"))).iloc[-1]

            if pd.isna(vwap):
                return False

            direction = trade["direction"]
            if direction == "long" and current_price < vwap:
                logger.info(
                    f"[ORB VWAP EXIT] {trade['symbol']}: price {current_price:.4f} "
                    f"crossed below VWAP {vwap:.4f} — closing"
                )
                return True
            elif direction == "short" and current_price > vwap:
                logger.info(
                    f"[ORB VWAP EXIT] {trade['symbol']}: price {current_price:.4f} "
                    f"crossed above VWAP {vwap:.4f} — closing"
                )
                return True

            return False
        except Exception as e:
            logger.debug(f"VWAP cross check error for {trade['symbol']}: {e}")
            return False

    # ------------------------------------------------------------------
    #  MOMENTUM RIDER HELPERS
    # ------------------------------------------------------------------

    def _get_bars(self, symbol: str, asset_class: str,
                  limit: int = 25) -> Optional[pd.DataFrame]:
        try:
            sc = self._get_scanner()
            if asset_class == "stock":
                return sc.stock_scanner.get_bars(symbol, timeframe="5Min", limit=limit)
            else:
                return sc.crypto_scanner.get_ohlcv(symbol, timeframe="5m", limit=limit)
        except Exception as e:
            logger.debug(f"Bar fetch error for {symbol}: {e}")
            return None

    def _score_momentum(self, symbol: str, asset_class: str) -> float:
        try:
            bars = self._get_bars(symbol, asset_class, limit=25)
            if bars is None or len(bars) < 15:
                return 0.0

            closes  = bars["close"]
            volumes = bars["volume"]
            hits    = 0

            delta    = closes.diff()
            gain     = delta.clip(lower=0)
            loss     = -delta.clip(upper=0)
            avg_gain = gain.ewm(com=13, adjust=False).mean()
            avg_loss = loss.ewm(com=13, adjust=False).mean()
            rs       = avg_gain / avg_loss.replace(0, np.nan)
            rsi      = 100 - (100 / (1 + rs))
            rsi_now  = rsi.iloc[-1]
            rsi_prev = rsi.iloc[-4]
            if rsi_now >= config.MOMENTUM_RIDER_RSI_MIN and rsi_now > rsi_prev:
                hits += 1

            c = closes.iloc[-3:].values
            if c[1] > c[0] and c[2] > c[1]:
                hits += 1

            vol_avg = volumes.iloc[-21:-1].mean()
            vol_now = volumes.iloc[-1]
            if vol_avg > 0 and vol_now >= vol_avg * config.MOMENTUM_RIDER_VOL_RATIO:
                hits += 1

            return hits / 3

        except Exception as e:
            logger.debug(f"Momentum score error for {symbol}: {e}")
            return 0.0

    # ------------------------------------------------------------------
    #  MAIN POSITION PROCESSOR
    # ------------------------------------------------------------------

    def _process_position(self, trade: Dict):
        """
        Process a single open position.

        Exit priority order:
          1.  STUCK check
          2.  EOD close (15:45 ET)
          3.  Stop-loss
          4.  ORB VWAP cross exit
          5.  Early loss identification (20 min)
          6.  Performance-contingent time stop (1hr)
          7.  Performance-contingent time stop (3hr)
          8.  Hard time stop (3.5hr)
          9.  Take-profit + momentum rider
          10. Pivot point break
          11. Stale position ADX/DI (3hr)
          12. Trailing stop update + logging
        """
        symbol      = trade["symbol"]
        asset_class = trade["asset_class"]
        direction   = trade["direction"]
        trade_id    = trade["trade_id"]
        strategy    = trade.get("strategy_name", "")
        is_overnight= bool(trade.get("is_overnight", False))

        # ── 1. STUCK CHECK ───────────────────────────────────────────────
        if self._is_stuck(trade_id):
            logger.warning(
                f"[STUCK] {symbol}: skipping — exceeded {MAX_CLOSE_ATTEMPTS} "
                f"close attempts. Use dashboard Close Now to resolve."
            )
            return

        current_price = self._get_scanner().get_current_price(symbol, asset_class)
        if current_price is None:
            logger.warning(f"Could not get price for {symbol} — skipping check")
            return

        qty = trade["quantity"]
        if direction == "long":
            pnl_pct = (current_price - trade["entry_price"]) / trade["entry_price"] * 100
        else:
            pnl_pct = (trade["entry_price"] - current_price) / trade["entry_price"] * 100

        age_seconds = _get_position_age_seconds(trade)
        age_hrs     = age_seconds / 3600

        logger.debug(
            f"{symbol}: price=${current_price:.4f} | "
            f"SL=${trade['stop_loss']:.4f} | TP=${trade['take_profit']:.4f} | "
            f"P&L: {pnl_pct:+.2f}% | Age: {age_hrs:.1f}hr"
        )

        # ── 2. EOD CLOSE (15:45 ET) ──────────────────────────────────────
        if asset_class == "stock" and not is_overnight and _approaching_eod():
            logger.info(
                f"[EOD CLOSE] {symbol}: closing before market close @ 15:45 ET"
            )
            self._db.set_state(f"momentum_ext_{trade_id}", 0)
            self._attempt_close(trade, current_price, "eod_close")
            return

        # ── 3. STOP-LOSS ──────────────────────────────────────────────────
        sl_exit = risk_manager.check_sl_exit(trade, current_price)
        if sl_exit:
            logger.info(
                f"[STOP LOSS] {symbol} @ ${current_price:.4f} | "
                f"P&L {pnl_pct:+.2f}% | age {age_hrs:.1f}hr"
            )
            self._db.set_state(f"momentum_ext_{trade_id}", 0)
            self._attempt_close(trade, current_price, sl_exit)
            return

        # ── 4. ORB VWAP CROSS EXIT ──────────────────────────────────────
        if strategy == "orb_breakout":
            if self._check_vwap_cross_exit(trade, current_price):
                self._db.set_state(f"momentum_ext_{trade_id}", 0)
                self._attempt_close(trade, current_price, "vwap_cross")
                return

        # ── 5. EARLY LOSS IDENTIFICATION (20 min) ────────────────────────
        # Skip for ORB — it needs time to develop past the opening range
        if strategy != "orb_breakout":
            early_exit = self._check_early_loss(
                trade, current_price, pnl_pct, age_seconds
            )
            if early_exit:
                self._db.set_state(f"momentum_ext_{trade_id}", 0)
                self._attempt_close(trade, current_price, early_exit)
                return

        # ── 6-8. PERFORMANCE-CONTINGENT AND HARD TIME STOPS ──────────────
        # Skip for overnight positions — they're explicitly held longer
        if not is_overnight:
            time_exit = self._check_performance_time_stop(
                trade, pnl_pct, age_seconds
            )
            if time_exit:
                self._db.set_state(f"momentum_ext_{trade_id}", 0)
                self._attempt_close(trade, current_price, time_exit)
                return

        # ── 9. TAKE-PROFIT + MOMENTUM RIDER (non-ORB) ────────────────────
        if strategy != "orb_breakout":
            at_tp = (
                (direction == "long"  and current_price >= trade["take_profit"]) or
                (direction == "short" and current_price <= trade["take_profit"])
            )

            if at_tp:
                rider_enabled  = getattr(config, "MOMENTUM_RIDER_ENABLED", True)
                max_extensions = getattr(config, "MOMENTUM_RIDER_MAX_EXTENSIONS", 3)
                min_score      = getattr(config, "MOMENTUM_RIDER_MIN_SCORE", 0.67)
                ext_count      = int(self._db.get_state(
                    f"momentum_ext_{trade_id}", default=0
                ))

                ride = False
                if rider_enabled and ext_count < max_extensions:
                    mom_score = self._score_momentum(symbol, asset_class)
                    ride = mom_score >= min_score

                if ride:
                    tp_pct = config.DEFAULT_TAKE_PROFIT_PCT / 100
                    new_tp = (
                        current_price * (1 + tp_pct)
                        if direction == "long"
                        else current_price * (1 - tp_pct)
                    )
                    new_tp = round(new_tp, 4)
                    self._db.update_trade_levels(trade_id, take_profit=new_tp)
                    self._db.set_state(f"momentum_ext_{trade_id}", ext_count + 1)
                    with self._db._conn() as conn:
                        conn.execute(
                            "UPDATE trades SET tp_hit_count = ? WHERE trade_id = ?",
                            (ext_count + 1, trade_id)
                        )
                        conn.commit()
                    # ── LOG TP EXTENSION ──────────────────────────────────
                    logger.info(
                        f"[TP EXTENDED] {symbol} {direction.upper()} | "
                        f"TP raised {trade['take_profit']:.4f} → {new_tp:.4f} | "
                        f"Extension {ext_count + 1}/{max_extensions} | "
                        f"Momentum score: {mom_score:.2f} | P&L {pnl_pct:+.2f}%"
                    )
                else:
                    logger.info(
                        f"[TAKE PROFIT] {symbol} @ ${current_price:.4f} | "
                        f"P&L {pnl_pct:+.2f}% | "
                        f"Extensions used: {ext_count} | "
                        f"Original TP was ${trade['take_profit']:.4f}"
                    )
                    self._db.set_state(f"momentum_ext_{trade_id}", 0)
                    with self._db._conn() as conn:
                        conn.execute(
                            "UPDATE trades SET tp_hit_count = 0 WHERE trade_id = ?",
                            (trade_id,)
                        )
                        conn.commit()
                    self._attempt_close(trade, current_price, "take_profit")
                    return

        # ── 10. PIVOT POINT BREAK ─────────────────────────────────────────
        # Only check after 30 min to allow trade to breathe past entry noise
        if age_seconds >= 30 * 60 and strategy != "orb_breakout":
            pivot_exit = self._check_pivot_break(trade, current_price)
            if pivot_exit:
                logger.info(
                    f"[PIVOT BREAK] {symbol}: structural level broken | "
                    f"P&L {pnl_pct:+.2f}% | age {age_hrs:.1f}hr"
                )
                self._db.set_state(f"momentum_ext_{trade_id}", 0)
                self._attempt_close(trade, current_price, pivot_exit)
                return

        # ── 11. STALE POSITION CHECK (3hr ADX/DI) ────────────────────────
        # Note: by this point the performance time stop at 3hr has already
        # fired if profit was below 1.5%. This catches winning positions
        # that are starting to show trend exhaustion.
        if age_seconds >= STALE_THRESHOLD_SEC:
            stale_exit = self._check_stale_position(trade)
            if stale_exit:
                logger.info(
                    f"[STALE EXIT] {symbol}: closing after "
                    f"{age_hrs:.1f}hrs | reason={stale_exit}"
                )
                self._db.set_state(f"momentum_ext_{trade_id}", 0)
                self._attempt_close(trade, current_price, stale_exit)
                return

        # ── 12. TRAILING STOP UPDATE + LOGGING ───────────────────────────
        updates = risk_manager.calculate_trailing_stop(trade, current_price)
        if updates:
            old_sl = trade.get("stop_loss", 0)
            old_tp = trade.get("take_profit", 0)
            self._db.update_trade_levels(
                trade_id,
                stop_loss   = updates.get("stop_loss"),
                take_profit = updates.get("take_profit"),
            )
            # Log trailing stop moves so closed trade history is clear
            if "stop_loss" in updates and updates["stop_loss"] != old_sl:
                logger.info(
                    f"[TRAILING STOP] {symbol} {direction.upper()} | "
                    f"SL ratcheted ${old_sl:.4f} → ${updates['stop_loss']:.4f} | "
                    f"Locked in {pnl_pct:+.2f}% gain"
                )
            if "take_profit" in updates and updates["take_profit"] != old_tp:
                logger.info(
                    f"[DYNAMIC TP] {symbol} {direction.upper()} | "
                    f"TP adjusted ${old_tp:.4f} → ${updates['take_profit']:.4f}"
                )

    def check_positions(self):
        open_trades = self._db.get_open_trades()
        if not open_trades:
            return

        market_open = _stock_market_open()

        stock_trades  = [t for t in open_trades if t.get("asset_class") == "stock"]
        crypto_trades = [t for t in open_trades if t.get("asset_class") != "stock"]

        if stock_trades and not market_open:
            logger.debug(
                f"Position monitor: skipping {len(stock_trades)} stock position(s) "
                f"— market closed"
            )

        trades_to_check = crypto_trades
        if market_open:
            trades_to_check = trades_to_check + stock_trades

        if not trades_to_check:
            return

        logger.debug(f"Monitoring {len(trades_to_check)} open positions...")

        for trade in trades_to_check:
            try:
                self._process_position(trade)
            except Exception as e:
                logger.error(
                    f"Error processing position {trade['symbol']}: {e}"
                )

        # Price alerts
        try:
            from reporting.alerts import alert_manager
            from data.database import db as _db

            all_symbols = list(config.CRYPTO_WATCHLIST)
            if market_open:
                all_symbols += (
                    list(config.STOCK_WATCHLIST) +
                    ["SOXL", "SOXS", "TQQQ", "SQQQ", "SPXL", "SPXS",
                     "UVXY", "SVXY", "LABU", "LABD"]
                )

            for sym in all_symbols:
                alerts = _db.get_state(f"price_alerts_{sym}", default=[])
                if not alerts:
                    continue
                asset = "crypto" if "/" in sym else "stock"
                price = self._get_scanner().get_current_price(sym, asset)
                if price:
                    alert_manager.check_price_alerts(sym, price)
        except Exception as e:
            logger.debug(f"Price alert check error: {e}")

    def check_all_positions(self):
        """Alias for backward compatibility."""
        self.check_positions()

    def get_positions_summary(self) -> List[Dict]:
        open_trades = self._db.get_open_trades()
        enriched    = []
        market_open = _stock_market_open()

        for trade in open_trades:
            symbol      = trade["symbol"]
            asset_class = trade["asset_class"]

            if asset_class == "stock" and not market_open:
                current_price = trade["entry_price"]
            else:
                current_price = self._get_scanner().get_current_price(
                    symbol, asset_class
                )
                if current_price is None:
                    current_price = trade["entry_price"]

            qty       = trade["quantity"]
            direction = trade["direction"]

            if direction == "long":
                unrealized_pnl = (current_price - trade["entry_price"]) * qty
                pnl_pct = (current_price / trade["entry_price"] - 1) * 100
            else:
                unrealized_pnl = (trade["entry_price"] - current_price) * qty
                pnl_pct = (trade["entry_price"] / current_price - 1) * 100

            age_seconds = _get_position_age_seconds(trade)
            is_stuck    = self._is_stuck(trade["trade_id"])
            close_attempts = self._get_close_attempts(trade["trade_id"])

            enriched.append({
                **trade,
                "current_price":   round(current_price, 6),
                "unrealized_pnl":  round(unrealized_pnl, 4),
                "pnl_pct":         round(pnl_pct, 2),
                "market_value":    round(current_price * qty, 2),
                "distance_to_sl":  round(
                    abs(current_price - trade["stop_loss"]) / current_price * 100, 2
                ),
                "distance_to_tp":  round(
                    abs(trade["take_profit"] - current_price) / current_price * 100, 2
                ),
                "age_hours":       round(age_seconds / 3600, 2),
                "is_overnight":    bool(trade.get("is_overnight", False)),
                "tp_hit_count":    int(trade.get("tp_hit_count", 0)),
                "is_stuck":        is_stuck,
                "close_attempts":  close_attempts,
            })

        return enriched


# Singleton
monitor = PositionMonitor()
