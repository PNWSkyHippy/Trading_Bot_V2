"""
=============================================================
  POSITION MONITOR
  Runs every 10 seconds. Watches all open positions for:
  - Stop-loss triggers
  - Take-profit triggers
  - Trailing stop adjustments (with logging)
  - Extended take-profit on continued momentum (with logging)
  - Performance-contingent time stops:
      < 0.2% profit after 2 hours → close (going nowhere)
      < 1.0% profit after 5 hours → close (too slow)
      grid_bot and dca_accumulator are EXEMPT from all time stops
  - Early loss identification:
      If trade is negative AND moving further wrong at 30 min → close
  - Hard time stop: 8 hours regardless of profit (grid_bot EXEMPT)
  - Stale position sell-off (3hr ADX/DI trend check)
  - Pivot point break exit (NEW):
      Long  breaks below S1 → close (structure failed)
      Short breaks above R1 → close (structure failed)
  - VWAP cross exit for ORB trades
  - Adaptive regime exit (EMA cross for trend; BB midline/RSI for mean rev)
  - EOD close for all stock positions

  Exit priority order:
    1.  STUCK check
    2.  EOD close (15:45 ET)
    3.  Stop-loss
    4.  ORB VWAP cross exit
    4b. RSI dip & spike exit (rsi_dip_spike_v4 strategy only)
    5.  Early loss identification (30 min check, -0.5% threshold)
    6.  Performance-contingent time stop (2hr check, needs 0.2%)
    7.  Performance-contingent time stop (5hr check, needs 1.0%)
    8.  Hard time stop (8hr — grid_bot/dca_accumulator EXEMPT)
    9.  Take-profit + momentum rider
    10. Pivot point break
    11. Stale position ADX/DI check (3hr)
    12. Trailing stop update

  Close attempt throttle:
    If a close attempt fails the trade stays open in DB and would
    retry every 10s forever (monitor interval). Close attempts are
    throttled by MIN_CLOSE_RETRY_SEC so the broker is not hammered.
    We track close attempts in bot_state.
    After MAX_CLOSE_ATTEMPTS the trade is flagged STUCK and skipped
    until human intervenes. Dashboard shows STUCK trades.

  Stock positions are only monitored during market hours
  (Mon-Fri 09:30-16:00 ET). Crypto is monitored 24/7.
=============================================================
"""

import json as _json
import logging
import time
import threading
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Callable

import numpy as np
import pandas as pd

import config
from data.database import db
from core.risk_manager import risk_manager
from core.strategy_registry import (
    TIME_STOP_EXEMPT,
    EARLY_LOSS_LIFECYCLE_EXEMPT,
    EARLY_LOSS_MIN_PCT,
    PERF_CHECK_2HR_MIN_PCT,
    PERF_CHECK_5HR_MIN_PCT,
)

logger = logging.getLogger(__name__)

# ── Stale position check ─────────────────────────────────────────────────────
STALE_THRESHOLD_SEC = 3 * 60 * 60       # 3 hours before ADX/DI stale check fires

# ADX threshold below which trend is considered stalled
ADX_STALE_THRESHOLD = 25.0

PM_DEBUG = False



# ── NEW: Time-based exit thresholds ──────────────────────────────────────────
# Performance-contingent: close if profit is below threshold after N hours.
# Prevents capital being locked in trades that never got going.
# NOTE: grid_bot trades are EXEMPT from all time stops (see _check_performance_time_stop)
# Grid strategies need time to oscillate — time stops kill them prematurely.
PERF_CHECK_2HR_SEC     = 2 * 60 * 60    # 2 hours — free up capital if going nowhere
# PERF_CHECK_2HR_MIN_PCT: need at least 0.2% profit by 2hr — canonical value
# now lives in core/strategy_registry.py (imported above) so backtester.py
# can share it instead of re-declaring its own copy.

PERF_CHECK_5HR_SEC     = 5 * 60 * 60    # 5 hours — too slow for a day trade
# PERF_CHECK_5HR_MIN_PCT: need at least 1.0% profit by 5hr — see import above.

# Legacy aliases — kept so any external references don't break during migration
PERF_CHECK_1HR_SEC     = PERF_CHECK_2HR_SEC
PERF_CHECK_1HR_MIN_PCT = PERF_CHECK_2HR_MIN_PCT
PERF_CHECK_3HR_SEC     = PERF_CHECK_5HR_SEC
PERF_CHECK_3HR_MIN_PCT = PERF_CHECK_5HR_MIN_PCT

HARD_TIME_STOP_SEC     = 8 * 60 * 60    # 8 hours — hard kill (was 3.5hr)

# Early loss check: if trade is negative AND worsening at 30 minutes, kill it.
# Catches trades where thesis was wrong from the start.
EARLY_LOSS_CHECK_SEC   = 30 * 60        # 30 minutes (was 20min — too tight)
# EARLY_LOSS_MIN_PCT: if worse than -0.5% AND still falling — see import above
# (was -0.3%; note config.EARLY_LOSS_MIN_PCT is a stale, unrelated -0.3
# leftover that nothing here reads).

# Breakout fast-fail: real breakouts move immediately. If flat or negative at
# 10 minutes (2 bars on 5m), the setup failed — take the tiny loss and move on.
# This keeps losses at $5-15 instead of riding to the full 2-4.5% stop.
BREAKOUT_FAST_FAIL_SEC      = 10 * 60   # 10 minutes — 2 bars on 5m
BREAKOUT_FAST_FAIL_MAX_SEC  = 20 * 60   # 20 minutes — window closes, early_loss takes over
BREAKOUT_FAST_FAIL_MIN_PCT  = 0.10      # must be up at least 0.1% to NOT fast-fail

# Breakout loss cap: cut failing breakout_scanner trades before they hit the
# full hard stop. This is a maximum-loss guard, not only a dead-on-arrival test.
BREAKOUT_EARLY_LOSS_CAP_SEC = int(
    getattr(config, "BREAKOUT_EARLY_LOSS_CAP_SEC", 3 * 60)
)
BREAKOUT_EARLY_LOSS_CAP_PCT = float(
    getattr(config, "BREAKOUT_EARLY_LOSS_CAP_PCT", -0.75)
)
# Pivot point break exit
# Uses last N bars to calculate classic floor trader pivots (PP, S1, S2, R1, R2)
PIVOT_BARS             = 20             # bars to use for pivot calculation

# ── EOD close ────────────────────────────────────────────────────────────────
EOD_CLOSE_HOUR   = 15
EOD_CLOSE_MINUTE = 45

# ── Max close attempts ────────────────────────────────────────────────────────
# Raised from 3 to 8 — 3 was too low, a brief API hiccup caused permanent STUCK.
# With 30s monitor interval this gives 4 minutes of retries before flagging STUCK.
MAX_CLOSE_ATTEMPTS = 8

# Minimum seconds between close attempts — prevents hammering the broker API
# on repeated failures and gives TWS/Alpaca time to recover from transient errors.
MIN_CLOSE_RETRY_SEC = 60   # wait at least 60s between failed close attempts

# Missing Kraken exchange stops are retried with backoff. Software stop-loss
# checks still run every monitor pass while the exchange stop is absent.
KRAKEN_STOP_RESTORE_BASE_RETRY_SEC = int(
    getattr(config, "KRAKEN_STOP_RESTORE_BASE_RETRY_SEC", 60)
)
KRAKEN_STOP_RESTORE_MAX_RETRY_SEC = int(
    getattr(config, "KRAKEN_STOP_RESTORE_MAX_RETRY_SEC", 15 * 60)
)


def _is_breakout_trade(trade: dict) -> bool:
    scanner_strategies = {"breakout_scanner", "funding_scanner", "gap_scanner"}
    if trade.get("strategy_name") in scanner_strategies:
        return True
    try:
        meta = _json.loads(trade.get("indicators_json") or "{}")
        return (
            meta.get("strategy_name") in scanner_strategies
            or meta.get("signal_source") in scanner_strategies
        )
    except Exception:
        return False


def _is_externally_managed_future(trade: dict) -> bool:
    if trade.get("asset_class") == "future" or trade.get("strategy_name") == "emt":
        return True
    try:
        meta = _json.loads(trade.get("indicators_json") or "{}")
        return meta.get("strategy_name") == "emt" or meta.get("signal_source") == "emt"
    except Exception:
        return False


def _stock_market_open() -> bool:
    from core.market_calendar import is_us_equity_regular_session_now

    return is_us_equity_regular_session_now()


def _approaching_eod() -> bool:
    """Returns True if it's time to close all stock positions (15:45 ET)."""
    from core.market_calendar import EASTERN, is_us_equity_market_holiday

    now_et = datetime.now(EASTERN)
    if now_et.weekday() > 4 or is_us_equity_market_holiday(now_et.date()):
        return False

    at_or_after = (
        now_et.hour > EOD_CLOSE_HOUR or
        (now_et.hour == EOD_CLOSE_HOUR and now_et.minute >= EOD_CLOSE_MINUTE)
    )
    before_close = now_et.hour < 16
    return at_or_after and before_close


def _parse_entry_time_local(trade: Dict) -> Optional[datetime]:
    """Parse trade entry time under the DB local-time policy."""
    try:
        entry_raw = trade.get("entry_time", "")
        if not entry_raw:
            return None
        entry_dt = pd.to_datetime(entry_raw)
        if hasattr(entry_dt, "to_pydatetime"):
            entry_dt = entry_dt.to_pydatetime()

        now_local = datetime.now()
        if entry_dt.tzinfo is not None:
            entry_dt = entry_dt.astimezone().replace(tzinfo=None)
        elif entry_dt > now_local and (entry_dt - now_local).total_seconds() <= 8.5 * 3600:
            entry_dt = entry_dt - timedelta(hours=7)
        return entry_dt
    except Exception:
        return None


def _get_position_age_seconds(trade: Dict) -> float:
    """Return how many seconds a position has been open."""
    try:
        entry_dt = _parse_entry_time_local(trade)
        if entry_dt is None:
            return 0.0
        return max(0.0, (datetime.now() - entry_dt).total_seconds())
    except Exception:
        return 0.0


def _scanner_stop_side(direction: str) -> str:
    return "sell" if direction == "long" else "buy"


