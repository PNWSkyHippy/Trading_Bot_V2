"""
bot_engine.py — Main entry point for the Autonomous Day Trading Bot
Trading Bot v2

Usage:
    python bot_engine.py            # Normal operation
    python bot_engine.py --verbose  # Verbose signal debugging (large log files!)
    python bot_engine.py -v         # Same as --verbose

IMPORTANT — TIMEZONE NOTE:
    This bot runs on a Windows machine set to Pacific Time (Spokane, WA).
    The schedule library has NO timezone awareness — it fires at whatever
    the system clock says. All schedule.at() times below are therefore in
    PACIFIC TIME. The actual ET times are noted in comments.

    Schedule times (PT = machine time, ET = actual market time):
      Stock close:   12:45 PT = 15:45 ET (15 min before market close)
      EOD report:    14:00 PT = 17:00 ET
      ML retrain:    15:00 PT = 18:00 ET
      Weekly log:    00:00 PT Sunday (midnight, covers prev Sun-Sat)
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone

import schedule

import config
from core.risk_manager import RiskManager
from core.trade_executor import TradeExecutor
from core.position_monitor import PositionMonitor
from core.broker_manager import BrokerManager
from data.database import Database
from scanners.market_scanner import MarketScanner
from strategies.strategy_engine import StrategyEngine
from intelligence.ml_scorer import MLScorer
from intelligence.condition_detector import ConditionDetector
from reporting.report_generator import ReportGenerator
from reporting.weekly_tradelog import run_weekly_export


def parse_args():
    parser = argparse.ArgumentParser(
        description="Autonomous Day Trading Bot v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable verbose signal logging for debugging"
    )
    return parser.parse_args()


def setup_logging(verbose: bool) -> logging.Logger:
    os.makedirs("logs", exist_ok=True)
    log_level = logging.DEBUG if verbose else logging.INFO

    file_handler = logging.FileHandler("logs/bot.log", encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    ))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return logging.getLogger("BotEngine")


def _is_market_open() -> bool:
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

    after_open  = hour > 10 or (hour == 10 and minute >= 0)
    before_close= hour < 15 or (hour == 15 and minute < 45)

    return after_open and before_close


def _et_now_str() -> str:
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("America/New_York")).strftime("%a %H:%M ET")


class BotEngine:

    def __init__(self):
        self.logger = logging.getLogger("BotEngine")
        self.logger.info("=" * 60)
        self.logger.info("  Autonomous Day Trading Bot v2 - Starting Up")
        self.logger.info("=" * 60)

        if config.VERBOSE_MODE:
            self.logger.info("*** VERBOSE MODE ACTIVE ***")

        self.db                = Database(config.DB_PATH)
        self.risk_manager      = RiskManager()
        self.broker_manager    = BrokerManager()
        self.trade_executor    = TradeExecutor()
        self.position_monitor  = PositionMonitor()
        self.strategy_engine   = StrategyEngine()
        self.ml_scorer         = MLScorer()
        self.condition_detector= ConditionDetector()
        self.market_scanner    = MarketScanner()
        self.report_generator  = ReportGenerator()

        self.logger.info("All components initialized successfully.")
        self._log_strategy_status()

        # Reconcile BEFORE registering jobs so ghosts are cleared
        # before any trading decisions are made today.
        # Ghost closures do NOT increment the consecutive loss counter.
        self._reconcile_positions()

        self._register_scheduled_jobs()

    def _log_strategy_status(self):
        strategies = self.strategy_engine.get_all_strategies()
        enabled    = [s for s in strategies if s.enabled]
        disabled   = [s for s in strategies if not s.enabled]
        self.logger.info(
            f"Strategy engine loaded: {len(enabled)} enabled, "
            f"{len(disabled)} disabled"
        )
        for s in enabled:
            self.logger.info(f"  [ENABLED]  {s.name}")
        for s in disabled:
            self.logger.info(f"  [DISABLED] {s.name}")

    # ------------------------------------------------------------------
    #  POSITION RECONCILIATION
    #
    #  IMPORTANT: Ghost closures bypass risk_manager.record_trade_result()
    #  entirely. They write directly to the DB so the consecutive loss
    #  counter is NOT incremented. Ghosts are not real trades and should
    #  never trigger a trading halt.
    # ------------------------------------------------------------------

    def _reconcile_positions(self):
        """
        Compare DB open trades against actual Alpaca positions at startup.
        Any stock trade in DB that Alpaca no longer holds gets marked
        closed with exit_reason='reconciled_ghost' and pnl=0.

        Ghost closures do NOT call risk_manager.record_trade_result()
        so they never increment the consecutive loss counter or trigger
        a halt. This prevents the bot from halting at startup because
        yesterday's ghost positions looked like 10 consecutive losses.

        Crypto positions are skipped — paper sim trades are intentionally
        not in Alpaca.
        """
        try:
            import alpaca_trade_api as tradeapi
            api = tradeapi.REST(
                config.ALPACA_API_KEY,
                config.ALPACA_SECRET_KEY,
                config.ALPACA_BASE_URL
            )

            try:
                alpaca_positions = api.list_positions()
                alpaca_symbols   = {p.symbol for p in alpaca_positions}
            except Exception as e:
                self.logger.warning(
                    f"Reconciliation: could not fetch Alpaca positions: {e}"
                )
                return

            open_trades  = self.db.get_open_trades()
            stock_trades = [
                t for t in open_trades
                if t.get("asset_class") == "stock"
            ]

            if not stock_trades:
                self.logger.debug(
                    "Reconciliation: no open stock trades to check."
                )
                return

            ghost_count = 0
            for trade in stock_trades:
                symbol = trade["symbol"]
                if symbol not in alpaca_symbols:
                    self.logger.warning(
                        f"Reconciliation: {symbol} in DB but not in Alpaca — "
                        f"marking as ghost (trade_id={trade['trade_id']}). "
                        f"Consecutive loss counter NOT incremented."
                    )
                    try:
                        # Write directly to DB — bypass trade_executor and
                        # risk_manager so consecutive_losses stays untouched
                        self.db.close_trade(
                            trade_id    = trade["trade_id"],
                            exit_price  = trade["entry_price"],
                            exit_reason = "reconciled_ghost",
                            pnl         = 0.0,
                            pnl_pct     = 0.0
                        )
                        ghost_count += 1
                    except Exception as e:
                        self.logger.error(
                            f"Reconciliation: failed to close ghost "
                            f"{symbol}: {e}"
                        )

            if ghost_count > 0:
                self.logger.info(
                    f"Reconciliation complete: {ghost_count} ghost(s) cleared. "
                    f"Alpaca has {len(alpaca_symbols)} real position(s): "
                    f"{', '.join(alpaca_symbols) if alpaca_symbols else 'none'}. "
                    f"Consecutive loss counter unchanged."
                )
            else:
                self.logger.info(
                    f"Reconciliation complete: all {len(stock_trades)} DB "
                    f"stock position(s) confirmed in Alpaca. No ghosts."
                )

        except Exception as e:
            self.logger.error(
                f"Reconciliation error: {e}", exc_info=True
            )

    def _register_scheduled_jobs(self):
        self.logger.info("Registering scheduled jobs...")

        schedule.every(config.CRYPTO_SCAN_INTERVAL_SEC).seconds.do(
            self._run_crypto_scan
        )
        schedule.every(config.STOCK_SCAN_INTERVAL_SEC).seconds.do(
            self._run_stock_scan
        )
        schedule.every(30).seconds.do(self.position_monitor.check_positions)
        schedule.every(config.CAPITAL_SYNC_MIN).minutes.do(self._sync_capital)

        for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
            getattr(schedule.every(), day).at("12:45").do(self._close_stocks_eod)

        for day in ["monday", "tuesday", "wednesday", "thursday", "friday",
                    "saturday", "sunday"]:
            getattr(schedule.every(), day).at("14:00").do(self._end_of_day)

        schedule.every().day.at("15:00").do(self._retrain_ml)
        schedule.every().sunday.at("00:00").do(run_weekly_export)

        self.logger.info("All scheduled jobs registered.")
        self.logger.info("  - Crypto scan:      every 5 min (24/7)")
        self.logger.info("  - Stock scan:       every 60s (Mon-Fri 10:00-15:44 ET)")
        self.logger.info("  - Stock EOD close:  15:45 ET (12:45 PT) weekdays")
        self.logger.info("  - Position monitor: every 30s (24/7)")
        self.logger.info("  - Capital sync:     every 15 min")
        self.logger.info("  - EOD report:       17:00 ET (14:00 PT) daily")
        self.logger.info("  - ML retrain:       18:00 ET (15:00 PT) daily")
        self.logger.info("  - Weekly trade log: Sunday 00:00 PT")

    def _run_stock_scan(self):
        try:
            if not _is_market_open():
                self.logger.debug(
                    f"Stock scan skipped — market closed ({_et_now_str()})"
                )
                return
            self.logger.debug(f"Running stock scan ({_et_now_str()})...")
            self.market_scanner.scan_stocks()
        except Exception as e:
            self.logger.error(f"Stock scan error: {e}", exc_info=True)

    def _run_crypto_scan(self):
        try:
            self.logger.debug("Running crypto scan...")
            self.market_scanner.scan_crypto()
        except Exception as e:
            self.logger.error(f"Crypto scan error: {e}", exc_info=True)

    def _close_stocks_eod(self):
        try:
            self.logger.info(
                f"15:45 ET stock EOD close starting ({_et_now_str()})..."
            )
            from data.database import db as _db
            open_trades  = _db.get_open_trades()
            stock_trades = [
                t for t in open_trades
                if t.get("asset_class") == "stock"
            ]
            if not stock_trades:
                self.logger.info("Stock EOD close: no open stock positions.")
                return

            closed_count  = 0
            skipped_count = 0
            for trade in stock_trades:
                if trade.get("is_overnight"):
                    self.logger.info(
                        f"Stock EOD close: SKIPPING {trade['symbol']} "
                        f"— flagged is_overnight"
                    )
                    skipped_count += 1
                    continue
                try:
                    current_price = self.market_scanner.get_current_price(
                        trade["symbol"], "stock"
                    )
                    if not current_price:
                        current_price = trade["entry_price"]
                except Exception:
                    current_price = trade["entry_price"]

                success = self.trade_executor.close_trade(
                    trade, current_price, "eod_close"
                )
                if success:
                    closed_count += 1
                    self.logger.info(
                        f"EOD closed: {trade['symbol']} @ "
                        f"${current_price:.4f}"
                    )
                else:
                    self.logger.error(
                        f"EOD close FAILED for {trade['symbol']} — "
                        f"manual close needed"
                    )

            self.logger.info(
                f"Stock EOD close complete: {closed_count} closed, "
                f"{skipped_count} overnight holds skipped"
            )
        except Exception as e:
            self.logger.error(f"Stock EOD close error: {e}", exc_info=True)

    def _end_of_day(self):
        try:
            self.logger.info(
                "Running end-of-day routine (report + session reset)..."
            )
            self.report_generator.generate_and_send_daily_report()
            self.db.reset_session_state()
            self.logger.info("End-of-day routine complete.")
        except Exception as e:
            self.logger.error(f"End-of-day routine error: {e}", exc_info=True)

    def _sync_capital(self):
        try:
            try:
                from core.settlement_tracker import settlement_tracker
                settlement_tracker.process_settlements()
            except Exception:
                pass
            self.logger.debug("Syncing capital from all brokers...")
            self.broker_manager.sync_all_balances()
            breakdown = self.broker_manager.get_capital_breakdown()
            total     = breakdown.get("total_balance", 0.0)
            if total > 0:
                self.db.record_capital_snapshot(total)
                self.logger.info(
                    f"Capital sync complete. Total: ${total:,.2f}"
                )
                for b in breakdown.get("brokers", []):
                    self.logger.info(
                        f"  {b['display_name']}: ${b['balance']:,.2f}"
                    )
            else:
                self.logger.info(
                    "Capital sync: no live balances yet "
                    "(normal in paper mode)"
                )
            self._reconcile_positions()
        except Exception as e:
            self.logger.error(f"Capital sync error: {e}", exc_info=True)

    def _retrain_ml(self):
        try:
            self.logger.info("Retraining ML model...")
            result = self.ml_scorer.retrain()
            if result:
                self.logger.info("ML model retrained successfully.")
            else:
                self.logger.info(
                    f"ML retrain skipped "
                    f"(need {config.ML_MIN_TRADES}+ trades)."
                )
        except Exception as e:
            self.logger.error(f"ML retrain error: {e}", exc_info=True)

    def run(self):
        self.logger.info("Bot is running. Press Ctrl+C to stop.")
        self.logger.info(
            f"Monitoring {len(config.CRYPTO_WATCHLIST)} crypto pairs 24/7"
        )
        self.logger.info(
            f"Monitoring {len(config.STOCK_WATCHLIST)} stocks "
            f"(market hours only: Mon-Fri 10:00-15:44 ET)"
        )
        self._sync_capital()
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested. Stopping bot.")
            self._shutdown()

    def _shutdown(self):
        self.logger.info("Shutting down gracefully...")
        self.logger.info("Bot stopped.")


if __name__ == "__main__":
    args   = parse_args()
    config.VERBOSE_MODE = args.verbose
    logger = setup_logging(args.verbose)

    if args.verbose:
        print("=" * 60)
        print("  VERBOSE MODE ENABLED")
        print("  Log file: logs/bot.log")
        print("=" * 60)

    bot = BotEngine()
    bot.run()
