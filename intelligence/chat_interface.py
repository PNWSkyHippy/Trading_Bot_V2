"""
=============================================================
  CLAUDE AI CHAT INTERFACE
  Lets you talk to your trading bot in plain English.

  Model: claude-haiku-4-5-20251001 (cheapest Claude, fast)
  Cost controls:
    - max_tokens capped at 512
    - context trimmed to essentials only
    - conversation history capped at 10 turns

  Activity logging:
    Every user message and every action executed is logged
    to the chat_actions table in the database.
    Search logs for [CLAUDE] to see all activity.
    EOD report includes a Claude Activity Summary section.
=============================================================
"""

import json
import logging
import requests
from datetime import date, datetime
from typing import List, Dict

import config
from data.database import db
from core.risk_manager import risk_manager
from core.position_monitor import monitor

logger = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are the AI controller for an autonomous day trading bot.
Help the owner monitor and control it through natural conversation.
Be concise. Use numbers. Confirm before withdrawals.

CRITICAL RULES — read carefully before taking any action:
- NEVER halt trading unless the user gives an EXPLICIT, DIRECT instruction like
  "halt trading", "pause trading", or "stop all trades".
- Do NOT infer intent from vague statements. If the user says something ambiguous
  like "resources are used up", "I'm exhausted", "things are slow", or "the budget
  ran out" — these are NOT instructions to halt trading. Ask for clarification instead.
- Only execute an action when you are 100% certain that is what the user is asking for.
- When in doubt, ASK. Never assume a command from conversational language.
- Treat halt_trading and withdraw as high-risk actions requiring explicit confirmation.

You can execute commands by including JSON in your response:
{"action": "halt_trading", "reason": "user request"}
{"action": "resume_trading"}
{"action": "withdraw", "amount": 500.00, "reason": "living expenses"}
{"action": "set_risk", "param": "MAX_POSITION_PCT", "value": 1.5}
{"action": "generate_report", "type": "daily"}
{"action": "export_taxes", "year": 2025}
{"action": "list_strategies"}
{"action": "enable_strategy", "name": "scalp_master"}
{"action": "disable_strategy", "name": "grid_bot"}
{"action": "strategy_stats"}
{"action": "list_brokers"}
{"action": "inject_funds", "broker": "kraken", "amount": 500.00, "reason": "deposit"}
{"action": "withdraw_funds", "broker": "alpaca", "amount": 200.00, "reason": "rent"}
{"action": "capital_breakdown"}
{"action": "enable_broker", "name": "kraken"}
{"action": "disable_broker", "name": "kraken"}

Fund injections/withdrawals are INFORMATIONAL ONLY — user moves money manually."""


class ChatInterface:

    def __init__(self):
        self.conversation_history: List[Dict] = []
        self.max_history = 10
        self._last_user_message = ""

    def _build_context(self) -> str:
        session      = risk_manager.get_daily_status()
        capital_rec  = db.get_latest_capital()
        positions    = monitor.get_positions_summary()
        today_trades = db.get_trades_for_date(date.today().isoformat())

        capital   = capital_rec["total_capital"] if capital_rec else 0
        daily_pnl = session.pnl_today
        starting  = capital - daily_pnl

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
        import re
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