class PositionMonitor:
    """
    Continuously monitors all open positions.
    Runs in its own background thread so it never blocks the scanner.
    """

    def __init__(self, db_ref=None, trade_executor=None):
        self._db            = db_ref or db
        self._executor      = trade_executor
        self.running        = False
        self.check_interval = 10   # reduced from 30s — faster SL detection
        self._thread        = None
        self._on_breakout_win_closed: Optional[Callable] = None
        # Peak price tracker — in-memory, per trade_id.
        # Resets on restart (acceptable — worst case SL trails from entry on restart).
        # Tracks the highest price seen for longs (lowest for shorts) so the ratchet
        # trails from the BEST price ever seen, not just the current price.
        self._peak_prices: dict = {}   # {trade_id: peak_price}
        # Duplicate-close guard: prevents monitor thread and dashboard HTTP thread
        # from both submitting a close order for the same trade simultaneously.
        self._closing_lock         = threading.Lock()
        self._closing_in_progress: set = set()

    def set_breakout_win_callback(
        self, cb: Callable[[str, bool, float, str], None]
    ) -> None:
        self._on_breakout_win_closed = cb

    def _get_executor(self):
        if self._executor:
            return self._executor
        from core.trade_executor import executor
        return executor

    def _get_scanner(self):
        from scanners.market_scanner import scanner
        return scanner

    def _confirmed_monitor_price(
        self, trade: Dict, current_price: float, asset_class: str
    ) -> Optional[float]:
        """
        Reject crypto monitor ticks that show a huge move but disagree with Kraken.

        Scanner prices can occasionally come from a stale/new-listing feed print.
        A normal entry-distance sanity check will not catch a fake +40% crypto move,
        but that tick can still trigger partial TP, TP close, and ratchet writes.
        For large claimed moves, require the monitor price to agree with the broker
        quote before using it for any money-recording decision.
        """
        if asset_class != "crypto":
            return current_price

        entry_price = float(trade.get("entry_price") or 0)
        if entry_price <= 0 or current_price <= 0:
            return current_price

        move_pct = abs(current_price - entry_price) / entry_price * 100
        confirm_move_pct = float(getattr(
            config, "CRYPTO_MONITOR_BROKER_CONFIRM_MOVE_PCT", 20.0
        ))
        if move_pct < confirm_move_pct:
            return current_price

        symbol = trade.get("symbol", "")
        try:
            broker_price = self._get_executor().kraken.get_current_price(symbol)
        except Exception as exc:
            logger.warning(
                f"[PRICE CONFIRM] {symbol}: monitor price ${current_price:.6f} "
                f"is {move_pct:.1f}% from entry but broker quote failed ({exc}); "
                "skipping this cycle"
            )
            return None

        if not broker_price or broker_price <= 0:
            logger.warning(
                f"[PRICE CONFIRM] {symbol}: monitor price ${current_price:.6f} "
                f"is {move_pct:.1f}% from entry but broker quote unavailable; "
                "skipping this cycle"
            )
            return None

        diff_pct = abs(current_price - broker_price) / broker_price * 100
        max_diff_pct = float(getattr(
            config, "CRYPTO_MONITOR_BROKER_MAX_DIFF_PCT", 5.0
        ))
        if diff_pct > max_diff_pct:
            broker_move_pct = abs(broker_price - entry_price) / entry_price * 100
            logger.warning(
                f"[PRICE CONFIRM] {symbol}: monitor=${current_price:.6f} "
                f"({move_pct:.1f}% from entry) disagrees with broker="
                f"${broker_price:.6f} ({broker_move_pct:.1f}% from entry) by "
                f"{diff_pct:.1f}% > {max_diff_pct:.1f}% — suspected bad tick; "
                "skipping this cycle"
            )
            return None

        return current_price

    def _update_trade_excursions(self, trade: Dict, pnl_pct: float) -> None:
        """Persist max favorable/adverse excursion seen while a trade is open."""
        try:
            trade_id = trade["trade_id"]
            mfe_key = f"mfe_pct_{trade_id}"
            mae_key = f"mae_pct_{trade_id}"
            old_mfe = float(self._db.get_state(mfe_key, default=0) or 0)
            old_mae = float(self._db.get_state(mae_key, default=0) or 0)
            mfe = max(old_mfe, pnl_pct)
            mae = min(old_mae, pnl_pct)
            if mfe == old_mfe and mae == old_mae:
                return
            self._db.set_state(mfe_key, round(mfe, 4))
            self._db.set_state(mae_key, round(mae, 4))
            self._db.update_trade_diagnostics(trade_id, mfe_pct=mfe, mae_pct=mae)
            trade["mfe_pct"] = mfe
            trade["mae_pct"] = mae
        except Exception as e:
            logger.debug(f"MFE/MAE update failed for {trade.get('symbol')}: {e}")

    def _maybe_take_scanner_partial(
        self, trade: Dict, current_price: float, pnl_pct: float
    ) -> bool:
        """Bank one partial profit, then confirm protection before marking it done."""
        if not getattr(config, "BREAKOUT_PARTIAL_TP_ENABLED", True):
            return False
        if not _is_breakout_trade(trade):
            return False
        if trade.get("asset_class") != "crypto":
            return False
        if int(trade.get("partial_exit_count") or 0) > 0:
            return False

        trade_id = trade["trade_id"]
        if int(self._db.get_state(f"scanner_partial_taken_{trade_id}", default=0) or 0):
            return False

        trigger = float(getattr(config, "BREAKOUT_PARTIAL_TP_TRIGGER_PCT", 1.5))
        fraction = float(getattr(config, "BREAKOUT_PARTIAL_TP_FRACTION", 0.35))
        if pnl_pct < trigger:
            return False

        outcome = self._get_executor().close_partial_trade(
            trade, current_price, fraction, "scanner_partial_tp"
        )
        partial_booked = bool(outcome)
        refresh_required = partial_booked or bool(
            getattr(outcome, "stop_refresh_required", False)
        )
        if not refresh_required:
            return False

        if partial_booked:
            logger.info(
                f"[SCANNER PARTIAL] {trade['symbol']}: partial fill booked at "
                f"{pnl_pct:+.2f}% | remaining position will keep trailing"
            )
            if getattr(outcome, "full_fill", False):
                self._record_close_in_db(
                    trade, float(outcome.fill_price), "scanner_partial_full_fill"
                )
                trade["status"] = "closed"
                trade["exit_price"] = float(outcome.fill_price)
                self._db.set_state(f"kraken_full_reconcile_{trade_id}", 0)
                return True

        # The partial close cancels all exchange-side orders.  Confirm the
        # replacement stop before persisting the one-shot scanner marker so a
        # falsey/failed stop placement enters the existing restore backoff.
        stop_loss = float(trade.get("stop_loss") or 0)
        qty = float(trade.get("quantity") or 0)
        old_stop_id = trade.get("stop_order_id") or ""
        stop_confirmed = False
        if stop_loss > 0 and qty > 0:
            try:
                _leverage = int(
                    _json.loads(trade.get("indicators_json") or "{}").get("kraken_leverage", 0)
                )
                stop_id = self._get_executor().kraken.place_stop_order(
                    trade["symbol"], qty, _scanner_stop_side(trade["direction"]),
                    round(stop_loss, 6), leverage=_leverage
                )
                if stop_id:
                    self._db.update_trade_order_ids(trade_id, stop_order_id=stop_id)
                    trade["stop_order_id"] = stop_id
                    stop_confirmed = True
            except Exception as exc:
                logger.warning(
                    f"[SCANNER PARTIAL] {trade['symbol']}: could not refresh "
                    f"remaining stop after partial: {exc}"
                )

        if stop_confirmed or qty <= 0:
            if partial_booked:
                self._db.set_state(f"scanner_partial_taken_{trade_id}", 1)
            elif getattr(outcome, "retryable", False):
                self._db.set_state(
                    f"scanner_partial_retry_after_{trade_id}",
                    time.time() + float(getattr(config, "KRAKEN_PARTIAL_ZERO_RETRY_SEC", 60)),
                )
        else:
            try:
                if partial_booked:
                    self._db.set_state(f"scanner_partial_pending_{trade_id}", 1)
                self._mark_kraken_stop_unprotected(
                    trade, trade_id, trade["symbol"], old_stop_id, stop_loss
                )
            except Exception as exc:
                logger.critical(
                    f"[SCANNER PARTIAL] {trade['symbol']}: failed to persist "
                    f"unprotected-stop recovery state: {exc}"
                )
        return partial_booked
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

    def _get_last_attempt_time(self, trade_id: str) -> float:
        """Return timestamp of last close attempt (0 if never attempted)."""
        return float(self._db.get_state(f"close_last_attempt_{trade_id}", default=0))

    def _increment_close_attempts(self, trade_id: str, symbol: str) -> int:
        count = self._get_close_attempts(trade_id) + 1
        self._db.set_state(f"close_attempts_{trade_id}", count)
        self._db.set_state(f"close_last_attempt_{trade_id}",
                           datetime.now(timezone.utc).timestamp())
        if count >= MAX_CLOSE_ATTEMPTS:
            self._db.set_state(f"close_stuck_{trade_id}", 1)
            logger.error(
                f"[STUCK] {symbol}: {count} failed close attempts. "
                f"Manual intervention required. Use dashboard Close Now "
                f"button or Scripts/clear_stuck_trades.py to resolve."
            )
        return count

    def _reset_close_attempts(self, trade_id: str):
        self._db.set_state(f"close_attempts_{trade_id}", 0)
        self._db.set_state(f"close_stuck_{trade_id}", 0)

    def _is_stuck(self, trade_id: str) -> bool:
        return int(self._db.get_state(f"close_stuck_{trade_id}", default=0)) == 1

    def _ratchet_update_exchange_stop(
        self, trade: dict, trade_id: str, symbol: str, direction: str, new_sl: float
    ) -> None:
        """
        Cancel the old exchange stop order and place a new one at the ratchet price.
        Works for both paper mode (fake order ID tracking) and live mode (real cancel+replace).
        Falls back to software-only monitoring if the exchange call fails — the DB SL
        is the source of truth for the position monitor's 10s price check loop.
        """
        asset_class = trade.get("asset_class", "")
        if asset_class != "crypto":
            return   # stocks: Alpaca trailing stop handled separately
        try:
            import config as _cfg
            kraken_ex   = self._get_executor().kraken
            if kraken_ex is None:
                return
            qty         = float(trade.get("quantity") or 0)
            old_stop_id = trade.get("stop_order_id", "")
            stop_side   = "buy" if direction == "short" else "sell"
            _leverage   = int(
                _json.loads(trade.get("indicators_json") or "{}").get("kraken_leverage", 0)
            )
            new_stop_id = kraken_ex.update_stop_order(
                symbol, old_stop_id, qty, stop_side, round(new_sl, 6),
                leverage=_leverage,
            )
            if new_stop_id:
                self._db.update_trade_order_ids(trade_id, stop_order_id=new_stop_id)
                trade["stop_order_id"] = new_stop_id
                self._db.set_state(f"kraken_stop_unprotected_{trade_id}", 0)
                logger.info(
                    f"[RATCHET {'PAPER' if _cfg.KRAKEN_PAPER_MODE else 'LIVE'}] "
                    f"{symbol}: exchange stop updated → ${new_sl:.6f} "
                    f"(order {new_stop_id})"
                )
            elif new_stop_id == "" and old_stop_id:
                self._mark_kraken_stop_unprotected(
                    trade, trade_id, symbol, old_stop_id, new_sl
                )
        except Exception as _e:
            # Non-fatal: DB SL is updated, software monitor will enforce it
            logger.warning(
                f"[RATCHET] {symbol}: exchange stop update failed ({_e}) — "
                f"software monitor will enforce SL ${new_sl:.6f}"
            )

    def _mark_kraken_stop_unprotected(
        self, trade: dict, trade_id: str, symbol: str, old_stop_id: str, new_sl: float
    ) -> None:
        existing = self._db.get_state(f"kraken_stop_unprotected_{trade_id}", default={})
        attempts = int(existing.get("attempts", 0) or 0) if isinstance(existing, dict) else 0
        self._db.update_trade_order_ids(trade_id, stop_order_id="")
        trade["stop_order_id"] = ""
        self._db.set_state(
            f"kraken_stop_unprotected_{trade_id}",
            {
                "symbol": symbol,
                "cancelled_stop_order_id": old_stop_id,
                "target_stop_loss": round(float(new_sl), 6),
                "attempts": attempts,
                "last_attempt_ts": existing.get("last_attempt_ts") if isinstance(existing, dict) else 0,
            },
        )
        logger.error(
            f"[STOP UNPROTECTED] {symbol}: cleared stale stop id {old_stop_id}; "
            f"software monitor will enforce SL ${new_sl:.6f}"
        )

    def _maybe_restore_missing_kraken_stop(
        self, trade: Dict, trade_id: str, symbol: str, direction: str
    ) -> None:
        if trade.get("asset_class") != "crypto":
            return
        if trade.get("stop_order_id"):
            return

        try:
            stop_loss = round(float(trade.get("stop_loss") or 0), 6)
            qty = float(trade.get("quantity") or 0)
        except (TypeError, ValueError):
            return
        if stop_loss <= 0 or qty <= 0:
            return

        state_key = f"kraken_stop_unprotected_{trade_id}"
        state = self._db.get_state(state_key, default={})
        if not isinstance(state, dict):
            state = {}

        attempts = int(state.get("attempts", 0) or 0)
        last_attempt = float(state.get("last_attempt_ts", 0) or 0)
        retry_after = min(
            KRAKEN_STOP_RESTORE_MAX_RETRY_SEC,
            KRAKEN_STOP_RESTORE_BASE_RETRY_SEC * (2 ** min(attempts, 4)),
        )
        now_ts = time.time()
        if last_attempt and now_ts - last_attempt < retry_after:
            return

        stop_side = _scanner_stop_side(direction)
        try:
            kraken_ex = self._get_executor().kraken
            if kraken_ex is None:
                return
            _leverage = int(
                _json.loads(trade.get("indicators_json") or "{}").get("kraken_leverage", 0)
            )
            new_stop_id = kraken_ex.place_stop_order(
                symbol, qty, stop_side, stop_loss, leverage=_leverage
            )
            if new_stop_id:
                self._db.update_trade_order_ids(trade_id, stop_order_id=new_stop_id)
                trade["stop_order_id"] = new_stop_id
                self._db.set_state(state_key, 0)
                if self._db.get_state(f"scanner_partial_pending_{trade_id}", default=0):
                    self._db.set_state(f"scanner_partial_taken_{trade_id}", 1)
                    self._db.set_state(f"scanner_partial_pending_{trade_id}", 0)
                logger.warning(
                    f"[STOP RESTORED] {symbol}: restored missing Kraken stop "
                    f"@ ${stop_loss:.6f} (order {new_stop_id})"
                )
                return
        except Exception as exc:
            state["last_error"] = str(exc)

        state.update(
            {
                "symbol": symbol,
                "target_stop_loss": stop_loss,
                "attempts": attempts + 1,
                "last_attempt_ts": now_ts,
                "next_retry_sec": min(
                    KRAKEN_STOP_RESTORE_MAX_RETRY_SEC,
                    KRAKEN_STOP_RESTORE_BASE_RETRY_SEC * (2 ** min(attempts + 1, 4)),
                ),
            }
        )
        self._db.set_state(state_key, state)
        logger.error(
            f"[STOP RESTORE FAILED] {symbol}: missing Kraken stop remains; "
            f"software monitor will enforce SL ${stop_loss:.6f}; "
            f"retry in {state['next_retry_sec']}s"
        )

    def _attempt_close(self, trade: Dict, current_price: float,
                       reason: str) -> bool:
        """
        Wrapper around close_trade that tracks failed attempts.
        - Enforces MIN_CLOSE_RETRY_SEC cooldown between attempts
        - After MAX_CLOSE_ATTEMPTS failures, flags trade as STUCK
        - If broker=ibkr and close fails, automatically retries via Alpaca
        """
        trade_id = trade["trade_id"]
        symbol   = trade["symbol"]
        broker   = trade.get("broker", "")

        # ── Paper mode price clamp ─────────────────────────────────────────
        # In paper trading the monitor may catch a price AFTER it has blown
        # through the SL or overshot the TP. A real stop/limit order would
        # fill AT those levels (with only minor slippage). Clamp here so every
        # exit path gets accurate P&L — wins capped at TP, losses floored at SL.
        try:
            import config as _cfg
            asset_class = trade.get("asset_class", "")
            _is_paper = (
                (asset_class == "crypto" and getattr(_cfg, "KRAKEN_PAPER_MODE", False)) or
                (asset_class == "stock"  and getattr(_cfg, "ALPACA_PAPER_MODE", False))
            )
            if _is_paper:
                direction = trade.get("direction", "long")
                _sl = trade.get("stop_loss")
                _tp = trade.get("take_profit")
                if _sl and _tp:
                    _sl, _tp = float(_sl), float(_tp)
                    _entry = float(trade.get("entry_price") or 0)
                    _skip_ratcheted_clamp = (
                        reason == "trailing_stop"
                        and _entry > 0
                        and (
                            (
                                direction == "long"
                                and _sl > _entry
                                and current_price < _entry
                            )
                            or (
                                direction == "short"
                                and 0 < _sl < _entry
                                and current_price > _entry
                            )
                        )
                    )
                    if _skip_ratcheted_clamp:
                        logger.warning(
                            f"[PAPER CLAMP SANITY] {symbol}: ratcheted SL "
                            f"${_sl:.6f} conflicts with sanity fill "
                            f"${current_price:.6f}; keeping sanity fill"
                        )
                    elif direction == "long":
                        current_price = min(current_price, _tp)   # cap wins at TP
                        current_price = max(current_price, _sl)   # floor losses at SL
                    else:  # short: TP is lower, SL is higher
                        current_price = max(current_price, _tp)   # cap wins at TP
                        current_price = min(current_price, _sl)   # floor losses at SL
        except Exception:
            pass  # never block a close over a clamp error

        # ── Duplicate-close guard ─────────────────────────────────────────
        # Monitor thread and dashboard HTTP thread can both trigger closes
        # simultaneously. The set check + add is atomic under the lock, so
        # only one caller proceeds to the broker; the other returns False.
        with self._closing_lock:
            if trade_id in self._closing_in_progress:
                logger.debug(f"[CLOSE GUARD] {symbol}: close already in progress, skipping")
                return False
            self._closing_in_progress.add(trade_id)

        try:
            return self._attempt_close_inner(trade, trade_id, symbol, broker,
                                             current_price, reason)
        finally:
            with self._closing_lock:
                self._closing_in_progress.discard(trade_id)

    def _attempt_close_inner(self, trade: Dict, trade_id: str, symbol: str,
                              broker: str, current_price: float, reason: str) -> bool:
        # ── Cooldown: don't hammer broker on repeated failures ─────────────
        last_attempt = self._get_last_attempt_time(trade_id)
        if last_attempt > 0:
            elapsed = datetime.now(timezone.utc).timestamp() - last_attempt
            if elapsed < MIN_CLOSE_RETRY_SEC:
                logger.debug(
                    f"[CLOSE COOLDOWN] {symbol}: last attempt {elapsed:.0f}s ago, "
                    f"waiting {MIN_CLOSE_RETRY_SEC - elapsed:.0f}s more before retry"
                )
                return False

        success = self._get_executor().close_trade(trade, current_price, reason)

        if success:
            self._reset_close_attempts(trade_id)
            if self._on_breakout_win_closed and _is_breakout_trade(trade):
                direction = trade.get("direction", "long")
                entry     = trade.get("entry_price", 0)
                won = (
                    (direction == "long"  and current_price > entry) or
                    (direction == "short" and current_price < entry)
                )
                try:
                    self._on_breakout_win_closed(symbol, won, current_price, direction)
                except Exception:
                    pass
            return True

        # ── IBKR fallback: if IBKR close fails try Alpaca directly ────────
        # This handles the common case where TWS is not running but Alpaca is.
        if broker == "ibkr" and trade.get("asset_class") == "stock":
            logger.warning(
                f"[IBKR FALLBACK] {symbol}: IBKR close failed, "
                f"attempting Alpaca fallback close..."
            )
            try:
                from core.trade_executor import AlpacaExecutor
                alpaca = AlpacaExecutor()
                # close_position only takes symbol — no price or reason args
                fallback_success = alpaca.close_position(symbol)
                if fallback_success:
                    logger.info(
                        f"[IBKR FALLBACK] {symbol}: Alpaca fallback close succeeded"
                    )
                    # executor.close_trade() failed earlier so the DB trade is still
                    # open.  Record the close here to prevent a ghost trade; calling
                    # _record_close_in_db() also resets close attempts and updates the
                    # risk_manager session so daily P&L and loss counters stay correct.
                    self._record_close_in_db(trade, current_price, "ibkr_fallback_close")
                    return True
                else:
                    logger.warning(
                        f"[IBKR FALLBACK] {symbol}: Alpaca fallback also failed"
                    )
            except Exception as e:
                logger.error(f"[IBKR FALLBACK] {symbol}: fallback error: {e}")

        count = self._increment_close_attempts(trade_id, symbol)
        logger.warning(
            f"Close attempt {count}/{MAX_CLOSE_ATTEMPTS} failed for "
            f"{symbol} | reason={reason} | "
            f"next retry in {MIN_CLOSE_RETRY_SEC}s"
        )
        return False

    # ------------------------------------------------------------------
    #  DB-ONLY CLOSE HELPER
    # ------------------------------------------------------------------

    def _record_close_in_db(self, trade: Dict, exit_price: float,
                             exit_reason: str) -> None:
        """
        Record a trade close directly in the DB without submitting a broker order.

        Use when the position is already confirmed closed on the exchange
        (broker reconciliation) or when a broker fallback close succeeded outside
        the normal executor flow (IBKR → Alpaca fallback).  Going through
        executor.close_trade() in these cases would re-submit a close order to
        a broker that no longer holds the position, which would fail and
        loop into the STUCK retry logic.

        Handles: DB close, risk_manager session update, tax event.
        """
        trade_id    = trade["trade_id"]
        direction   = trade["direction"]
        entry_price = trade["entry_price"]
        qty         = trade["quantity"]
        symbol      = trade["symbol"]

        asset_class = trade.get("asset_class", "crypto")

        if direction == "long":
            pnl     = (exit_price - entry_price) * qty
            pnl_pct = ((exit_price / entry_price) - 1) * 100 if entry_price else 0.0
        else:
            pnl     = (entry_price - exit_price) * qty
            pnl_pct = ((entry_price / exit_price) - 1) * 100 if exit_price else 0.0

        # Fee simulation — matches backtester rates
        if asset_class == "crypto":
            fee_rt_pct = (config.BT_COMMISSION_CRYPTO_PCT + config.BT_SLIPPAGE_CRYPTO_PCT) / 100 * 2
        else:
            fee_rt_pct = (config.BT_COMMISSION_STOCK_PCT + config.BT_SLIPPAGE_STOCK_PCT) / 100 * 2
        fees_paid = round(entry_price * qty * fee_rt_pct, 4)
        pnl       = pnl - fees_paid

        pnl     = round(pnl, 4)
        pnl_pct = round(pnl_pct, 4)

        self._db.close_trade(
            trade_id    = trade_id,
            exit_price  = exit_price,
            exit_reason = exit_reason,
            pnl         = pnl,
            pnl_pct     = pnl_pct,
            fees_paid   = fees_paid,
        )

        try:
            full_trade = {**trade, "exit_time": datetime.now().isoformat(),
                          "exit_price": exit_price, "status": "closed",
                          "fees_paid": fees_paid}
            self._db.record_tax_event(full_trade)
        except Exception:
            pass

        risk_manager.record_trade_result(pnl=pnl, trade_won=(pnl > 0), symbol=symbol,
                                          strategy=trade.get("strategy_name", ""))
        self._reset_close_attempts(trade_id)
        if self._on_breakout_win_closed and _is_breakout_trade(trade):
            try:
                self._on_breakout_win_closed(
                    symbol, pnl > 0, exit_price, trade.get("direction", "long")
                )
            except Exception:
                pass
        # Clean up per-trade state keys so they don't accumulate in bot_state
        for _key in (f"sl_raise_count_{trade_id}", f"early_loss_checked_{trade_id}"):
            try:
                self._db.set_state(_key, None)
            except Exception:
                pass

        logger.info(
            f"[DB CLOSE] {symbol}: recorded close @ ${exit_price:.4f} | "
            f"reason={exit_reason} | pnl=${pnl:.2f} ({pnl_pct:+.2f}%)"
        )

    # ------------------------------------------------------------------
    #  NEW: PERFORMANCE-CONTINGENT TIME STOPS
    # ------------------------------------------------------------------

    def _check_performance_time_stop(
        self, trade: Dict, pnl_pct: float, age_seconds: float
    ) -> Optional[str]:
        """
        Kill trades that aren't performing within expected timeframes.

        Logic:
          - After 30 min: if pnl < -0.5% AND still moving wrong → early exit
          - After 2 hours: if pnl < 0.2% → going nowhere, free up capital
          - After 5 hours: if pnl < 1.0% → too slow for a day trade
          - After 8 hours: hard kill regardless of profit

        Returns exit reason string or None if trade should continue.
        """
        symbol    = trade["symbol"]
        direction = trade["direction"]
        trade_id  = trade["trade_id"]
        strategy  = trade.get("strategy_name", "")

        # ── Fee-hurdle floor (Opus audit 2026-05-29) ───────────────────
        # A "perf time stop" that closes a crypto trade for being below
        # 0.2% booked a guaranteed net loss (round-trip fee = 0.62%) AND
        # truncated winners that simply needed more time. Raise the floor
        # above the asset's fee hurdle, and on crypto only cut when the
        # trade is genuinely NEGATIVE — let slow-but-green trades run.
        _asset = trade.get("asset_class", "crypto")
        if _asset == "crypto":
            _hurdle    = getattr(config, "FEE_RT_CRYPTO_PCT", 0.62)
            _floor_2hr = 0.0                           # crypto: only cut if losing
            _floor_5hr = round(_hurdle + 0.40, 2)      # ~1.02 % net target
        else:
            _hurdle    = getattr(config, "FEE_RT_STOCK_PCT", 0.02)
            _floor_2hr = max(PERF_CHECK_2HR_MIN_PCT, round(_hurdle + 0.10, 2))
            _floor_5hr = max(PERF_CHECK_5HR_MIN_PCT, round(_hurdle + 0.30, 2))

        # ── Strategy-defined time stop exemption ──────────────────────
        # Strategies that manage their own exit timing declare this via
        # time_stop_profile = "strategy_defined" on their class.
        # The position monitor must not override their thesis with generic
        # intraday time stops.
        #
        # DCA accumulator: slow oscillation strategy; time stops inappropriate.
        # Grid bot: profits from range oscillations across many hours.
        # MR mean-reversion 1h strategies: 24/36/48-bar holds are intentional;
        # the 8hr generic stop would cut trades before the thesis plays out.
        # ── Opus live-vs-paper audit 2026-05-29 ──────────────────────────────
        # This set MUST mirror intelligence/backtester.py's exempt set — both
        # now import TIME_STOP_EXEMPT from core/strategy_registry.py (see
        # import at top of file) instead of each declaring their own copy,
        # so the two can no longer drift apart independently. Previously live
        # exempted only 6 strategies while the backtester exempted ~30, then
        # later drifted again the other direction (backtester exempted 11
        # strategies live did not) — both were instances of the same root
        # cause: two hand-maintained literals with no shared source.
        if strategy in TIME_STOP_EXEMPT:
            logger.debug(
                f"[TIME STOP EXEMPT] {symbol}: strategy={strategy} "
                f"manages its own exit timing — skipping performance time stops"
            )
            return None

        # ── Hard time stop: 8 hours ───────────────────────────────────
        if age_seconds >= HARD_TIME_STOP_SEC:
            logger.info(
                f"[HARD TIME STOP] {symbol}: open {age_seconds/3600:.1f}hrs — "
                f"8hr max reached | P&L {pnl_pct:+.2f}% | closing"
            )
            return "hard_time_stop"

        # ── 5-hour performance check ──────────────────────────────────
        if age_seconds >= PERF_CHECK_5HR_SEC:
            if pnl_pct < _floor_5hr:
                logger.info(
                    f"[PERF TIME STOP 5HR] {symbol}: open {age_seconds/3600:.1f}hrs | "
                    f"P&L {pnl_pct:+.2f}% < {_floor_5hr}% target — closing"
                )
                return "perf_time_stop_3hr"   # reason code unchanged for DB compatibility

        # ── 2-hour performance check ──────────────────────────────────
        if age_seconds >= PERF_CHECK_2HR_SEC:
            if pnl_pct < _floor_2hr:
                logger.info(
                    f"[PERF TIME STOP 2HR] {symbol}: open {age_seconds/3600:.1f}hrs | "
                    f"P&L {pnl_pct:+.2f}% < {_floor_2hr}% target — closing"
                )
                return "perf_time_stop_1hr"   # reason code unchanged for DB compatibility

        return None

    # ------------------------------------------------------------------
    #  NEW: EARLY LOSS IDENTIFICATION (30 MIN CHECK)
    # ------------------------------------------------------------------

    def _check_early_loss(
        self, trade: Dict, current_price: float, pnl_pct: float, age_seconds: float
    ) -> Optional[str]:
        """
        Catch trades where the thesis was wrong from the start.
        At 30 minutes: if trade is negative AND still moving against us → close.
        This limits losses on trades that immediately went the wrong way
        rather than waiting for the full stop loss to be hit.

        Uses last 3 bars to confirm the move is still going against us,
        not just a brief wick.
        """
        symbol    = trade["symbol"]
        direction = trade["direction"]
        trade_id  = trade["trade_id"]

        # Only check in the 30-60 minute window (don't re-check after)
        if age_seconds < EARLY_LOSS_CHECK_SEC:
            return None
        if age_seconds > EARLY_LOSS_CHECK_SEC * 2:  # 60 minutes max window
            return None

        # Already checked this trade at 30 min?
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
                f"[EARLY CHECK] {symbol}: P&L {pnl_pct:+.2f}% at 30min — OK"
            )
            return None

        # Trade is negative — check if still moving against us
        bars = self._get_bars(symbol, trade["asset_class"], limit=5)
        if bars is None or len(bars) < 3:
            logger.info(
                f"[EARLY LOSS EXIT] {symbol}: P&L {pnl_pct:+.2f}% at 30min, "
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
                f"[EARLY LOSS EXIT] {symbol}: P&L {pnl_pct:+.2f}% at 30min "
                f"AND still moving wrong direction — thesis failed, closing"
            )
            return "early_loss"
        else:
            logger.info(
                f"[EARLY CHECK] {symbol}: P&L {pnl_pct:+.2f}% at 30min but "
                f"price stabilizing — holding, watching stop loss"
            )
            return None

    # ------------------------------------------------------------------
    #  REVERSAL CANDLE EXIT  (breakout_scanner + vwap_confirmed_orb)
    # ------------------------------------------------------------------

    def _check_reversal_candles(
        self, trade: Dict, age_seconds: float, pnl_pct: float = 0.0
    ) -> Optional[str]:
        """
        If 2+ consecutive CLOSED candles move against the trade direction
        within the first 30 minutes, the breakout has reversed — exit
        immediately rather than riding to the stop loss.

        Logic:
          Long:  last 2 closed closes are BOTH lower than their open (bearish body)
                 AND both lower than the candle before them → confirmed reversal
          Short: last 2 closed closes are BOTH higher than their open (bullish body)
                 AND both higher than the candle before them → confirmed reversal

        Only fires for breakout_scanner and vwap_confirmed_orb trades.
        Only within the first 30 minutes (after that, fast-fail / early-loss takes over).
        Only fires once per trade.
        """
        strategy = trade.get("strategy_name", "")
        if strategy not in ("breakout_scanner", "vwap_confirmed_orb"):
            return None

        # Opus diff 08: only fire when trade is losing — don't cut profitable breakouts early
        if pnl_pct > 0:
            return None

        # Only in first 30 minutes
        if age_seconds > 30 * 60:
            return None

        # Need at least 2 closed bars after entry — wait at least 2 bars (10 min on 5m)
        if age_seconds < 10 * 60:
            return None

        trade_id  = trade["trade_id"]
        symbol    = trade["symbol"]
        direction = trade["direction"]

        # Only fire once per trade
        already = int(self._db.get_state(f"reversal_check_{trade_id}", default=0))
        if already:
            return None

        bars = self._get_bars(symbol, trade["asset_class"], limit=6)
        if bars is None or len(bars) < 3:
            return None

        self._db.set_state(f"reversal_check_{trade_id}", 1)

        # Last 2 fully closed candles (bars are closed-only from _get_bars)
        c1 = bars.iloc[-2]   # older of the two
        c2 = bars.iloc[-1]   # most recent closed

        if direction == "long":
            # Both candles bearish body AND c2 closed lower than c1
            c1_bearish = float(c1["close"]) < float(c1["open"])
            c2_bearish = float(c2["close"]) < float(c2["open"])
            c2_lower   = float(c2["close"]) < float(c1["close"])
            if c1_bearish and c2_bearish and c2_lower:
                logger.info(
                    f"[REVERSAL EXIT] {symbol}: 2 consecutive bearish candles after long entry "
                    f"— c1 close={c1['close']:.4f} c2 close={c2['close']:.4f} — exiting"
                )
                return "reversal_candles"
        else:  # short
            c1_bullish = float(c1["close"]) > float(c1["open"])
            c2_bullish = float(c2["close"]) > float(c2["open"])
            c2_higher  = float(c2["close"]) > float(c1["close"])
            if c1_bullish and c2_bullish and c2_higher:
                logger.info(
                    f"[REVERSAL EXIT] {symbol}: 2 consecutive bullish candles after short entry "
                    f"— c1 close={c1['close']:.4f} c2 close={c2['close']:.4f} — exiting"
                )
                return "reversal_candles"

        logger.debug(
            f"[REVERSAL EXIT] {symbol}: no reversal pattern — holding "
            f"(c1 {'bear' if float(c1['close']) < float(c1['open']) else 'bull'} "
            f"c2 {'bear' if float(c2['close']) < float(c2['open']) else 'bull'})"
        )
        return None

    # ------------------------------------------------------------------
    #  BREAKOUT FAST-FAIL (10-20 min window, breakout_scanner only)
    # ------------------------------------------------------------------

    def _check_breakout_fast_fail(
        self, trade: Dict, current_price: float, pnl_pct: float, age_seconds: float
    ) -> Optional[str]:
        """
        Breakout-specific fast-fail: real breakouts move immediately.
        If price is flat or negative at 10 minutes the thesis failed — exit
        with a tiny loss rather than riding to the full 2-4.5% stop.

        Window: 10-20 minutes after entry (2-4 bars on 5m).
        After 20 min the regular early_loss check takes over.

        Only fires for breakout_scanner trades.
        """
        if not _is_breakout_trade(trade):
            return None

        if not getattr(config, "BREAKOUT_FAST_FAIL_ENABLED", True):
            return None

        # Only in the 10-20 minute window
        if age_seconds < BREAKOUT_FAST_FAIL_SEC:
            return None
        if age_seconds > BREAKOUT_FAST_FAIL_MAX_SEC:
            return None

        trade_id = trade["trade_id"]
        symbol   = trade["symbol"]

        # Only fire once per trade
        already_checked = int(
            self._db.get_state(f"breakout_fast_fail_checked_{trade_id}", default=0)
        )
        if already_checked:
            return None
        self._db.set_state(f"breakout_fast_fail_checked_{trade_id}", 1)

        # If up by threshold — thesis working, let it run
        if pnl_pct >= BREAKOUT_FAST_FAIL_MIN_PCT:
            logger.info(
                f"[BREAKOUT FAST-FAIL] {symbol}: P&L {pnl_pct:+.2f}% at 10min "
                f">= {BREAKOUT_FAST_FAIL_MIN_PCT}% — breakout confirmed, holding"
            )
            return None

        # Flat or negative — thesis failed immediately, cut it clean
        logger.info(
            f"[BREAKOUT FAST-FAIL] {symbol}: P&L {pnl_pct:+.2f}% at 10min "
            f"< {BREAKOUT_FAST_FAIL_MIN_PCT}% threshold — breakout failed, "
            f"cutting before full stop | price=${current_price:.4f}"
        )
        return "breakout_fast_fail"

    def _check_breakout_early_loss_cap(
        self, trade: Dict, current_price: float, pnl_pct: float, age_seconds: float
    ) -> Optional[str]:
        """
        Breakout-specific maximum loss guard.

        This is intentionally narrower than _is_breakout_trade(): it applies
        only to breakout_scanner, because funding/gap scanners need separate
        evidence before sharing the same emergency exit.
        """
        strategy = trade.get("strategy_name", "")
        if strategy != "breakout_scanner":
            return None

        if not getattr(config, "BREAKOUT_EARLY_LOSS_CAP_ENABLED", True):
            return None

        if age_seconds < BREAKOUT_EARLY_LOSS_CAP_SEC:
            return None

        if pnl_pct > BREAKOUT_EARLY_LOSS_CAP_PCT:
            return None

        symbol = trade["symbol"]
        mfe_pct = float(trade.get("mfe_pct") or 0.0)
        logger.info(
            f"[BREAKOUT LOSS-CAP] {symbol}: P&L {pnl_pct:+.2f}% "
            f"after {age_seconds/60:.1f}min with MFE {mfe_pct:+.2f}% — "
            f"cutting before full stop | price=${current_price:.4f}"
        )
        return "breakout_loss_cap"

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

        if not all(np.isfinite(v) for v in (adx, plus_di, minus_di)):
            logger.warning(
                f"[STALE EXIT] {symbol}: invalid ADX/DI data "
                f"ADX={adx} +DI={plus_di} -DI={minus_di} — closing"
            )
            return "stale_bad_di_data"

        if plus_di == 0.0 and minus_di == 0.0:
            logger.warning(
                f"[STALE EXIT] {symbol}: +DI and -DI are both 0.0 while "
                f"ADX={adx:.1f}; treating as missing DI data — closing"
            )
            return "stale_bad_di_data"

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

    # ------------------------------------------------------------------
    #  RSI DIP & SPIKE V4 EXIT (strategy-specific)
    # ------------------------------------------------------------------

    def _check_rsi_dip_spike_exit(
        self, trade: Dict, current_price: float, age_seconds: float
    ) -> Optional[str]:
        """
        Delegate to RSIDipSpikeV4Strategy.check_custom_exit() for live parity.

        Provides two exits that only the strategy knows about:
          - RSI neutral exit : RSI recovers past the exit threshold (55/45)
          - 48-bar max-hold  : time limit enforced by the strategy thesis

        Without this, the generic 8-hour hard stop fires first, producing
        different exit-reason distributions live vs backtested.

        _bars_held is derived from age_seconds using the 1h bar size (3600s).
        """
        import json

        symbol      = trade["symbol"]
        asset_class = trade.get("asset_class", "crypto")
        direction   = trade["direction"]

        try:
            meta = json.loads(trade.get("indicators_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            meta = {}

        # Derive bars_held from wall-clock age — rsi_dip_spike_v4 is 1h only
        meta["_bars_held"] = int(age_seconds / 3600)

        bars = self._get_bars(symbol, asset_class, limit=60, timeframe="1h")
        if bars is None or len(bars) < 15:
            logger.debug(
                f"[RSI DIP EXIT] {symbol}: insufficient bars "
                f"(got {len(bars) if bars is not None else 0}, need 15+) — skip"
            )
            return None

        try:
            from strategies.rsi_dip_spike_v4 import RSIDipSpikeV4Strategy
            return RSIDipSpikeV4Strategy().check_custom_exit(
                symbol, bars, direction, meta
            )
        except Exception as e:
            logger.debug(f"[RSI DIP EXIT] {symbol}: check_custom_exit error: {e}")
            return None

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    #  GENERIC STRATEGY CUSTOM EXIT  (Opus live-vs-paper audit 2026-05-29)
    # ------------------------------------------------------------------
    def _check_generic_custom_exit(
        self, trade: Dict, age_seconds: float
    ) -> Optional[str]:
        """
        Call the trade's strategy object's check_custom_exit() — the SAME method
        the backtester calls on every bar. This gives live/backtest parity for
        every strategy that defines a custom exit, instead of hardcoding each one.

        Returns an exit-reason string to close, or None to keep holding.
        Fails safe (returns None) on any error so a strategy bug can never wedge
        the monitor — the protective structural stop is still the hard backstop.
        """
        import json

        symbol      = trade["symbol"]
        asset_class = trade.get("asset_class", "crypto")
        direction   = trade["direction"]
        strat_name  = trade.get("strategy_name", "")
        if not strat_name:
            return None

        try:
            from strategies.strategy_engine import strategy_engine
            from strategies.base_strategy import BaseStrategy
            strat = strategy_engine._get_strategy(strat_name)
        except Exception as e:
            logger.debug(f"[CUSTOM EXIT] {symbol}: engine lookup failed: {e}")
            return None
        if strat is None:
            return None

        # Only strategies that actually override the hook are worth fetching bars
        # for; the BaseStrategy stub returns None.
        if type(strat).check_custom_exit is BaseStrategy.check_custom_exit:
            return None

        # Pick the timeframe and bar size the strategy declares for this asset.
        if asset_class == "stock":
            tf = getattr(strat, "stock_candle_timeframe", "5Min")
            bar_sec = {"1Min": 60, "5Min": 300, "15Min": 900,
                       "1Hour": 3600, "1Day": 86400}.get(tf, 300)
        else:
            tf = getattr(strat, "crypto_candle_timeframe", "1h")
            bar_sec = {"1m": 60, "5m": 300, "15m": 900,
                       "1h": 3600, "1d": 86400}.get(tf, 3600)

        try:
            meta = json.loads(trade.get("indicators_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            meta = {}
        meta["_bars_held"]   = int(age_seconds / bar_sec) if bar_sec else 0
        meta["_entry_price"] = trade.get("entry_price", 0)

        bars = self._get_bars(symbol, asset_class, limit=150, timeframe=tf)
        if bars is None or len(bars) < 30:
            return None

        try:
            return strat.check_custom_exit(symbol, bars, direction, meta)
        except Exception as e:
            logger.debug(f"[CUSTOM EXIT] {symbol}: {strat_name} check error: {e}")
            return None

    def _check_vwap_cross_exit(self, trade: Dict, current_price: float) -> bool:
        """
        VWAP cross exit for ORB trades.

        DISABLED 2026-05-31: This exit used a rolling 50-bar VWAP which is a
        different calculation from the session-anchored VWAP used for ORB entry
        confirmation.  The mismatch caused the exit to fire on the first monitor
        cycle (often within 0.1–1 min of entry) before the trade had any chance
        to move — 21 of 28 ORB trades exited this way at 0% WR.  The ORB
        backtester (PF=2.01) never included this exit; removing it restores
        live behaviour to match the backtested thesis.

        ORB exits are now handled solely by: stop_loss, take_profit, stale checks.
        """
        return False

    # ------------------------------------------------------------------
    #  MOMENTUM RIDER HELPERS
    # ------------------------------------------------------------------

    def _get_bars(self, symbol: str, asset_class: str,
                  limit: int = 25,
                  timeframe: str = None) -> Optional[pd.DataFrame]:
        """
        Fetch CLOSED bars for a symbol.

        Closed-bar guarantee: both underlying scanner methods (StockScanner.get_bars
        and CryptoScanner.get_ohlcv) call _strip_forming_bar() before returning.
        That function drops the last row when now_utc < bar_open + timeframe_duration,
        so all callers of _get_bars() receive only fully closed candles.  Exit logic
        based on EMA crosses, BB midlines, ADX/DI, and two-bar trailing stops is
        therefore never contaminated by a still-forming intrabar wick.

        `timeframe` controls which candle size is fetched:
          - Pass the trade's entry_timeframe for structural exit logic (trailing stop,
            adaptive regime exits).  A 1h-entry trade must trail on 1h bars.
          - Omit (or pass None) for monitoring overlay checks (early loss, pivot,
            ADX stale, VWAP, momentum) — those default to 5Min/5m regardless of
            entry timeframe, which is the intentional hybrid design documented in
            TIMEFRAME_LIFECYCLE_SPEC.md.

        THREADING NOTE: the scanner's ccxt exchange object is NOT thread-safe.
        The position monitor runs in its own daemon thread while the scanner loop
        runs in the main thread.  Concurrent fetch_ohlcv calls on the same ccxt
        object cause rate-limiter lock deadlocks that silently hang this thread
        (observed: monitor goes silent at 13:27, all SLs stop firing).
        Fix: use a private ccxt exchange instance that belongs only to the monitor
        thread, with an aggressive timeout so a stale connection can't hang forever.
        """
        try:
            # CandleManager cache first — eliminates ccxt thread-safety issue entirely.
            # The refresh loop pre-warms all watchlist symbols so this is usually
            # an instant SQLite read with no network call.
            from core.candle_manager import candle_manager
            tf = timeframe or ("5Min" if asset_class == "stock" else "5m")
            df = candle_manager.get(symbol, tf, limit=limit)
            if df is not None and not df.empty:
                return df
        except Exception:
            pass

        # Fallback: direct fetch (candle_manager cold start or symbol not in watchlist)
        try:
            if asset_class == "stock":
                tf = timeframe or "5Min"
                sc = self._get_scanner()
                return sc.stock_scanner.get_bars(symbol, timeframe=tf, limit=limit)
            else:
                tf = timeframe or "5m"
                ex = self._get_monitor_exchange()
                ohlcv = ex.fetch_ohlcv(symbol, tf, limit=limit + 1)
                if not ohlcv:
                    return None
                df = pd.DataFrame(
                    ohlcv,
                    columns=["timestamp", "open", "high", "low", "close", "volume"]
                )
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)
                if len(df) > 1:
                    df = df.iloc[:-1]
                return df
        except Exception as e:
            logger.debug(f"Bar fetch error for {symbol}: {e}")
            return None

    def _get_monitor_exchange(self):
        """
        Returns a dedicated ccxt Kraken exchange for this monitor thread.
        Lazily created on first call — NOT shared with the scanner.

        Short timeout (8s) so a hung TCP connection times out within one
        monitor cycle (10s interval) rather than blocking forever.
        """
        if not hasattr(self, "_monitor_exchange") or self._monitor_exchange is None:
            import ccxt as _ccxt
            self._monitor_exchange = _ccxt.kraken({
                "apiKey":          config.KRAKEN_API_KEY,
                "secret":          config.KRAKEN_SECRET_KEY,
                "enableRateLimit": True,
                "timeout":         8000,   # 8s — dies inside one 10s monitor cycle
            })
            logger.info("[MONITOR] Private ccxt exchange created for monitor thread")
        return self._monitor_exchange

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
          5.  Early loss identification (30 min)
          6.  Performance-contingent time stop (2hr)
          7.  Performance-contingent time stop (5hr)
          8.  Hard time stop (8hr)
          9.  Take-profit + momentum rider
          10. Pivot point break
          11. Stale position ADX/DI (3hr)
          12. Trailing stop update + logging
        """
        symbol           = trade["symbol"]
        asset_class      = trade["asset_class"]
        direction        = trade["direction"]
        trade_id         = trade["trade_id"]
        strategy         = trade.get("strategy_name", "")
        is_overnight     = bool(trade.get("is_overnight", False))
        entry_timeframe  = trade.get("entry_timeframe") or (
            "5Min" if asset_class == "stock" else "5m"
        )

        if PM_DEBUG:
            if PM_DEBUG:logger.info(f"[PM-DBG] ① {symbol} — entering _process_position")

        # ── 1. STUCK CHECK ───────────────────────────────────────────────
        if self._is_stuck(trade_id):
            logger.warning(
                f"[STUCK] {symbol}: skipping — exceeded {MAX_CLOSE_ATTEMPTS} "
                f"close attempts. Use dashboard Close Now to resolve."
            )
            return

        if asset_class == "crypto":
            hold = self._db.get_state(f"kraken_full_reconcile_{trade_id}", default=0)
            if hold:
                logger.critical(
                    f"[KRAKEN FULL HOLD] {symbol}: skipping monitor actions until "
                    "manual live-fill reconciliation clears the hold"
                )
                return

        if PM_DEBUG:
            logger.info(f"[PM-DBG] ② {symbol} — fetching price")
        current_price = self._get_scanner().get_current_price(symbol, asset_class)
        if current_price is None:
            logger.warning(f"Could not get price for {symbol} — skipping check")
            return
        if PM_DEBUG:
            logger.info(f"[PM-DBG] ③ {symbol} — price=${current_price:.6g}")

        # ── Price sanity gate ─────────────────────────────────────────────────
        # Reject prices that are wildly wrong relative to the trade entry.
        # A bad price feed (e.g. Kraken returning a stale listing price for a
        # new token) can look like a -99% stop-loss and force-close a live trade.
        # 80% is conservative: real stops/moves are at most a few percent.
        _entry = trade.get("entry_price", 0)
        if _entry > 0 and current_price > 0:
            _deviation = abs(current_price - _entry) / _entry
            if _deviation > 0.80:
                if asset_class == "crypto":
                    try:
                        broker_price = self._get_executor().kraken.get_current_price(symbol)
                        if broker_price and broker_price > 0:
                            broker_deviation = abs(broker_price - _entry) / _entry
                            if broker_deviation <= 0.80:
                                logger.warning(
                                    f"[PRICE SANITY FALLBACK] {symbol}: scanner "
                                    f"live=${current_price:.6f} is "
                                    f"{_deviation*100:.1f}% from entry=${_entry:.4f}; "
                                    f"using Kraken quote ${broker_price:.6f} "
                                    f"({broker_deviation*100:.1f}% from entry)"
                                )
                                current_price = broker_price
                            else:
                                logger.warning(
                                    f"[PRICE SANITY] {symbol}: scanner "
                                    f"live=${current_price:.6f} and Kraken "
                                    f"live=${broker_price:.6f} are both far from "
                                    f"entry=${_entry:.4f}; skipping this cycle"
                                )
                                return
                        else:
                            logger.warning(
                                f"[PRICE SANITY] {symbol}: live=${current_price:.6f} is "
                                f"{_deviation*100:.1f}% from entry=${_entry:.4f}; "
                                "Kraken fallback unavailable, skipping this cycle"
                            )
                            return
                    except Exception as exc:
                        logger.warning(
                            f"[PRICE SANITY] {symbol}: live=${current_price:.6f} is "
                            f"{_deviation*100:.1f}% from entry=${_entry:.4f}; "
                            f"Kraken fallback failed ({exc}), skipping this cycle"
                        )
                        return
                else:
                    logger.warning(
                        f"[PRICE SANITY] {symbol}: live=${current_price:.6f} is "
                        f"{_deviation*100:.1f}% from entry=${_entry:.4f} — "
                        f"likely bad price feed, skipping this cycle"
                    )
                    return

        confirmed_price = self._confirmed_monitor_price(
            trade, current_price, asset_class
        )
        if confirmed_price is None:
            return
        current_price = confirmed_price

        qty = trade["quantity"]
        if direction == "long":
            pnl_pct = (current_price - trade["entry_price"]) / trade["entry_price"] * 100
        else:
            pnl_pct = (trade["entry_price"] - current_price) / trade["entry_price"] * 100

        age_seconds = _get_position_age_seconds(trade)
        age_hrs     = age_seconds / 3600
        self._update_trade_excursions(trade, pnl_pct)

        logger.debug(
            f"[PM-DBG] ④ {symbol} [{entry_timeframe}]: price=${current_price:.4f} | "
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

        # ── 2b. BROKER RECONCILIATION (live mode only) ───────────────────
        # Check if the position was already closed by the exchange (SL/TP order).
        # This handles the case where Kraken fired an SL order automatically
        # and we need to record the close in our DB without trying to close again.
        if asset_class == "crypto" and not getattr(
                __import__("config"), "KRAKEN_PAPER_MODE", True):
            try:
                kraken_ex = self._get_executor().kraken
                pos = kraken_ex.get_open_position(symbol)
                if pos is None:
                    # Position gone from exchange — find the fill price
                    import time as _t
                    entry_ts = None
                    try:
                        entry_dt = _parse_entry_time_local(trade)
                        entry_ts = entry_dt.timestamp() if entry_dt else None
                    except Exception:
                        pass

                    closed_order = kraken_ex.get_recent_closed_order(
                        symbol, since_timestamp=entry_ts
                    )
                    fill_price = (
                        closed_order["fill_price"]
                        if closed_order and closed_order["fill_price"] > 0
                        else current_price
                    )
                    fill_source = "exchange order" if closed_order else "current price"
                    logger.info(
                        f"[BROKER RECONCILE] {symbol}: position no longer on Kraken — "
                        f"recording close @ ${fill_price:.4f} (via {fill_source})"
                    )
                    self._db.set_state(f"momentum_ext_{trade_id}", 0)
                    # Use _record_close_in_db, NOT _attempt_close.
                    # The position is already gone from Kraken — submitting another
                    # close order via executor.close_trade() would fail and loop
                    # into the STUCK retry.  Record directly in DB instead.
                    self._record_close_in_db(trade, fill_price, "broker_closed_sl_tp")
                    return
            except Exception as _rec_err:
                logger.debug(f"Reconciliation check error for {symbol}: {_rec_err}")

        self._maybe_restore_missing_kraken_stop(trade, trade_id, symbol, direction)

        if PM_DEBUG:
            logger.info(f"[PM-DBG] ⑤ {symbol} — checking SL/TP exits")

        # ── 2c. BREAKOUT EARLY LOSS CAP ───────────────────────────────────
        # Cut failing breakout_scanner trades before they reach the full hard
        # stop, even if they briefly moved green first.
# Temp disabled by ron 06\23\2026 as its responsible for 95pct of loss count
# breakout_loss_cap_exit = self._check_breakout_early_loss_cap(
#            trade, current_price, pnl_pct, age_seconds
#        )
#        if breakout_loss_cap_exit:
#            self._db.set_state(f"momentum_ext_{trade_id}", 0)
#            self._attempt_close(trade, current_price, breakout_loss_cap_exit)
#            return

        # ── 3. STOP-LOSS ──────────────────────────────────────────────────
        sl_exit = risk_manager.check_sl_exit(trade, current_price)
        if sl_exit:
            # Fill at stop_loss price, not current candle price.
            # Live brokers execute the stop order at stop price; paper must match.
            #
            # Sanity check 1: if stop_loss is > 20% away from current price AND
            # the stop is below entry (original/structural stop, not ratcheted),
            # treat it as a corrupt bad-feed stop and fill at current_price instead.
            #
            # IMPORTANT: when stop_loss > entry_price the stop has been ratcheted
            # to lock profit.  A crash can gap the price 25%+ below the ratcheted SL
            # in one 10-second monitor interval.  Overriding with current_price here
            # would turn a locked profit into a large loss.  Sanity check 2 (below)
            # already caps fake windfall gains, so check 1 is not needed for ratcheted
            # stops — honour the ratcheted SL price unconditionally.
            _raw_sl    = float(trade.get("stop_loss") or 0)
            _entry_ref = float(trade.get("entry_price") or 0)
            _direction_ref = trade.get("direction", "long")
            _sl_dist_pct = abs(_raw_sl - current_price) / current_price * 100 if current_price else 0
            _sl_is_ratcheted = (
                (_direction_ref == "long" and _raw_sl > _entry_ref > 0) or
                (_direction_ref == "short" and 0 < _raw_sl < _entry_ref)
            )

            if _sl_is_ratcheted:
                # Ratcheted stop: price moved through it — honour the locked-in stop price.
                # A real exchange stop order would have filled at or near this level.
                sl_fill_price = _raw_sl
                if _sl_dist_pct > 20.0:
                    logger.info(
                        f"[SL FILL] {symbol}: ratcheted stop ${_raw_sl:.6f} "
                        f"({_sl_dist_pct:.1f}% from live price ${current_price:.6f}) — "
                        f"filling at locked SL (profit protected)"
                    )
            else:
                # Original/structural stop below entry — apply corrupt-stop guard
                sl_fill_price = _raw_sl if _raw_sl and _sl_dist_pct <= 20.0 else current_price
                if _sl_dist_pct > 20.0:
                    logger.warning(
                        f"[SL FILL SANITY] {symbol}: stop_loss ${_raw_sl:.4f} is "
                        f"{_sl_dist_pct:.1f}% from current ${current_price:.4f} "
                        f"-- suspected corrupt stop, filling at current price"
                    )
            # Sanity check 2: for trailing_stop exits, the fill price should not be
            # more than 11% (stock) / 22% (crypto) above entry.  A fake feed spike
            # can leave a corrupted SL that triggers a windfall exit at an impossible
            # price.  If the fill looks too good relative to entry, fall back to
            # current_price (the real market price) instead of the inflated SL value.
            if sl_exit == "trailing_stop":
                _entry_ref = float(trade.get("entry_price") or 0)
                _direction = trade.get("direction", "long")
                _fill_max_pct = 11.0 if asset_class == "stock" else 22.0
                if _entry_ref > 0 and _direction == "long":
                    _fill_gain_pct = (sl_fill_price - _entry_ref) / _entry_ref * 100
                    if _fill_gain_pct > _fill_max_pct:
                        logger.warning(
                            f"[TRAIL FILL SANITY] {symbol}: trailing_stop fill ${sl_fill_price:.4f} "
                            f"is {_fill_gain_pct:.1f}% above entry ${_entry_ref:.4f} "
                            f"(>{_fill_max_pct}% cap) — suspected bad-feed exit, "
                            f"using current_price ${current_price:.4f} instead"
                        )
                        sl_fill_price = current_price
                elif _entry_ref > 0 and _direction == "short":
                    _fill_gain_pct = (_entry_ref - sl_fill_price) / _entry_ref * 100
                    if _fill_gain_pct > _fill_max_pct:
                        logger.warning(
                            f"[TRAIL FILL SANITY] {symbol}: trailing_stop fill ${sl_fill_price:.4f} "
                            f"is {_fill_gain_pct:.1f}% gain on short from entry ${_entry_ref:.4f} "
                            f"(>{_fill_max_pct}% cap) — suspected bad-feed exit, "
                            f"using current_price ${current_price:.4f} instead"
                        )
                        sl_fill_price = current_price
            logger.info(
                f"[STOP LOSS] {symbol} @ ${current_price:.6f} | "
                f"fill @ ${sl_fill_price:.6f} | "
                f"P&L {pnl_pct:+.2f}% | age {age_hrs:.1f}hr"
            )
            self._db.set_state(f"momentum_ext_{trade_id}", 0)
            self._attempt_close(trade, sl_fill_price, sl_exit)
            return

        # ── 4. ORB VWAP CROSS EXIT ──────────────────────────────────────
        if strategy == "orb_breakout":
            if self._check_vwap_cross_exit(trade, current_price):
                self._db.set_state(f"momentum_ext_{trade_id}", 0)
                self._attempt_close(trade, current_price, "vwap_cross")
                return

        # ── 4c. RSI DIP & SPIKE EXIT ─────────────────────────────────────
        # Strategy-specific exit: RSI neutral exit + 48-bar max-hold.
        # Takes priority over generic time stops — rsi_dip_spike_v4 is
        # TIME_STOP_EXEMPT in the backtester; this block gives live parity.
        if strategy == "rsi_dip_spike_v4":
            rsi_dip_exit = self._check_rsi_dip_spike_exit(trade, current_price, age_seconds)
            if rsi_dip_exit:
                self._db.set_state(f"momentum_ext_{trade_id}", 0)
                self._attempt_close(trade, current_price, rsi_dip_exit)
                return

        # ── 4c-2. GENERIC STRATEGY CUSTOM EXIT (live/backtest parity) ────────
        # Opus live-vs-paper audit 2026-05-29. Every strategy overriding
        # BaseStrategy.check_custom_exit() has its exit applied by the backtester
        # on every bar. adaptive_regime and rsi_dip_spike_v4 are handled above;
        # this dispatch covers ALL remaining strategies (btc_v6_chandelier,
        # ema_ribbon_breakout, kds/rcr_mean_reversion, mr_02/03/04, ecb_strategy,
        # swing_trader, bollinger_squeeze, pll_cycle, etc.) so live exits match
        # the thesis the params were tuned on. Pairs with diff 09.
        if strategy not in ("adaptive_regime", "rsi_dip_spike_v4", "orb_breakout"):
            custom_exit = self._check_generic_custom_exit(trade, age_seconds)
            if custom_exit:
                self._db.set_state(f"momentum_ext_{trade_id}", 0)
                self._attempt_close(trade, current_price, custom_exit)
                return

        # ── 4d. REVERSAL CANDLE EXIT (10-30 min, breakout + vwap_orb) ───────
        # 2 consecutive candles closing against the trade = reversal confirmed.
        # Fires before fast-fail — gets out even earlier on clean reversals.
        reversal_exit = self._check_reversal_candles(trade, age_seconds, pnl_pct)
        if reversal_exit:
            self._db.set_state(f"momentum_ext_{trade_id}", 0)
            self._attempt_close(trade, current_price, reversal_exit)
            return

        # ── 4e. BREAKOUT FAST-FAIL (10-20 min) ──────────────────────────────
        # Breakout trades must move immediately — if flat/negative at 10 min
        # the setup failed. Cut clean for tiny loss rather than riding to
        # the full 2-4.5% stop. Fires before early_loss (30 min) on purpose.
        fast_fail_exit = self._check_breakout_fast_fail(
            trade, current_price, pnl_pct, age_seconds
        )
        if fast_fail_exit:
            self._db.set_state(f"momentum_ext_{trade_id}", 0)
            self._attempt_close(trade, current_price, fast_fail_exit)
            return

        # ── 5. EARLY LOSS IDENTIFICATION (30 min) ────────────────────────
        # This guard is intentionally narrower than TIME_STOP_EXEMPT.
        if strategy not in EARLY_LOSS_LIFECYCLE_EXEMPT:
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

        # ── 8b. SCANNER PARTIAL PROFIT ───────────────────────────────────
        # One-shot harvest at fee-adjusted net-lock territory; remainder keeps
        # using the existing ratchet/trailing logic.
        self._maybe_take_scanner_partial(trade, current_price, pnl_pct)

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
                    import config as _cfg
                    tp_pct = _cfg.DEFAULT_TAKE_PROFIT_PCT / 100
                    new_tp = (
                        current_price * (1 + tp_pct)
                        if direction == "long"
                        else current_price * (1 - tp_pct)
                    )
                    new_tp = round(new_tp, 4)

                    if asset_class == "crypto" and not _cfg.KRAKEN_PAPER_MODE:
                        # ── LIVE MODE: close + reopen ─────────────────────
                        # Can't modify TP on a real exchange. Close the position
                        # at current price (booking the TP profit), then immediately
                        # re-enter with a fresh SL/TP if momentum still holds.
                        logger.info(
                            f"[LIVE TP RIDE] {symbol}: closing at TP ${current_price:.4f} "
                            f"and re-entering for momentum extension "
                            f"(ext {ext_count + 1}/{max_extensions})"
                        )
                        # Cancel existing stop order before closing
                        old_stop_id = trade.get("stop_order_id", "")
                        if old_stop_id:
                            self._get_executor().kraken.cancel_order(symbol, old_stop_id)
                        # Close the position (books the profit)
                        self._attempt_close(trade, current_price, "take_profit_ride")
                        # Re-enter immediately via scanner signal injection
                        # The scanner will pick it up on next cycle if momentum holds.
                        # We mark this so the cooldown knows it was a win-ride, not revenge.
                        try:
                            from core.risk_manager import risk_manager as _rm
                            _rm._last_closed[symbol] = {
                                "time": __import__("time").time() - 90,  # 90s ago = inside win cooldown
                                "won":  True,
                            }
                        except Exception:
                            pass
                        return
                    else:
                        # ── PAPER MODE: extend TP in DB (no real orders) ──
                        entry_price = float(trade.get("entry_price") or 0)
                        old_sl = float(trade.get("stop_loss") or 0)
                        lock_ratio = float(getattr(
                            _cfg, "MOMENTUM_RIDER_LOCK_PROFIT_RATIO", 0.50
                        ))
                        min_lock = float(getattr(
                            _cfg, "MOMENTUM_RIDER_MIN_LOCK_PCT", 0.25
                        ))
                        lock_pct = max(min_lock, pnl_pct * lock_ratio)
                        new_sl = old_sl

                        if entry_price > 0 and pnl_pct > 0:
                            if direction == "long":
                                candidate_sl = entry_price * (1 + lock_pct / 100)
                                candidate_sl = min(candidate_sl, current_price * 0.995)
                                new_sl = max(old_sl, candidate_sl) if old_sl else candidate_sl
                            else:
                                candidate_sl = entry_price * (1 - lock_pct / 100)
                                candidate_sl = max(candidate_sl, current_price * 1.005)
                                new_sl = min(old_sl, candidate_sl) if old_sl else candidate_sl
                            new_sl = round(new_sl, 6)

                        self._db.update_trade_levels(
                            trade_id, stop_loss=new_sl, take_profit=new_tp
                        )
                        trade["stop_loss"] = new_sl
                        trade["take_profit"] = new_tp
                        self._db.set_state(f"momentum_ext_{trade_id}", ext_count + 1)
                        self._db.increment_tp_hit_count(trade_id)
                        logger.info(
                            f"[PAPER TP EXTENDED] {symbol} {direction.upper()} | "
                            f"TP raised {trade['take_profit']:.4f} → {new_tp:.4f} | "
                            f"SL raised {old_sl:.4f} → {new_sl:.4f} | "
                            f"locked ~{lock_pct:.2f}% | "
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
                    # Fill at take_profit price, not current_price.
                    # In paper mode the monitor catches TP after price may have
                    # overshot — record at the actual TP level like a real limit order.
                    # In live mode this path is rarely hit (broker reconciliation at
                    # step 2b catches broker-filled TP orders first).
                    tp_fill_price = float(trade.get("take_profit") or current_price)
                    self._attempt_close(trade, tp_fill_price, "take_profit")
                    return

        # ── 10. PIVOT POINT BREAK ─────────────────────────────────────────
        # Only check after 30 min, and only for strategies explicitly opted in.
        # This prevents structural pivot exits from bleeding into strategies
        # that own their own exit logic.
        pivot_strategies = set(
            getattr(config, "PIVOT_EXIT_STRATEGIES", set()) or set()
        )
        if (
            getattr(config, "PIVOT_EXIT_ENABLED", True)
            and age_seconds >= 30 * 60
            and strategy in pivot_strategies
        ):
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
        # Note: by this point the performance time stop at 5hr has already
        # fired if profit was below 1.0%. This catches winning positions
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

        if PM_DEBUG:
            logger.info(f"[PM-DBG] ⑥ {symbol} — reached trailing stop section")
        # ── 11b. UNIVERSAL PROFIT RATCHET ────────────────────────────────────
        # Staged protection:
        #   1) first meaningful green move: reduce risk to gross breakeven;
        #   2) stronger move: lock fee-adjusted breakeven/net-positive;
        #   3) runners: trail from peak while never lowering the locked floor.
        #
        # Per-strategy thresholds — tighter for faster/crypto strategies:
        _RATCHET_THRESHOLDS = {
            # strategy_name:           (trigger_pct, trail_pct)   None = exempt
            "breakout_scanner":        (1.0, 0.75),
            "funding_scanner":         (1.0, 0.75),
            "gap_scanner":             (1.0, 0.75),
            "vwap_confirmed_orb":      (1.0, 0.75),
            "orb_breakout":            (1.0, 0.75),
            "bmr_357":                 (1.5, 0.50),  # 15m crypto — must clear fee/edge floor
            "fakeout_fade_sfr":        (0.8, 0.60),  # stock 5m
            "rsi_dip_spike_v4":        (1.0, 0.75),
            "grid_bot":                None,          # oscillates by design — ratchet kills the pattern
            "dca_accumulator":         None,          # adds on dips — ratchet would SL out mid-ladder
        }
        _ratchet_cfg = _RATCHET_THRESHOLDS.get(strategy, (1.0, 0.75))
        if _ratchet_cfg is not None:
            _RATCHET_TRIGGER_PCT, _RATCHET_TRAIL_PCT = _ratchet_cfg
            _entry       = float(trade.get("entry_price") or 0)
            _cur_sl      = float(trade.get("stop_loss") or 0)
            _pnl_pct_raw = pnl_pct
            _min_lock_pct = float(getattr(
                config,
                "MIN_NET_PROFIT_CRYPTO_PCT" if asset_class == "crypto" else "MIN_NET_PROFIT_STOCK_PCT",
                0.0,
            ))

            _is_scanner_ratchet = _is_breakout_trade(trade)
            if _is_scanner_ratchet:
                _risk_reduce_trigger = float(getattr(
                    config, "SCANNER_RATCHET_REDUCE_RISK_TRIGGER_PCT", 1.0
                ))
                _gross_lock_pct = float(getattr(
                    config, "SCANNER_RATCHET_GROSS_BREAKEVEN_PCT", 0.0
                ))
                _net_lock_trigger = max(
                    float(getattr(config, "SCANNER_RATCHET_NET_LOCK_TRIGGER_PCT", 1.5)),
                    _min_lock_pct,
                )
            else:
                _risk_reduce_trigger = max(_RATCHET_TRIGGER_PCT, _min_lock_pct)
                _gross_lock_pct = _min_lock_pct
                _net_lock_trigger = _risk_reduce_trigger

            _active_trigger = (
                _net_lock_trigger
                if _pnl_pct_raw >= _net_lock_trigger
                else _risk_reduce_trigger
            )
            _lock_floor_pct = (
                _min_lock_pct
                if _pnl_pct_raw >= _net_lock_trigger
                else _gross_lock_pct
            )

            if _entry > 0 and direction == "long":
                _peak = self._peak_prices.get(trade_id, _entry)
                if current_price > _peak:
                    _peak = current_price
                    self._peak_prices[trade_id] = _peak
                _ratchet_sl = _peak * (1 - _RATCHET_TRAIL_PCT / 100)
                if PM_DEBUG:
                    logger.info(
                        f"[PM-DBG] ⑦ {symbol} ({strategy}) ratchet: P&L={_pnl_pct_raw:+.2f}% "
                        f"peak=${_peak:.4f} ratchet_sl=${_ratchet_sl:.4f} "
                        f"trigger={_active_trigger}% floor={_lock_floor_pct}% "
                        f"{'ACTIVE' if _pnl_pct_raw >= _risk_reduce_trigger else 'waiting'}"
                    )
                if _pnl_pct_raw >= _risk_reduce_trigger:
                    _floor_sl = _entry * (1 + _lock_floor_pct / 100)
                    _target_sl = max(_floor_sl, _ratchet_sl)
                    _target_sl_rounded = round(_target_sl, 6)
                    _cur_sl_rounded = round(_cur_sl, 6)
                    if _target_sl_rounded > _cur_sl_rounded:
                        logger.info(
                            f"[PROFIT RATCHET] {symbol} ({strategy}): SL ${_cur_sl_rounded:.6f} → "
                            f"${_target_sl_rounded:.6f} | P&L {_pnl_pct_raw:.2f}% "
                            f"peak ${_peak:.4f} lock={_lock_floor_pct:.2f}%"
                        )
                        self._db.update_trade_levels(trade_id, stop_loss=_target_sl_rounded)
                        trade["stop_loss"] = _target_sl_rounded
                        self._ratchet_update_exchange_stop(
                            trade, trade_id, symbol, direction, _target_sl_rounded
                        )
            elif _entry > 0 and direction == "short":
                _peak = self._peak_prices.get(trade_id, _entry)
                if current_price < _peak:
                    _peak = current_price
                    self._peak_prices[trade_id] = _peak
                _ratchet_sl = _peak * (1 + _RATCHET_TRAIL_PCT / 100)
                if PM_DEBUG:
                    logger.info(
                        f"[PM-DBG] ⑦ {symbol} ({strategy}) ratchet: P&L={_pnl_pct_raw:+.2f}% "
                        f"peak=${_peak:.4f} ratchet_sl=${_ratchet_sl:.4f} "
                        f"trigger={_active_trigger}% floor={_lock_floor_pct}% "
                        f"{'ACTIVE' if _pnl_pct_raw >= _risk_reduce_trigger else 'waiting'}"
                    )
                if _pnl_pct_raw >= _risk_reduce_trigger:
                    _floor_sl = _entry * (1 - _lock_floor_pct / 100)
                    _target_sl = min(_floor_sl, _ratchet_sl)
                    _target_sl_rounded = round(_target_sl, 6)
                    _cur_sl_rounded = round(_cur_sl, 6)
                    if _target_sl_rounded < _cur_sl_rounded:
                        logger.info(
                            f"[PROFIT RATCHET] {symbol} ({strategy}): SL ${_cur_sl_rounded:.6f} → "
                            f"${_target_sl_rounded:.6f} | P&L {_pnl_pct_raw:.2f}% "
                            f"peak ${_peak:.4f} lock={_lock_floor_pct:.2f}%"
                        )
                        self._db.update_trade_levels(trade_id, stop_loss=_target_sl_rounded)
                        trade["stop_loss"] = _target_sl_rounded
                        self._ratchet_update_exchange_stop(
                            trade, trade_id, symbol, direction, _target_sl_rounded
                        )

        # ── 12. TRAILING STOP UPDATE + LOGGING ───────────────────────────
        # Breakout trades use the ratchet only — skip two-bar trail.
        # All others: two-bar structural trail runs in addition to the ratchet above.
        if _is_breakout_trade(trade):
            return
        # Non-breakout path — two-bar structural trailing stop
        _trade_meta   = _json.loads(trade.get("indicators_json") or "{}")
        _trail_pref   = _trade_meta.get("preferred_trail_mode", "two_bar").lower()
        _recent_high  = None
        _recent_low   = None
        if PM_DEBUG:
            logger.info(f"[PM-DBG] ⑦ {symbol} — two-bar trail path | trail_mode={_trail_pref}")
        if _trail_pref == "none":
            updates = None   # strategy manages its own exit — no trailing
        else:
            _trail_bars = self._get_bars(symbol, asset_class, limit=25, timeframe=entry_timeframe)

            # ── Price-spike guard ─────────────────────────────────────────────
            # A single bad feed tick can drive current_price far above real market
            # price.  If the trail runs on that tick it writes a corrupted SL above
            # the real price; the real price then falls "below" that fake SL and
            # fires a trailing_stop exit at the inflated fill → fake large wins.
            # Guard: if current_price is >3% above the highest candle high in the
            # last 3 closed bars, treat it as a bad tick and skip the trail update.
            _spike_blocked = False
            if _trail_bars is not None and len(_trail_bars) >= 2:
                _recent_high = float(_trail_bars["high"].iloc[-3:].max())
                _recent_low  = float(_trail_bars["low"].iloc[-3:].min())
                _spike_pct   = (current_price - _recent_high) / _recent_high * 100 if _recent_high > 0 else 0
                if _spike_pct > 3.0:
                    logger.warning(
                        f"[PRICE SPIKE GUARD] {symbol}: current_price ${current_price:.4f} "
                        f"is {_spike_pct:.1f}% above recent candle high ${_recent_high:.4f} "
                        f"— suspected bad feed tick, skipping trail update this cycle"
                    )
                    _spike_blocked = True

            updates = (
                None
                if _spike_blocked
                else risk_manager.calculate_trailing_stop(trade, current_price, bars=_trail_bars)
            )
        if PM_DEBUG:
            logger.info(f"[PM-DBG] ⑧ {symbol} — trail calc done | updates={updates}")
        if updates:
            old_sl = trade.get("stop_loss", 0)
            old_tp = trade.get("take_profit", 0)
            # Sanity-check the proposed new stop against entry before writing to DB.
            # A bad price feed can produce a bar low that's nowhere near entry, which
            # would corrupt the stop_loss and then get used as the exit fill price.
            # Stocks: cap SL at 10% above entry (real intraday moves >10% are rare;
            #         anything beyond that is almost certainly a feed spike).
            # Crypto: cap at 20% (wider for volatile assets, still tighter than old 60%).
            _entry      = float(trade.get("entry_price") or 0)
            _prop_sl    = updates.get("stop_loss")
            _max_sl_pct = 10.0 if asset_class == "stock" else 20.0
            _sl_rejected = False
            if (_prop_sl and _entry > 0
                    and abs(_prop_sl - _entry) / _entry * 100 > _max_sl_pct):
                logger.warning(
                    f"[TRAIL SANITY] {symbol}: proposed SL ${_prop_sl:.4f} is "
                    f"{abs(_prop_sl-_entry)/_entry*100:.1f}% from entry ${_entry:.4f} "
                    f"(>{_max_sl_pct}% cap) -- bad price feed suspected, skipping stop update"
                )
                _sl_rejected = True
            # ── Recent-range guard ────────────────────────────────────────
            # The entry-relative cap above can still be fooled by a bad tick that
            # happens to land under the % threshold (e.g. a stock 9% off entry is
            # "normal", but if it's also 9% above every recent candle high it's
            # still almost certainly a feed spike, not a real ratchet). Reject any
            # proposed SL that sits further than 5% outside the recent 3-bar range
            # on the side that matters for this direction, mirroring the same
            # tolerance the [PRICE SPIKE GUARD] above uses for current_price.
            _range_cap_pct = 5.0
            if not _sl_rejected and _prop_sl:
                if direction == "long" and _recent_high and _recent_high > 0:
                    _range_dev_pct = (_prop_sl - _recent_high) / _recent_high * 100
                    if _range_dev_pct > _range_cap_pct:
                        logger.warning(
                            f"[TRAIL SANITY] {symbol}: proposed SL ${_prop_sl:.4f} is "
                            f"{_range_dev_pct:.1f}% above recent candle high ${_recent_high:.4f} "
                            f"(>{_range_cap_pct}% cap) -- bad price feed suspected, skipping stop update"
                        )
                        _sl_rejected = True
                elif direction == "short" and _recent_low and _recent_low > 0:
                    _range_dev_pct = (_recent_low - _prop_sl) / _recent_low * 100
                    if _range_dev_pct > _range_cap_pct:
                        logger.warning(
                            f"[TRAIL SANITY] {symbol}: proposed SL ${_prop_sl:.4f} is "
                            f"{_range_dev_pct:.1f}% below recent candle low ${_recent_low:.4f} "
                            f"(>{_range_cap_pct}% cap) -- bad price feed suspected, skipping stop update"
                        )
                        _sl_rejected = True
            if _sl_rejected:
                updates.pop("stop_loss", None)
            if not updates:
                pass  # nothing safe to write
            else:
                self._db.update_trade_levels(
                    trade_id,
                    stop_loss   = updates.get("stop_loss"),
                    take_profit = updates.get("take_profit"),
                )
            if "stop_loss" in updates and updates["stop_loss"] != old_sl:
                new_sl = updates["stop_loss"]
                # Track how many times the stop has been ratcheted for dashboard indicator
                _raise_key   = f"sl_raise_count_{trade_id}"
                _raise_count = int(self._db.get_state(_raise_key, default=0) or 0) + 1
                self._db.set_state(_raise_key, _raise_count)
                logger.info(
                    f"[TRAILING STOP] {symbol} {direction.upper()} | "
                    f"SL ratcheted #{_raise_count} ${old_sl:.4f} → ${new_sl:.4f} | "
                    f"Locked in {pnl_pct:+.2f}% gain"
                )
                # ── Live + Paper: cancel old stop order, place new one ────
                # Paper mode: updates fake order ID for tracking parity
                # Live mode:  cancels real Kraken stop, places new one
                if asset_class == "crypto":
                    try:
                        kraken_ex      = self._get_executor().kraken
                        old_stop_id    = trade.get("stop_order_id", "")
                        stop_side      = "buy" if direction == "short" else "sell"
                        _leverage      = int(
                            _json.loads(trade.get("indicators_json") or "{}").get("kraken_leverage", 0)
                        )
                        new_stop_id    = kraken_ex.update_stop_order(
                            symbol, old_stop_id, qty, stop_side, new_sl,
                            leverage=_leverage,
                        )
                        if new_stop_id:
                            self._db.update_trade_order_ids(
                                trade_id, stop_order_id=new_stop_id
                            )
                            self._db.set_state(f"kraken_stop_unprotected_{trade_id}", 0)
                            logger.info(
                                f"[{'PAPER' if __import__('config').KRAKEN_PAPER_MODE else 'LIVE'}] "
                                f"Stop order updated for {symbol} "
                                f"${old_sl:.4f} → ${new_sl:.4f} | "
                                f"new_id={new_stop_id}"
                            )
                        elif new_stop_id == "" and old_stop_id:
                            self._mark_kraken_stop_unprotected(
                                trade, trade_id, symbol, old_stop_id, new_sl
                            )
                    except Exception as _trail_err:
                        logger.warning(
                            f"Stop order update failed for {symbol}: {_trail_err}"
                        )
            if "take_profit" in updates and updates["take_profit"] != old_tp:
                logger.info(
                    f"[DYNAMIC TP] {symbol} {direction.upper()} | "
                    f"TP adjusted ${old_tp:.4f} → ${updates['take_profit']:.4f}"
                )

    def check_positions(self):
        open_trades = self._db.get_open_trades()
        if PM_DEBUG:
            logger.info(f"[PM-DBG] check_positions called — {len(open_trades)} open trade(s)")
        if not open_trades:
            return

        market_open = _stock_market_open()

        externally_managed = [t for t in open_trades if _is_externally_managed_future(t)]
        managed_trades = [t for t in open_trades if not _is_externally_managed_future(t)]
        stock_trades = [t for t in managed_trades if t.get("asset_class") == "stock"]
        crypto_trades = [t for t in managed_trades if t.get("asset_class") != "stock"]

        if externally_managed:
            logger.debug(
                "Position monitor: skipping %d externally managed futures position(s)",
                len(externally_managed),
            )

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

            entry_price = float(trade["entry_price"] or 0)
            if asset_class == "stock" and not market_open:
                current_price = entry_price
            else:
                raw_price = self._get_scanner().get_current_price(symbol, asset_class)
                if raw_price and entry_price > 0:
                    _dev = abs(raw_price - entry_price) / entry_price
                    if _dev > 0.80:
                        logger.warning(
                            "[SUMMARY SANITY] %s: live $%.4f deviates %.1f%% from "
                            "entry $%.4f — bad feed, using entry for display",
                            symbol, raw_price, _dev * 100, entry_price,
                        )
                        current_price = entry_price
                    else:
                        current_price = raw_price
                else:
                    current_price = raw_price or entry_price

            qty       = trade["quantity"]
            direction = trade["direction"]

            if direction == "long":
                unrealized_pnl = (current_price - entry_price) * qty
                pnl_pct = (current_price / entry_price - 1) * 100 if entry_price else 0.0
            else:
                unrealized_pnl = (entry_price - current_price) * qty
                pnl_pct = (entry_price / current_price - 1) * 100 if current_price else 0.0

            age_seconds = _get_position_age_seconds(trade)
            is_stuck    = self._is_stuck(trade["trade_id"])
            close_attempts = self._get_close_attempts(trade["trade_id"])

            _raw_sl  = float(trade.get("stop_loss") or 0)
            _raw_tp  = float(trade.get("take_profit") or 0)
            _sl_dist = abs(current_price - _raw_sl) / current_price * 100 if current_price else 0
            _tp_dist = abs(_raw_tp - current_price) / current_price * 100 if current_price else 0
            enriched.append({
                **trade,
                "current_price":   round(current_price, 6),
                "unrealized_pnl":  round(unrealized_pnl, 4),
                "pnl_pct":         round(max(-200.0, min(200.0, pnl_pct)), 2),
                "market_value":    round(current_price * qty, 2),
                "distance_to_sl":  round(min(_sl_dist, 999.0), 2),
                "distance_to_tp":  round(min(_tp_dist, 999.0), 2),
                "age_hours":       round(age_seconds / 3600, 2),
                "is_overnight":    bool(trade.get("is_overnight", False)),
                "tp_hit_count":    int(trade.get("tp_hit_count", 0)),
                "is_stuck":        is_stuck,
                "close_attempts":  close_attempts,
            })

        return enriched


# Singleton
monitor = PositionMonitor()
