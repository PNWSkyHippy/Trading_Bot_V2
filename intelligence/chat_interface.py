"""
=============================================================
  CLAUDE AI CHAT INTERFACE
  Lets you talk to your trading bot in plain English.
  Commands include: pause trading, show stats, withdraw funds,
  change risk settings, view positions, generate reports,
  manage strategies, manage brokers, inject/withdraw funds.
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

SYSTEM_PROMPT = """You are the AI controller for an autonomous day trading system.
You help the owner monitor and control their trading bot through natural conversation.

You have access to live data provided in each message including:
- Current capital and daily P&L
- Open positions with unrealized gains/losses
- Today's trade history
- Risk settings and session status

You can execute the following commands by including them in your response as JSON:
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
{"action": "inject_funds", "broker": "kraken", "amount": 500.00, "reason": "initial deposit"}
{"action": "withdraw_funds", "broker": "alpaca", "amount": 200.00, "reason": "rent"}
{"action": "capital_breakdown"}
{"action": "add_broker", "name": "kraken", "type": "crypto", "display_name": "Kraken"}
{"action": "enable_broker", "name": "kraken"}
{"action": "disable_broker", "name": "kraken"}

IMPORTANT RULES:
- You manage capital belonging solely to the user. Never suggest external transfers.
- Be concise but thorough. Use numbers when discussing performance.
- Always confirm before executing withdraw commands.
- Fund injections and withdrawals are INFORMATIONAL ONLY — the user moves money manually.
- If trading is halted, explain why and what conditions would allow resumption.
- Keep responses conversational and direct. Use dollar signs and percentages clearly.
- You genuinely care about the user's financial wellbeing and long-term goals.
"""


class ChatInterface:

    def __init__(self):
        self.conversation_history: List[Dict] = []
        self.max_history = 20

    def _build_context(self) -> str:
        session      = risk_manager.get_daily_status()
        capital_rec  = db.get_latest_capital()
        positions    = monitor.get_positions_summary()
        today_trades = db.get_trades_for_date(date.today().isoformat())
        summaries    = db.get_daily_summaries(7)

        capital   = capital_rec["total_capital"] if capital_rec else 0
        daily_pnl = session.pnl_today
        starting  = capital - daily_pnl

        closed_today = [t for t in today_trades if t["status"] == "closed"]
        wins     = sum(1 for t in closed_today if t.get("pnl", 0) > 0)
        win_rate = (wins / len(closed_today) * 100) if closed_today else 0

        broker_info = ""
        try:
            from core.broker_manager import broker_manager
            breakdown = broker_manager.get_capital_breakdown()
            for b in breakdown["brokers"]:
                paper = " (PAPER)" if b.get("paper") else ""
                broker_info += (
                    f"  {b['display_name']}{paper}: ${b['balance']:,.2f} "
                    f"(invested: ${b['invested']:,.2f}, "
                    f"available: ${b['available']:,.2f})\n"
                )
        except Exception:
            broker_info = "  (broker manager not available)\n"

        daily_target = starting * (config.DAILY_PROFIT_TARGET_PCT / 100)

        context = f"""
=== LIVE TRADING BOT STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===

CAPITAL:
  Current Total:   ${capital:,.2f}
  Today Starting:  ${starting:,.2f}
  Daily P&L:       ${daily_pnl:+,.2f} ({(daily_pnl/starting*100) if starting else 0:+.2f}%)
  Daily Target:    ${daily_target:,.2f} ({config.DAILY_PROFIT_TARGET_PCT:.0f}%)

CAPITAL BY BROKER:
{broker_info}
SESSION:
  Trading Active:     {'YES' if session.trading_active else 'HALTED'}
  Halt Reason:        {session.halt_reason or 'N/A'}
  Trades Today:       {session.trades_today}
  Consecutive Losses: {session.consecutive_losses}
  Daily Loss Remaining: ${session.daily_loss_remaining:,.2f}
  Today Win Rate:     {win_rate:.1f}% ({wins}W / {len(closed_today)-wins}L)

