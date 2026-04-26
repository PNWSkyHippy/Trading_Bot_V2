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
    Simple commands (enable/disable strategy, morning scan, watchlist
    queries, reload watchlist) are detected directly from the user
    message BEFORE sending to Haiku. This bypasses Haiku's tendency
    to second-guess simple commands and ensures they always execute
    reliably.

  Watchlist commands (pre-parsed, no Haiku needed):
    "what stocks are you watching"    → lists master + injected stocks
    "what crypto are you watching"    → lists master + injected crypto
    "show watchlist"                  → full combined watchlist
    "show injected symbols"           → only temp/injected symbols
    "is AAPL in watchlist"            → checks if specific symbol active
    "is BTC/USD being watched"        → same for crypto
    "reload watchlist"                → reloads temp files into memory
    "refresh watchlist"               → same as reload

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
from pathlib import Path
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

# Watchlist file paths
WATCHLIST_DIR        = Path("watchlists")
MASTER_STOCKS_FILE   = WATCHLIST_DIR / "stocks.txt"
MASTER_CRYPTO_FILE   = WATCHLIST_DIR / "crypto.txt"
TEMP_STOCKS_FILE     = Path("watchlist/scanned_stocks.txt")
TEMP_CRYPTO_FILE     = Path("watchlist/scanned_crypto.txt")

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
scalp_master, swing_trader, grid_bot, dca_accumulator, vwap_momentum,
hammer_reversal, orb_breakout

When user says "enable X" or "disable X" — execute IMMEDIATELY, no questions.
Do NOT say the strategy doesn't exist. Do NOT list strategies first. Just do it.

MORNING SCAN command:
When user says "morning scan" or "what should I trade" or "top setups":
- Execute {"action": "morning_scan"} immediately
- This surfaces top ORB and momentum candidates for manual trading

