"""
=============================================================
  CLAUDE AI CHAT INTERFACE
  Lets you talk to your trading bot in plain English.

  Model: claude-haiku-4-5-20251001 (cheapest Claude, fast)
  Cost controls:
    - max_tokens capped at 512
    - context trimmed to essentials only
    - conversation history capped at 10 turns

  Pre-parse layer:
    Simple commands (enable/disable strategy, morning scan) are
    detected directly from the user message BEFORE sending to
    Haiku. This bypasses Haiku's tendency to second-guess simple
    commands and ensures they always execute reliably.

  Activity logging:
    Every user message and every action executed is logged
    to the chat_actions table in the database.
    Search logs for [CLAUDE] to see all activity.
    EOD report includes a Claude Activity Summary section.
=============================================================
"""

import json
import logging
import re
import requests
from datetime import date, datetime
from typing import List, Dict, Optional

import config
from data.database import db
from core.risk_manager import risk_manager
from core.position_monitor import monitor

logger = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# All valid strategy names — used by pre-parser
STRATEGY_NAMES = [
    "rsi_momentum", "bollinger_breakout", "ema_crossover", "mean_reversion",
    "scalp_master", "swing_trader", "grid_bot", "dca_accumulator",
    "vwap_momentum", "hammer_reversal", "orb_breakout",
]

SYSTEM_PROMPT = """You are the AI controller for an autonomous day trading bot.
Help the owner monitor and control it through natural conversation.
Be concise. Use numbers. Confirm before withdrawals.

CRITICAL RULES:
- NEVER halt trading unless the user says EXACTLY "halt trading", "pause trading", or "stop all trades".
- Vague statements like "resources used up", "I'm tired", "things are slow" are NOT halt commands. Ask instead.
- Only execute actions when you are 100% certain. When in doubt, ASK.
- halt_trading and withdraw require explicit confirmation.

STRATEGY COMMANDS:
Valid names: rsi_momentum, bollinger_breakout, ema_crossover, mean_reversion,
salp_master, swing_trader, grid_bot, dca_accumulator, vwap_momentum,
hammer_reversal, orb_breakout

When user says "enable X" or "disable X" — execute IMMEDIATELY, no questions.
Do NOT say the strategy doesn't exist. Do NOT list strategies first. Just do it.

MORNING SCAN command:
When user says "morning scan" or "what should I trade" or "top setups":
- Execute {"action": "morning_scan"} immediately
- This surfaces top ORB and momentum candidates for manual trading

Available actions (include JSON in response to execute):
{"action": "halt_trading", "reason": "user request"}
{"action": "resume_trading"}
{"action": "withdraw", "amount": 500.00, "reason": "living expenses"}
{"action": "set_risk", "param": "MAX_POSITION_PCT", "value": 1.5}
{"action": "export_taxes", "year": 2025}
{"action": "list_strategies"}
{"action": "enable_strategy", "name": "orb_breakout"}
{"action": "disable_strategy", "name": "grid_bot"}
{"action": "strategy_stats"}
{"action": "morning_scan"}
{"action": "list_brokers"}
{"action": "inject_funds", "broker": "kraken", "amount": 500.00, "reason": "deposit"}
{"action": "withdraw_funds", "broker": "alpaca", "amount": 200.00, "reason": "rent"}
{"action": "capital_breakdown"}
{"action": "enable_broker", "name": "kraken"}
{"action": "disable_broker", "name": "kraken"}

Fund injections/withdrawals are INFORMATIONAL ONLY."""