OPEN POSITIONS ({len(positions)}):
"""
        for pos in positions:
            context += (
                f"  {pos['symbol']} {pos['direction'].upper()} | "
                f"Entry: ${pos['entry_price']:.4f} | Now: ${pos['current_price']:.4f} | "
                f"P&L: ${pos['unrealized_pnl']:+.2f} ({pos['pnl_pct']:+.2f}%) | "
                f"SL: ${pos['stop_loss']:.4f} | TP: ${pos['take_profit']:.4f}\n"
            )
        if not positions:
            context += "  No open positions.\n"

        context += "\nTODAY'S CLOSED TRADES:\n"
        for t in closed_today[-10:]:
            pnl = t.get("pnl", 0)
            context += (
                f"  {t['symbol']} {t['direction'].upper()} -> "
                f"{'WIN' if pnl > 0 else 'LOSS'} ${pnl:+.2f} "
                f"({t.get('pnl_pct', 0):+.2f}%) [{t.get('exit_reason', '')}]\n"
            )
        if not closed_today:
            context += "  No closed trades today.\n"

        context += "\nRECENT DAILY SUMMARIES (last 7 days):\n"
        for s in summaries[:7]:
            goal   = "Y" if s.get("goal_met") else "N"
            halted = " HALTED" if s.get("trading_halted") else ""
            context += (
                f"  {s['trade_date']}: ${s['daily_pnl']:+.2f} "
                f"({s['daily_pnl_pct']:+.2f}%) | "
                f"{s['winning_trades']}W/{s['losing_trades']}L | "
                f"Capital: ${s['ending_capital']:,.2f} Goal:{goal}{halted}\n"
            )

        context += "\nRISK SETTINGS:\n"
        context += f"  Max position:    {config.MAX_POSITION_PCT:.0f}% of capital\n"
        context += f"  Stop-loss:       {config.DEFAULT_STOP_LOSS_PCT:.0f}%\n"
        context += f"  Take-profit:     {config.DEFAULT_TAKE_PROFIT_PCT:.0f}%\n"
        context += f"  Max daily loss:  {config.MAX_DAILY_LOSS_PCT:.0f}%\n"
        context += f"  Max positions:   {config.MAX_OPEN_POSITIONS}\n"
        context += (
            f"  Min confidence:  "
            f"{config.SIGNAL_TUNING.get('min_signal_confidence', config.MIN_SIGNAL_CONFIDENCE):.2f}\n"
        )

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
        context      = self._build_context()
        full_user_msg= f"{context}\n\nUser message: {user_message}"

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
                    "x-api-key": api_key,
                    "anthropic-version":  "2023-06-01",
                    "content-type":       "application/json"
                },
                json={
                    "model":      "claude-sonnet-4-6",
                    "max_tokens": 1024,
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

            action_results = self._parse_and_execute_actions(assistant_reply)
            if action_results:
                assistant_reply += "\n\n" + "\n".join(action_results)

            return assistant_reply

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return (
                f"Chat interface error: {str(e)}. "
                "Bot is still running normally."
            )

    def _parse_and_execute_actions(self, response_text: str) -> List[str]:
        results = []
        import re
        json_matches = re.findall(r'\{[^{}]+\}', response_text)

        for match in json_matches:
            try:
                cmd    = json.loads(match)
                action = cmd.get("action")

                if action == "halt_trading":
                    reason = cmd.get("reason", "User request via chat")
                    risk_manager.manual_halt(reason)
                    results.append(f"Trading halted: {reason}")

                elif action == "resume_trading":
                    risk_manager.manual_resume()
                    results.append("Trading resumed.")

                elif action == "withdraw":
                    amount = float(cmd.get("amount", 0))
                    reason = cmd.get("reason", "Withdrawal")
                    result = risk_manager.process_withdrawal(amount, reason)
                    results.append(result["message"])

                elif action == "set_risk":
                    param = cmd.get("param")
                    value = cmd.get("value")
                    if hasattr(config, param):
                        setattr(config, param, value)
                        results.append(f"Risk setting updated: {param} = {value}")
                        db.set_state(f"risk_{param}", value)
                    else:
                        results.append(f"Unknown config param: {param}")

                elif action == "export_taxes":
                    year     = cmd.get("year", datetime.now().year)
                    filepath = f"exports/tax_form_8949_{year}.csv"
                    db.export_8949_csv(year, filepath)
                    results.append(f"Tax export saved: {filepath}")

                elif action == "list_strategies":
                    from strategies.strategy_engine import strategy_engine
                    strategies = strategy_engine.list_strategies()
                    info = "\n".join(
                        f"  {'ON' if s['enabled'] else 'OFF'} "
                        f"{s['name']}: {s.get('description', '')}"
                        for s in strategies
                    )
                    results.append(f"Strategies:\n{info}")

                elif action == "enable_strategy":
                    from strategies.strategy_engine import strategy_engine
                    msg = strategy_engine.enable_strategy(cmd.get("name", ""))
                    results.append(msg)

                elif action == "disable_strategy":
                    from strategies.strategy_engine import strategy_engine
                    msg = strategy_engine.disable_strategy(cmd.get("name", ""))
                    results.append(msg)

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
                            f"P&L: ${s['total_pnl']:+.2f} | "
                            f"PF: {s['profit_factor']:.2f}"
                        )
                    results.append(f"Strategy Performance:{info}")

                elif action == "list_brokers":
                    from core.broker_manager import broker_manager
                    brokers = broker_manager.list_brokers()
                    info = ""
                    for b in brokers:
                        paper = " (PAPER)" if b.get("paper") else ""
                        info += (
                            f"\n  {'ON' if b['enabled'] else 'OFF'} "
                            f"{b['display_name']} [{b['name']}] - "
                            f"{b['broker_type']}{paper}"
                        )
                    results.append(f"Registered Brokers:{info}")

                elif action == "inject_funds":
                    from core.broker_manager import broker_manager
                    broker = cmd.get("broker", "")
                    amount = float(cmd.get("amount", 0))
                    reason = cmd.get("reason", "Fund deposit")
                    result = broker_manager.inject_funds(broker, amount, reason)
                    results.append(result["message"])

                elif action == "withdraw_funds":
                    from core.broker_manager import broker_manager
                    broker = cmd.get("broker", "")
                    amount = float(cmd.get("amount", 0))
                    reason = cmd.get("reason", "Withdrawal")
                    result = broker_manager.withdraw_funds(broker, amount, reason)
                    results.append(result["message"])

                elif action == "capital_breakdown":
                    from core.broker_manager import broker_manager
                    breakdown = broker_manager.get_capital_breakdown()
                    info  = f"\nTotal Capital:    ${breakdown['total_balance']:,.2f}"
                    info += f"\nTotal Invested:   ${breakdown['total_invested']:,.2f}"
                    info += f"\nTotal Available:  ${breakdown['total_available']:,.2f}"
                    info += f"\n\nPer Broker:"
                    for b in breakdown["brokers"]:
                        paper = " (PAPER)" if b.get("paper") else ""
                        info += (
                            f"\n  {b['display_name']}{paper}: "
                            f"${b['balance']:,.2f} "
                            f"(invested: ${b['invested']:,.2f}, "
                            f"available: ${b['available']:,.2f})"
                        )
                    results.append(f"Capital Breakdown:{info}")

                elif action == "add_broker":
                    from core.broker_manager import broker_manager
                    msg = broker_manager.register_broker(
                        name         = cmd.get("name", ""),
                        broker_type  = cmd.get("type", "crypto"),
                        display_name = cmd.get("display_name", ""),
                    )
                    results.append(msg)

                elif action == "enable_broker":
                    from core.broker_manager import broker_manager
                    msg = broker_manager.enable_broker(cmd.get("name", ""))
                    results.append(msg)

                elif action == "disable_broker":
                    from core.broker_manager import broker_manager
                    msg = broker_manager.disable_broker(cmd.get("name", ""))
                    results.append(msg)

            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        return results

    def clear_history(self):
        self.conversation_history = []
        logger.info("Chat history cleared.")


# Singleton
chat = ChatInterface()