WATCHLIST commands are handled by pre-parse layer — do NOT attempt to answer
watchlist queries yourself. They are already handled before reaching you.

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
    #  WATCHLIST HELPERS
    # ------------------------------------------------------------------

    def _read_watchlist_file(self, filepath: Path) -> List[str]:
        """Read a watchlist file and return list of symbols, ignoring comments."""
        if not filepath.exists():
            return []
        try:
            lines = filepath.read_text().splitlines()
            return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
        except Exception:
            return []

    def _get_active_stocks(self) -> tuple[List[str], List[str]]:
        """
        Returns (master_stocks, injected_stocks).
        Master = from watchlists/stocks.txt
        Injected = from watchlist/scanned_stocks.txt (temp, from scanner or dashboard)
        """
        master   = self._read_watchlist_file(MASTER_STOCKS_FILE)
        injected = self._read_watchlist_file(TEMP_STOCKS_FILE)
        return master, injected

    def _get_active_crypto(self) -> tuple[List[str], List[str]]:
        """
        Returns (master_crypto, injected_crypto).
        Master = from watchlists/crypto.txt
        Injected = from watchlist/scanned_crypto.txt
        """
        master   = self._read_watchlist_file(MASTER_CRYPTO_FILE)
        injected = self._read_watchlist_file(TEMP_CRYPTO_FILE)
        return master, injected

    def _check_symbol_in_watchlist(self, symbol: str) -> str:
        """Check if a specific symbol is in any watchlist and report where."""
        sym_upper = symbol.upper().strip()
        # Normalize — add /USD if crypto-like and no slash
        is_crypto_query = "/" in sym_upper or any(
            sym_upper == s for s in [
                "BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA",
                "AVAX", "DOT", "LINK", "MATIC", "LTC", "UNI", "ATOM"
            ]
        )

        found_in = []

        # Check stocks master
        master_stocks, injected_stocks = self._get_active_stocks()
        if sym_upper in [s.upper() for s in master_stocks]:
            found_in.append("master stock watchlist")
        if sym_upper in [s.upper() for s in injected_stocks]:
            found_in.append("injected stocks (today only)")

        # Check crypto master — try both formats (BTC and BTC/USD)
        master_crypto, injected_crypto = self._get_active_crypto()
        crypto_syms = [s.upper() for s in master_crypto]
        crypto_base = [s.split("/")[0].upper() for s in master_crypto]
        if sym_upper in crypto_syms or sym_upper in crypto_base:
            found_in.append("master crypto watchlist")

        inj_syms = [s.upper() for s in injected_crypto]
        inj_base = [s.split("/")[0].upper() for s in injected_crypto]
        if sym_upper in inj_syms or sym_upper in inj_base:
            found_in.append("injected crypto (today only)")

        if found_in:
            return f"✅ {sym_upper} is active — found in: {', '.join(found_in)}"
        else:
            return (
                f"❌ {sym_upper} is NOT currently being watched.\n"
                f"Use the dashboard Inject Symbols panel or say "
                f"'add {sym_upper} to watchlist' to add it temporarily."
            )

    def _handle_watchlist_query(self, msg: str) -> Optional[str]:
        """
        Handle watchlist-related queries from the pre-parse layer.
        Returns formatted response string or None if not a watchlist query.
        """
        msg_lower = msg.lower().strip()

        # ── "is X in watchlist / being watched" ──────────────────────────
        # Patterns: "is AAPL in watchlist", "is BTC/USD being watched",
        #           "are you watching TSLA", "do you have SOL"
        is_watching_patterns = [
            r'\bis\s+(\S+)\s+(?:in\s+(?:the\s+)?watchlist|being\s+watched)',
            r'\bare\s+you\s+watching\s+(\S+)',
            r'\bdo\s+you\s+(?:have|watch|track)\s+(\S+)',
            r'\bwatching\s+(\S+)\b',
            r'\bcheck\s+(?:if\s+)?(\S+)\s+(?:is\s+)?(?:in\s+)?(?:the\s+)?watchlist',
        ]
        for pattern in is_watching_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                symbol = match.group(1).upper().rstrip("?.,")
                # Filter out common words that aren't symbols
                if symbol not in {"THE", "A", "AN", "MY", "YOUR", "IT", "THIS"}:
                    logger.info(f"[CLAUDE] PRE-PARSE watchlist_check | symbol={symbol}")
                    return self._check_symbol_in_watchlist(symbol)

        # ── Show injected/scanned symbols only ───────────────────────────
        if any(p in msg_lower for p in [
            "show injected", "injected symbols", "scanned symbols",
            "what did scanner find", "scanner results", "what was injected"
        ]):
            _, injected_stocks = self._get_active_stocks()
            _, injected_crypto = self._get_active_crypto()
            lines = ["📋 Currently Injected Symbols (temporary, today only):\n"]
            if injected_stocks:
                lines.append(f"📈 Stocks ({len(injected_stocks)}): {', '.join(injected_stocks)}")
            else:
                lines.append("📈 Stocks: none injected")
            if injected_crypto:
                lines.append(f"🪙 Crypto ({len(injected_crypto)}): {', '.join(injected_crypto)}")
            else:
                lines.append("🪙 Crypto: none injected")
            lines.append("\nThese were added by the daily scanner or dashboard injection.")
            lines.append("They reset on next scan or reboot.")
            logger.info("[CLAUDE] PRE-PARSE show_injected")
            return "\n".join(lines)

        # ── Full watchlist ────────────────────────────────────────────────
        if any(p in msg_lower for p in [
            "show watchlist", "full watchlist", "all watchlist",
            "list watchlist", "what's in watchlist", "whats in watchlist"
        ]):
            master_stocks, injected_stocks = self._get_active_stocks()
            master_crypto, injected_crypto = self._get_active_crypto()
            lines = ["📋 Full Active Watchlist:\n"]
            lines.append(
                f"📈 Master Stocks ({len(master_stocks)}): "
                f"{', '.join(master_stocks[:20])}"
                f"{'...' if len(master_stocks) > 20 else ''}"
            )
            if injected_stocks:
                lines.append(
                    f"📈 + Injected Stocks ({len(injected_stocks)}): "
                    f"{', '.join(injected_stocks)}"
                )
            lines.append(
                f"🪙 Master Crypto ({len(master_crypto)}): "
                f"{', '.join(master_crypto[:20])}"
                f"{'...' if len(master_crypto) > 20 else ''}"
            )
            if injected_crypto:
                lines.append(
                    f"🪙 + Injected Crypto ({len(injected_crypto)}): "
                    f"{', '.join(injected_crypto)}"
                )
            logger.info("[CLAUDE] PRE-PARSE show_full_watchlist")
            return "\n".join(lines)

        # ── Stocks watchlist only ─────────────────────────────────────────
        if any(p in msg_lower for p in [
            "what stocks", "which stocks", "stocks watching",
            "stock watchlist", "list stocks"
        ]):
            master_stocks, injected_stocks = self._get_active_stocks()
            lines = [f"📈 Stock Watchlist:\n"]
            lines.append(
                f"Master ({len(master_stocks)}): "
                f"{', '.join(master_stocks)}"
            )
            if injected_stocks:
                lines.append(
                    f"\nInjected today ({len(injected_stocks)}): "
                    f"{', '.join(injected_stocks)}"
                )
            else:
                lines.append("\nNo stocks injected today.")
            logger.info("[CLAUDE] PRE-PARSE show_stock_watchlist")
            return "\n".join(lines)

        # ── Crypto watchlist only ─────────────────────────────────────────
        if any(p in msg_lower for p in [
            "what crypto", "which crypto", "crypto watching",
            "crypto watchlist", "list crypto"
        ]):
            master_crypto, injected_crypto = self._get_active_crypto()
            lines = [f"🪙 Crypto Watchlist:\n"]
            lines.append(
                f"Master ({len(master_crypto)}): "
                f"{', '.join(master_crypto)}"
            )
            if injected_crypto:
                lines.append(
                    f"\nInjected today ({len(injected_crypto)}): "
                    f"{', '.join(injected_crypto)}"
                )
            else:
                lines.append("\nNo crypto injected today.")
            logger.info("[CLAUDE] PRE-PARSE show_crypto_watchlist")
            return "\n".join(lines)

        # ── Reload watchlist from temp files ─────────────────────────────
        if any(p in msg_lower for p in [
            "reload watchlist", "refresh watchlist",
            "reload symbols", "refresh symbols",
            "load scanner results", "pick up scanner"
        ]):
            return self._reload_watchlist()

        return None  # Not a watchlist query

    def _reload_watchlist(self) -> str:
        """
        Reload temp watchlist files into the bot's in-memory lists.
        This picks up new scanner results or dashboard injections without
        requiring a full bot reboot.
        """
        try:
            from market_scanner import load_watchlist_temps
            scanned_stocks, scanned_crypto = load_watchlist_temps()

            reloaded = []

            if scanned_stocks:
                # Update bot engine's stock watchlist if accessible
                try:
                    import bot_engine as _be
                    existing = getattr(_be.bot, "stock_watchlist", [])
                    _be.bot.stock_watchlist = scanned_stocks + [
                        t for t in existing if t not in scanned_stocks
                    ]
                    reloaded.append(f"{len(scanned_stocks)} stocks")
                except Exception:
                    # Bot engine not directly accessible — file is updated,
                    # will load on next scan cycle
                    reloaded.append(
                        f"{len(scanned_stocks)} stocks (file updated, "
                        f"active on next scan cycle)"
                    )

            if scanned_crypto:
                try:
                    import bot_engine as _be
                    existing = getattr(_be.bot, "crypto_watchlist", [])
                    _be.bot.crypto_watchlist = scanned_crypto + [
                        p for p in existing if p not in scanned_crypto
                    ]
                    reloaded.append(f"{len(scanned_crypto)} crypto pairs")
                except Exception:
                    reloaded.append(
                        f"{len(scanned_crypto)} crypto pairs (file updated, "
                        f"active on next scan cycle)"
                    )

            if reloaded:
                logger.info(f"[CLAUDE] PRE-PARSE reload_watchlist | {', '.join(reloaded)}")
                return (
                    f"✅ Watchlist reloaded: {', '.join(reloaded)}\n"
                    f"Injected symbols are now active for signal scanning."
                )
            else:
                return (
                    "📋 No injected symbols found in temp files.\n"
                    "Run the market scanner or inject symbols via the dashboard first."
                )

        except Exception as e:
            logger.error(f"Watchlist reload error: {e}")
            return f"Watchlist reload error: {e}"

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
        - watchlist queries (show, check, reload)
        """
        msg = user_message.strip().lower()

        # --- watchlist queries (check before strategy names to avoid conflicts) ---
        watchlist_result = self._handle_watchlist_query(msg)
        if watchlist_result is not None:
            return [watchlist_result]

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

            now_et   = datetime.now(ZoneInfo("America/New_York"))
            time_str = now_et.strftime("%H:%M ET")

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

                    bars = scanner.stock_scanner.get_bars(
                        symbol, timeframe="5Min", limit=20
                    )
                    if bars is None or len(bars) < 5:
                        continue

                    closes     = bars["close"]
                    volumes    = bars["volume"]
                    open_price = float(closes.iloc[0])
                    curr_price = float(closes.iloc[-1])
                    avg_vol    = float(volumes.iloc[:-1].mean())
                    curr_vol   = float(volumes.iloc[-1])
                    pct_move   = (curr_price - open_price) / open_price * 100
                    vol_ratio  = curr_vol / avg_vol if avg_vol > 0 else 0

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

            results.sort(key=lambda x: x[0] * x[1], reverse=True)
            top   = results[:5]
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
        load_dotenv(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), '..', '.env'
            )
        )
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
                user_message  = user_message,
                action_type   = "message",
                action_detail = "",
                result        = ""
            )
        except Exception:
            pass

        # --- Pre-parse layer: handle simple commands without Haiku ---
        pre_results = self._pre_parse(user_message)
        if pre_results is not None:
            reply = "\n".join(pre_results)
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
                    "x-api-key":         api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json"
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
        results      = []
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
                    logger.info(
                        f"[CLAUDE] ACTION withdraw | "
                        f"amount=${amount:.2f} reason={reason}"
                    )

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
                    logger.info(
                        f"[CLAUDE] ACTION inject_funds | "
                        f"broker={broker} amount=${amount:.2f}"
                    )

                elif action == "withdraw_funds":
                    from core.broker_manager import broker_manager
                    broker = cmd.get("broker", "")
                    amount = float(cmd.get("amount", 0))
                    reason = cmd.get("reason", "Withdrawal")
                    res    = broker_manager.withdraw_funds(broker, amount, reason)
                    result_msg = res["message"]
                    logger.info(
                        f"[CLAUDE] ACTION withdraw_funds | "
                        f"broker={broker} amount=${amount:.2f}"
                    )

                elif action == "capital_breakdown":
                    from core.broker_manager import broker_manager
                    breakdown = broker_manager.get_capital_breakdown()
                    info  = f"\nTotal: ${breakdown['total_balance']:,.2f}"
                    info += f" | Invested: ${breakdown['total_invested']:,.2f}"
                    info += f" | Available: ${breakdown['total_available']:,.2f}"
                    for b in breakdown["brokers"]:
                        paper = " (PAPER)" if b.get("paper") else ""
                        info += (
                            f"\n  {b['display_name']}{paper}: "
                            f"${b['balance']:,.2f}"
                        )
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
                            user_message  = user_message,
                            action_type   = action,
                            action_detail = json.dumps(
                                {k: v for k, v in cmd.items() if k != "action"}
                            ),
                            result        = result_msg[:200]
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