class ChatInterface:

    def __init__(self):
        self.conversation_history: List[Dict] = []
        self.max_history = 10
        self._last_user_message = ""
        self._last_strategy_mentioned: Optional[str] = None

    # ------------------------------------------------------------------
    #  PRE-PARSE LAYER
    #  Detects simple commands directly from user message.
    #  Bypasses Haiku entirely for reliability.
    # ------------------------------------------------------------------

    def _pre_parse(self, user_message: str) -> Optional[List[str]]:
        """
        Detect simple commands directly from user input before sending
        to Haiku. Returns list of result strings if handled, None if
        Haiku should handle it.

        Handles:
        - enable/disable strategy (by name or alias)
        - morning scan
        """
        msg = user_message.strip().lower()

        # --- enable strategy ---
        for name in STRATEGY_NAMES:
            if re.search(rf'\benable\b.*\b{re.escape(name)}\b', msg) or \
               re.search(rf'\b{re.escape(name)}\b.*\benable\b', msg) or \
               re.search(rf'turn on.*\b{re.escape(name)}\b', msg):
                from strategies.strategy_engine import strategy_engine
                result = strategy_engine.enable_strategy(name)
                logger.info(f"[CLAUDE] PRE-PARSE enable_strategy | name={name}")
                self._last_strategy_mentioned = name
                return [result]

        # --- disable strategy ---
        for name in STRATEGY_NAMES:
            if re.search(rf'\bdisable\b.*\b{re.escape(name)}\b', msg) or \
               re.search(rf'\b{re.escape(name)}\b.*\bdisable\b', msg) or \
               re.search(rf'turn off.*\b{re.escape(name)}\b', msg):
                from strategies.strategy_engine import strategy_engine
                result = strategy_engine.disable_strategy(name)
                logger.info(f"[CLAUDE] PRE-PARSE disable_strategy | name={name}")
                self._last_strategy_mentioned = name
                return [result]

        # --- morning scan ---
        if any(phrase in msg for phrase in [
            "morning scan", "what should i trade", "top setups",
            "best setups", "what to trade", "scan for me"
        ]):
            result = self._run_morning_scan()
            logger.info("[CLAUDE] PRE-PARSE morning_scan")
            return [result]

        return None  # Let Haiku handle it

    def _run_morning_scan(self) -> str:
        """
        Morning scan: surfaces top trading candidates.
        Queries the scanner for current signals across ORB whitelist
        and momentum stocks. Called at ~10:00 AM ET.
        """
        try:
            from scanners.market_scanner import scanner
            from strategies.strategy_engine import strategy_engine
            import pandas as pd

            try:
                from zoneinfo import ZoneInfo
            except ImportError:
                from backports.zoneinfo import ZoneInfo

            now_et = datetime.now(ZoneInfo("America/New_York"))
            time_str = now_et.strftime("%H:%M ET")

            # ORB whitelist stocks to scan
            orb_candidates = [
                "META", "TSLA", "MSFT", "AMD", "MRVL",
                "ALAB", "PLTR", "CRWV", "IREN", "CLS", "AMZN"
            ]

            results = []
            for symbol in orb_candidates:
                try:
                    price = scanner.get_current_price(symbol, "stock")
                    if not price:
                        continue

                    # Get recent bars for basic momentum check
                    bars = scanner.stock_scanner.get_bars(symbol, timeframe="5Min", limit=20)
                    if bars is None or len(bars) < 5:
                        continue

                    closes = bars["close"]
                    volumes = bars["volume"]

                    # Simple momentum: is price above open? Volume above average?
                    open_price  = float(closes.iloc[0])
                    curr_price  = float(closes.iloc[-1])
                    avg_vol     = float(volumes.iloc[:-1].mean())
                    curr_vol    = float(volumes.iloc[-1])
                    pct_move    = (curr_price - open_price) / open_price * 100
                    vol_ratio   = curr_vol / avg_vol if avg_vol > 0 else 0

                    if abs(pct_move) >= 0.3 and vol_ratio >= 1.2:
                        direction = "▲ LONG" if pct_move > 0 else "▼ SHORT"
                        results.append((
                            abs(pct_move), vol_ratio,
                            f"{symbol}: {direction} | "
                            f"Move: {pct_move:+.2f}% | "
                            f"Vol: {vol_ratio:.1f}x | "
                            f"Price: ${curr_price:.2f}"
                        ))
                except Exception:
                    continue

            if not results:
                return (
                    f"🔍 Morning Scan ({time_str}) — No strong setups found yet.\n"
                    f"Check back after 10:00 AM ET when ORB window opens."
                )

            # Sort by move size × volume
            results.sort(key=lambda x: x[0] * x[1], reverse=True)
            top = results[:5]

            lines = [f"🔍 Morning Scan ({time_str}) — Top {len(top)} Candidates:\n"]
            for i, (_, _, line) in enumerate(top, 1):
                lines.append(f"{i}. {line}")

            lines.append("\n💡 Wait for 9:45 ET ORB window before entering.")
            lines.append("Enter in direction of move if volume confirms.")
            lines.append("Exit when price crosses back below VWAP or EOD.")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Morning scan error: {e}")
            return f"Morning scan error: {e}. Bot is still running normally."

    def _build_context(self) -> str:
        session      = risk_manager.get_daily_status()
        capital_rec  = db.get_latest_capital()
        positions    = monitor.get_positions_summary()
        today_trades = db.get_trades_for_date(date.today().isoformat())

        capital   = capital_rec["total_capital"] if capital_rec else 0
        daily_pnl = session.pnl_today

        closed_today = [t for t in today_trades if t["status"] == "closed"]
        wins     = sum(1 for t in closed_today if t.get("pnl", 0) > 0)
        win_rate = (wins / len(closed_today) * 100) if closed_today else 0

        context = (
            f"[BOT STATUS {datetime.now().strftime('%H:%M')}] "
            f"Capital: ${capital:,.2f} | "
            f"P&L: ${daily_pnl:+,.2f} | "
            f"Trading: {'ON' if session.trading_active else 'HALTED'} | "
            f"Trades: {session.trades_today} | "
            f"Win rate: {win_rate:.0f}% | "
            f"Consec losses: {session.consecutive_losses}\n"
        )

        if positions:
            context += f"OPEN ({len(positions)}): "
            context += " | ".join(
                f"{p['symbol']} {p['direction'].upper()} "
                f"${p['unrealized_pnl']:+.2f} ({p['pnl_pct']:+.1f}%)"
                for p in positions
            ) + "\n"

        if closed_today:
            recent = closed_today[-5:]
            context += "RECENT TRADES: "
            context += " | ".join(
                f"{t['symbol']} {'W' if t.get('pnl',0)>0 else 'L'} "
                f"${t.get('pnl',0):+.2f}"
                for t in recent
            ) + "\n"

        return context

    def chat(self, user_message: str) -> str:
        import os
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))
        api_key = config.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return (
                "Chat interface requires an Anthropic API key. "
                "Add ANTHROPIC_API_KEY to your .env file."
            )

        logger.info(f"[CLAUDE] User message: {user_message[:120]}")
        self._last_user_message = user_message

        try:
            db.log_chat_action(
                user_message = user_message,
                action_type  = "message",
                action_detail= "",
                result       = ""
            )
        except Exception:
            pass

        # --- Pre-parse layer: handle simple commands without Haiku ---
        pre_results = self._pre_parse(user_message)
        if pre_results is not None:
            reply = "\n".join(pre_results)
            # Add to history so Haiku has context on follow-up messages
            self.conversation_history.append(
                {"role": "user", "content": user_message}
            )
            self.conversation_history.append(
                {"role": "assistant", "content": reply}
            )
            return reply

        # --- Full Haiku call for everything else ---
        context       = self._build_context()
        full_user_msg = f"{context}\nUser: {user_message}"

        self.conversation_history.append(
            {"role": "user", "content": full_user_msg}
        )

        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = \
                self.conversation_history[-self.max_history * 2:]

        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":          api_key,
                    "anthropic-version":  "2023-06-01",
                    "content-type":       "application/json"
                },
                json={
                    "model":      CLAUDE_MODEL,
                    "max_tokens": 512,
                    "system":     SYSTEM_PROMPT,
                    "messages":   self.conversation_history
                },
                timeout=30
            )
            response.raise_for_status()
            data            = response.json()
            assistant_reply = data["content"][0]["text"]

            self.conversation_history.append(
                {"role": "assistant", "content": assistant_reply}
            )

            action_results = self._parse_and_execute_actions(
                assistant_reply, user_message
            )
            if action_results:
                assistant_reply += "\n\n" + "\n".join(action_results)

            return assistant_reply

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return (
                f"Chat interface error: {str(e)}. "
                "Bot is still running normally."
            )

    def _parse_and_execute_actions(
        self, response_text: str, user_message: str = ""
    ) -> List[str]:
        results = []
        json_matches = re.findall(r'\{[^{}]+\}', response_text)

        for match in json_matches:
            try:
                cmd    = json.loads(match)
                action = cmd.get("action")
                if not action:
                    continue

                result_msg = ""

                if action == "halt_trading":
                    reason = cmd.get("reason", "User request via chat")
                    risk_manager.manual_halt(reason)
                    result_msg = f"Trading halted: {reason}"
                    logger.info(f"[CLAUDE] ACTION halt_trading | reason={reason}")

                elif action == "resume_trading":
                    risk_manager.manual_resume()
                    result_msg = "Trading resumed."
                    logger.info("[CLAUDE] ACTION resume_trading")

                elif action == "withdraw":
                    amount = float(cmd.get("amount", 0))
                    reason = cmd.get("reason", "Withdrawal")
                    res    = risk_manager.process_withdrawal(amount, reason)
                    result_msg = res["message"]
                    logger.info(f"[CLAUDE] ACTION withdraw | amount=${amount:.2f} reason={reason}")

                elif action == "set_risk":
                    param = cmd.get("param")
                    value = cmd.get("value")
                    if hasattr(config, param):
                        setattr(config, param, value)
                        result_msg = f"Risk setting updated: {param} = {value}"
                        db.set_state(f"risk_{param}", value)
                        logger.info(f"[CLAUDE] ACTION set_risk | {param}={value}")
                    else:
                        result_msg = f"Unknown config param: {param}"

                elif action == "export_taxes":
                    year     = cmd.get("year", datetime.now().year)
                    filepath = f"exports/tax_form_8949_{year}.csv"
                    db.export_8949_csv(year, filepath)
                    result_msg = f"Tax export saved: {filepath}"
                    logger.info(f"[CLAUDE] ACTION export_taxes | year={year}")

                elif action == "list_strategies":
                    from strategies.strategy_engine import strategy_engine
                    strategies = strategy_engine.list_strategies()
                    info = "\n".join(
                        f"  {'ON' if s['enabled'] else 'OFF'} {s['name']}"
                        for s in strategies
                    )
                    result_msg = f"Strategies:\n{info}"
                    logger.info("[CLAUDE] ACTION list_strategies")

                elif action == "enable_strategy":
                    from strategies.strategy_engine import strategy_engine
                    name = cmd.get("name", "")
                    result_msg = strategy_engine.enable_strategy(name)
                    logger.info(f"[CLAUDE] ACTION enable_strategy | name={name}")

                elif action == "disable_strategy":
                    from strategies.strategy_engine import strategy_engine
                    name = cmd.get("name", "")
                    result_msg = strategy_engine.disable_strategy(name)
                    logger.info(f"[CLAUDE] ACTION disable_strategy | name={name}")

                elif action == "strategy_stats":
                    from strategies.strategy_engine import strategy_engine
                    all_stats = strategy_engine.get_all_stats()
                    info = ""
                    for s in all_stats:
                        status = "ON" if s["enabled"] else "OFF"
                        info += (
                            f"\n{status} {s['strategy_name']}: "
                            f"{s['total_trades']} trades | "
                            f"Win rate: {s['win_rate']:.1f}% | "
                            f"P&L: ${s['total_pnl']:+.2f}"
                        )
                    result_msg = f"Strategy Performance:{info}"
                    logger.info("[CLAUDE] ACTION strategy_stats")

                elif action == "morning_scan":
                    result_msg = self._run_morning_scan()
                    logger.info("[CLAUDE] ACTION morning_scan")

                elif action == "list_brokers":
                    from core.broker_manager import broker_manager
                    brokers = broker_manager.list_brokers()
                    info = ""
                    for b in brokers:
                        paper = " (PAPER)" if b.get("paper") else ""
                        info += (
                            f"\n  {'ON' if b['enabled'] else 'OFF'} "
                            f"{b['display_name']} [{b['name']}]{paper}"
                        )
                    result_msg = f"Registered Brokers:{info}"
                    logger.info("[CLAUDE] ACTION list_brokers")

                elif action == "inject_funds":
                    from core.broker_manager import broker_manager
                    broker = cmd.get("broker", "")
                    amount = float(cmd.get("amount", 0))
                    reason = cmd.get("reason", "Fund deposit")
                    res    = broker_manager.inject_funds(broker, amount, reason)
                    result_msg = res["message"]
                    logger.info(f"[CLAUDE] ACTION inject_funds | broker={broker} amount=${amount:.2f}")

                elif action == "withdraw_funds":
                    from core.broker_manager import broker_manager
                    broker = cmd.get("broker", "")
                    amount = float(cmd.get("amount", 0))
                    reason = cmd.get("reason", "Withdrawal")
                    res    = broker_manager.withdraw_funds(broker, amount, reason)
                    result_msg = res["message"]
                    logger.info(f"[CLAUDE] ACTION withdraw_funds | broker={broker} amount=${amount:.2f}")

                elif action == "capital_breakdown":
                    from core.broker_manager import broker_manager
                    breakdown = broker_manager.get_capital_breakdown()
                    info  = f"\nTotal: ${breakdown['total_balance']:,.2f}"
                    info += f" | Invested: ${breakdown['total_invested']:,.2f}"
                    info += f" | Available: ${breakdown['total_available']:,.2f}"
                    for b in breakdown["brokers"]:
                        paper = " (PAPER)" if b.get("paper") else ""
                        info += f"\n  {b['display_name']}{paper}: ${b['balance']:,.2f}"
                    result_msg = f"Capital Breakdown:{info}"
                    logger.info("[CLAUDE] ACTION capital_breakdown")

                elif action == "enable_broker":
                    from core.broker_manager import broker_manager
                    name = cmd.get("name", "")
                    result_msg = broker_manager.enable_broker(name)
                    logger.info(f"[CLAUDE] ACTION enable_broker | name={name}")

                elif action == "disable_broker":
                    from core.broker_manager import broker_manager
                    name = cmd.get("name", "")
                    result_msg = broker_manager.disable_broker(name)
                    logger.info(f"[CLAUDE] ACTION disable_broker | name={name}")

                if result_msg:
                    results.append(result_msg)
                    try:
                        db.log_chat_action(
                            user_message = user_message,
                            action_type  = action,
                            action_detail= json.dumps(
                                {k: v for k, v in cmd.items() if k != "action"}
                            ),
                            result       = result_msg[:200]
                        )
                    except Exception:
                        pass

            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        return results

    def clear_history(self):
        self.conversation_history = []
        logger.info("Chat history cleared.")


# Singleton
chat = ChatInterface()
