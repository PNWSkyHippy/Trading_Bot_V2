"""
=============================================================
  RISK MANAGER
  The single most important module. Every trade must pass
  through here before execution. Enforces all rules:
  - 2% max position sizing
  - 1.5% stop-loss on all trades
  - 3% take-profit (initial)
  - 15% max daily loss ceiling
  - 10 consecutive loss halt
  - Max 30 open positions
=============================================================
"""

import logging
from datetime import date, datetime
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

import config
try:
    from reporting.alerts import alert_manager
except Exception:
    alert_manager = None
from data.database import db

logger = logging.getLogger(__name__)


@dataclass
class TradeApproval:
    approved:       bool
    reason:         str
    quantity:       float = 0.0
    position_value: float = 0.0
    stop_loss:      float = 0.0
    take_profit:    float = 0.0
    risk_amount:    float = 0.0


@dataclass
class DailyStatus:
    trading_active:       bool
    halt_reason:          str
    pnl_today:            float
    pnl_pct_today:        float
    consecutive_losses:   int
    trades_today:         int
    capital:              float
    daily_loss_remaining: float


class RiskManager:
    """
    Guardian of the trading system. Nothing gets traded without approval here.
    All rules are enforced strictly and logged.
    """

    def __init__(self):
        self._session_date = None
        self._session      = None
        self._refresh_session()

    def _refresh_session(self):
        today = date.today().isoformat()
        if self._session_date != today:
            self._session_date = today
            self._session = db.get_session(today)

    def _get_capital(self) -> float:
        """
        Calculate true capital by adding all-time realized P&L to starting capital.
        This ensures capital tracks correctly even though Alpaca paper balance never changes.
        """
        try:
            closed = db.get_all_closed_trades(limit=99999)
            total_pnl = sum(t.get("pnl", 0.0) or 0.0 for t in closed)
            total = config.STARTING_CAPITAL + total_pnl

            cap = db.get_latest_capital()
            last = cap["total_capital"] if cap else 0
            if abs(total - last) > 0.50:
                db.record_capital_snapshot(total)

            allocation = getattr(config, "BOT_CAPITAL_ALLOCATION", None)
            if allocation and allocation > 0:
                return min(total, allocation)
            return max(total, 1.0)
        except Exception:
            cap = db.get_latest_capital()
            total = cap["total_capital"] if cap else config.STARTING_CAPITAL
            allocation = getattr(config, "BOT_CAPITAL_ALLOCATION", None)
            if allocation and allocation > 0:
                return min(total, allocation)
            return total

    # ----------------------------------------------------------
    #  DAILY STATUS CHECK
    # ----------------------------------------------------------

    def get_daily_status(self) -> DailyStatus:
        self._refresh_session()
        capital   = self._get_capital()
        pnl_today = self._session.get("pnl_today", 0.0)
        pnl_pct   = (pnl_today / capital * 100) if capital else 0
        max_daily_loss       = capital * (config.MAX_DAILY_LOSS_PCT / 100)
        daily_loss_remaining = max_daily_loss + pnl_today

        return DailyStatus(
            trading_active       = not bool(self._session.get("trading_halted", 0)),
            halt_reason          = self._session.get("halt_reason", ""),
            pnl_today            = pnl_today,
            pnl_pct_today        = pnl_pct,
            consecutive_losses   = self._session.get("consecutive_losses", 0),
            trades_today         = self._session.get("trades_today", 0),
            capital              = capital,
            daily_loss_remaining = max(0, daily_loss_remaining)
        )

    def is_trading_allowed(self) -> Tuple[bool, str]:
        self._refresh_session()

        if self._session.get("trading_halted"):
            reason = self._session.get("halt_reason", "Trading halted")
            return False, reason

        capital        = self._get_capital()
        pnl_today      = self._session.get("pnl_today", 0.0)
        max_daily_loss = capital * (config.MAX_DAILY_LOSS_PCT / 100)

        if pnl_today <= -max_daily_loss:
            self._halt_trading(
                f"Daily loss limit reached: ${abs(pnl_today):.2f} "
                f"({abs(pnl_today / capital * 100):.1f}%)"
            )
            return False, f"{config.MAX_DAILY_LOSS_PCT:.0f}% daily loss ceiling reached. Trading halted until tomorrow."

        if self._session.get("consecutive_losses", 0) >= config.MAX_CONSECUTIVE_LOSSES:
            self._halt_trading(f"{config.MAX_CONSECUTIVE_LOSSES} consecutive losses triggered halt")
            return False, f"{config.MAX_CONSECUTIVE_LOSSES} consecutive losing trades. Trading halted until tomorrow."

        open_trades = db.get_open_trades()
        if len(open_trades) >= config.MAX_OPEN_POSITIONS:
            return False, f"Maximum {config.MAX_OPEN_POSITIONS} open positions reached."

        return True, "Trading allowed"

    # ----------------------------------------------------------
    #  POSITION SIZING & TRADE APPROVAL
    # ----------------------------------------------------------

    def approve_trade(self, symbol: str, entry_price: float,
                      signal_score: float, direction: str = "long",
                      custom_stop_loss_pct: float = None,
                      custom_take_profit_pct: float = None,
                      custom_position_pct: float = None) -> TradeApproval:
        allowed, reason = self.is_trading_allowed()
        if not allowed:
            return TradeApproval(approved=False, reason=reason)

        min_confidence = config.SIGNAL_TUNING.get(
            "min_signal_confidence", config.MIN_SIGNAL_CONFIDENCE
        )
        if signal_score < min_confidence:
            return TradeApproval(
                approved=False,
                reason=(f"Signal confidence {signal_score:.2f} below "
                        f"minimum {min_confidence:.2f}")
            )

        capital = self._get_capital()
        if capital <= 0:
            return TradeApproval(approved=False, reason="No capital available")

        position_pct   = (custom_position_pct or config.MAX_POSITION_PCT) / 100
        position_value = capital * position_pct
        quantity       = position_value / entry_price

        stop_loss_pct   = (custom_stop_loss_pct   or config.DEFAULT_STOP_LOSS_PCT)   / 100
        take_profit_pct = (custom_take_profit_pct or config.DEFAULT_TAKE_PROFIT_PCT) / 100

        risk_amount = position_value * stop_loss_pct

        pnl_today              = self._session.get("pnl_today", 0.0)
        max_daily_loss         = capital * (config.MAX_DAILY_LOSS_PCT / 100)
        remaining_loss_budget  = max_daily_loss + pnl_today
        if risk_amount > remaining_loss_budget and remaining_loss_budget > 0:
            position_value = remaining_loss_budget / stop_loss_pct
            quantity       = position_value / entry_price
            risk_amount    = remaining_loss_budget
            logger.warning(f"Position scaled down for {symbol}: daily budget constraint")

        if quantity <= 0 or position_value < 1.0:
            return TradeApproval(
                approved=False,
                reason="Position too small after risk constraints"
            )

        if direction == "long":
            stop_loss   = entry_price * (1 - stop_loss_pct)
            take_profit = entry_price * (1 + take_profit_pct)
        else:
            stop_loss   = entry_price * (1 + stop_loss_pct)
            take_profit = entry_price * (1 - take_profit_pct)

        logger.info(
            f"APPROVED: {symbol} {direction.upper()} | "
            f"${position_value:.2f} ({position_pct*100:.0f}% capital) | "
            f"Entry: ${entry_price:.4f} | SL: ${stop_loss:.4f} | "
            f"TP: ${take_profit:.4f} | Risk: ${risk_amount:.2f} | "
            f"Score: {signal_score:.2f}"
        )

        return TradeApproval(
            approved        = True,
            reason          = "Approved",
            quantity        = round(quantity, 6),
            position_value  = round(position_value, 2),
            stop_loss       = round(stop_loss, 4),
            take_profit     = round(take_profit, 4),
            risk_amount     = round(risk_amount, 2)
        )

    # ----------------------------------------------------------
    #  TRAILING STOP MANAGEMENT
    # ----------------------------------------------------------

    def calculate_trailing_stop(self, trade: Dict,
                                 current_price: float) -> Optional[Dict]:
        direction  = trade["direction"]
        current_sl = trade["stop_loss"]
        trailing_gap = config.TRAILING_STOP_PCT / 100
        updates = {}

        if direction == "long":
            new_sl = current_price * (1 - trailing_gap)
            if new_sl > current_sl:
                updates["stop_loss"] = round(new_sl, 4)
                logger.info(
                    f"Trailing stop raised for {trade['symbol']}: "
                    f"${current_sl:.4f} -> ${new_sl:.4f}"
                )
        elif direction == "short":
            new_sl = current_price * (1 + trailing_gap)
            if new_sl < current_sl:
                updates["stop_loss"] = round(new_sl, 4)

        return updates if updates else None

    def check_sl_exit(self, trade: Dict, current_price: float) -> Optional[str]:
        direction = trade["direction"]
        sl = trade["stop_loss"]
        if direction == "long"  and current_price <= sl: return "stop_loss"
        if direction == "short" and current_price >= sl: return "stop_loss"
        return None

    def check_exit_conditions(self, trade: Dict,
                               current_price: float) -> Optional[str]:
        direction = trade["direction"]
        sl = trade["stop_loss"]
        tp = trade["take_profit"]

        if direction == "long":
            if current_price <= sl: return "stop_loss"
            if current_price >= tp: return "take_profit"
        elif direction == "short":
            if current_price >= sl: return "stop_loss"
            if current_price <= tp: return "take_profit"

        return None

    # ----------------------------------------------------------
    #  POST-TRADE RECORDING
    # ----------------------------------------------------------

    def record_trade_result(self, pnl: float, trade_won: bool):
        """Update session state after a trade closes."""
        self._refresh_session()
        session_date = date.today().isoformat()

        current_losses = self._session.get("consecutive_losses", 0)
        new_losses     = 0 if trade_won else current_losses + 1
        pnl_today      = self._session.get("pnl_today", 0.0) + pnl
        trades_today   = self._session.get("trades_today", 0) + 1

        db.update_session(session_date,
            consecutive_losses = new_losses,
            pnl_today          = pnl_today,
            trades_today       = trades_today
        )
        self._session["consecutive_losses"] = new_losses
        self._session["pnl_today"]          = pnl_today
        self._session["trades_today"]       = trades_today

        if not trade_won:
            logger.warning(
                f"Losing trade recorded. Consecutive losses: {new_losses}"
            )
            if new_losses >= config.MAX_CONSECUTIVE_LOSSES:
                self._halt_trading(
                    f"{config.MAX_CONSECUTIVE_LOSSES} consecutive losing trades"
                )
        else:
            logger.info(f"Winning trade: +${pnl:.2f}. Consecutive loss counter reset.")

    def _halt_trading(self, reason: str):
        session_date = date.today().isoformat()
        db.update_session(session_date, trading_halted=1, halt_reason=reason)
        self._session["trading_halted"] = 1
        self._session["halt_reason"]    = reason
        logger.critical(f"[HALT] TRADING HALTED: {reason}")
        try:
            if alert_manager:
                alert_manager.trading_halted(reason)
        except Exception:
            pass

    def manual_halt(self, reason: str = "Manual halt by user"):
        self._halt_trading(reason)

    def manual_resume(self):
        session_date = date.today().isoformat()
        db.update_session(session_date,
            trading_halted     = 0,
            halt_reason        = None,
            consecutive_losses = 0
        )
        self._session["trading_halted"] = 0
        self._session["halt_reason"]    = None
        logger.info("Trading resumed by manual command.")

    # ----------------------------------------------------------
    #  WITHDRAWAL PROCESSING
    # ----------------------------------------------------------

    def process_withdrawal(self, amount: float,
                            reason: str = "Living expenses") -> Dict:
        capital = self._get_capital()
        if amount > capital * 0.5:
            return {
                "approved": False,
                "message": (
                    f"Withdrawal of ${amount:.2f} exceeds 50% of capital "
                    f"(${capital:.2f}). Please confirm this is intentional."
                )
            }
        if amount <= 0:
            return {"approved": False, "message": "Invalid withdrawal amount."}

        new_capital = capital - amount
        db.record_withdrawal(amount, reason, capital, new_capital)
        db.log_capital(
            total     = new_capital,
            available = new_capital,
            invested  = 0,
            note      = f"Withdrawal: ${amount:.2f} - {reason}"
        )

        logger.info(
            f"Withdrawal processed: ${amount:.2f}. New capital: ${new_capital:.2f}"
        )
        return {
            "approved":       True,
            "withdrawn":      amount,
            "capital_before": capital,
            "capital_after":  new_capital,
            "message": (
                f"Withdrawal of ${amount:.2f} processed. "
                f"Capital adjusted to ${new_capital:.2f}"
            )
        }

    def reset_session(self):
        """Reset the daily session state (called at end of day)."""
        session_date = date.today().isoformat()
        db.update_session(session_date,
            trading_halted     = 0,
            halt_reason        = None,
            consecutive_losses = 0,
            pnl_today          = 0.0,
            trades_today       = 0
        )
        self._session = db.get_session(session_date)
        logger.info("Session state reset for new trading day.")


# Singleton
risk_manager = RiskManager()
