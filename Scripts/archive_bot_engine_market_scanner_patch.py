"""
bot_engine_market_scanner_patch.py
===================================
Integration patch for bot_engine.py and config.py.

WHAT THIS ADDS:
  1. Scheduled daily scan at 4:30 PM ET (30 min after market close)
  2. Results saved to reports/MM-DD-YYYY-market_scan.csv
  3. Top stocks/crypto written to watchlist/scanned_stocks.txt
     and watchlist/scanned_crypto.txt
  4. In-memory watchlists updated — scanned tickers prepended so
     signals try these first
  5. On bot reboot: temp files loaded before master watchlists
  6. Scanned tickers also added to ORB GO whitelist temporarily

APPLY THIS PATCH:
  Read each section below and splice into the corresponding file.
  Sections are clearly labeled.
"""

# =============================================================================
# SECTION A — config.py additions
# =============================================================================

CONFIG_PY_ADDITIONS = """
# ── Daily Market Scanner ─────────────────────────────────────────────────────
SCANNER_ENABLED         = True
SCANNER_TOP_N           = 10
SCANNER_RUN_TIME_ET     = "16:30"     # 4:30 PM ET = 1:30 PM PT
STOCK_PCT_OF_52W_HIGH   = 0.98
STOCK_VOL_SURGE_MIN     = 1.30
STOCK_HISTORY_DAYS      = "1y"
CRYPTO_RSI_MIN          = 55
CRYPTO_RSI_MAX          = 75
CRYPTO_VOL_SURGE_MIN    = 1.50
COINGECKO_API_KEY       = ""          # leave blank for free tier
COINGECKO_DELAY         = 2.5
COINGECKO_MAX_RETRIES   = 3
COINGECKO_BASE_WAIT     = 30
WIKIPEDIA_DELAY         = 3.0
SCANNER_REPORTS_DIR     = "reports"
SCANNER_WATCHLIST_DIR   = "watchlist"
TEMP_STOCKS_FILE        = "watchlist/scanned_stocks.txt"
TEMP_CRYPTO_FILE        = "watchlist/scanned_crypto.txt"
"""

# =============================================================================
# SECTION B — bot_engine.py imports (add to top of file)
# =============================================================================

BOT_ENGINE_IMPORTS = """
from market_scanner import (
    scan_stocks, scan_crypto, save_watchlist_temps,
    load_watchlist_temps, resolve_output_path, save_csv,
)
import config as cfg
"""

# =============================================================================
# SECTION C — BotEngine class methods (splice into BotEngine class)
# =============================================================================

BOT_ENGINE_METHODS = """
    def run_daily_market_scan(self):
        """Run the daily market scanner after market close.
        Saves CSV to reports/, updates temp watchlist files,
        and prepends results to in-memory watchlists.
        Scheduled at 4:30 PM ET (1:30 PM PT) weekdays.
        """
        if not cfg.SCANNER_ENABLED:
            return
        logger.info("Daily market scan starting...")
        try:
            stock_df  = scan_stocks(top_n=cfg.SCANNER_TOP_N)
            crypto_df = scan_crypto(top_n=cfg.SCANNER_TOP_N)
            output_path = resolve_output_path(None)
            save_csv(stock_df, crypto_df, output_path)
            logger.info(f"Market scan saved to {output_path}")
            save_watchlist_temps(stock_df, crypto_df)
            self._inject_scanned_symbols(stock_df, crypto_df)
            logger.info(f"Market scan complete: {len(stock_df)} stocks, {len(crypto_df)} crypto added to watchlists.")
        except Exception as e:
            logger.error(f"Daily market scan failed: {e}", exc_info=True)

    def _inject_scanned_symbols(self, stock_df, crypto_df):
        if not stock_df.empty:
            new_stocks = stock_df["Ticker"].tolist()
            existing = getattr(self, "stock_watchlist", [])
            self.stock_watchlist = new_stocks + [t for t in existing if t not in new_stocks]
            if hasattr(self, "orb_go_whitelist"):
                existing_orb = self.orb_go_whitelist
                self.orb_go_whitelist = new_stocks + [t for t in existing_orb if t not in new_stocks]
            logger.info(f"Injected {len(new_stocks)} scanned stocks into watchlist")
        if not crypto_df.empty:
            new_pairs = [f"{sym}/USD" for sym in crypto_df["Ticker"].tolist()]
            existing = getattr(self, "crypto_watchlist", [])
            self.crypto_watchlist = new_pairs + [p for p in existing if p not in new_pairs]
            logger.info(f"Injected {len(new_pairs)} scanned crypto pairs into watchlist")

    def load_scanned_watchlists_on_boot(self):
        scanned_stocks, scanned_crypto = load_watchlist_temps()
        if scanned_stocks:
            existing = getattr(self, "stock_watchlist", [])
            self.stock_watchlist = scanned_stocks + [t for t in existing if t not in scanned_stocks]
            logger.info(f"Boot: loaded {len(scanned_stocks)} scanned stocks from temp file")
        if scanned_crypto:
            existing = getattr(self, "crypto_watchlist", [])
            self.crypto_watchlist = scanned_crypto + [p for p in existing if p not in scanned_crypto]
            logger.info(f"Boot: loaded {len(scanned_crypto)} scanned crypto from temp file")
"""

# =============================================================================
# SECTION D — Scheduler entry (add alongside other scheduled jobs)
# =============================================================================

BOT_ENGINE_SCHEDULER = """
    self.scheduler.add_job(
        self.run_daily_market_scan,
        trigger="cron",
        day_of_week="mon-fri",
        hour=16,
        minute=30,
        timezone="America/New_York",
        id="daily_market_scan",
        name="Daily Market Scan",
        replace_existing=True,
    )
"""

# =============================================================================
# SECTION E — Bot startup call (add after watchlists initialized)
# =============================================================================

BOT_ENGINE_STARTUP = """
    self.load_scanned_watchlists_on_boot()
"""

# =============================================================================
# SECTION F — dashboard.py manual injection UI
# Add as a new expander in your Streamlit dashboard
# =============================================================================

DASHBOARD_MANUAL_INJECTION = """
with st.expander("\u2795 Inject Symbols (Temporary)", expanded=False):
    st.caption(
        "Add stocks or crypto to today's active watchlist. "
        "Temporary — resets on next market scan. To make permanent, edit master watchlist files."
    )
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Stocks")
        stock_input = st.text_area("Tickers (one per line or comma-separated)", height=100, key="manual_stock_input", placeholder="AAPL\\nMSFT\\nNVDA")
        if st.button("Inject Stocks", key="inject_stocks_btn"):
            tickers = [t.strip().upper() for t in stock_input.replace(",", "\\n").splitlines() if t.strip()]
            if tickers:
                temp_file = Path(cfg.TEMP_STOCKS_FILE)
                temp_file.parent.mkdir(parents=True, exist_ok=True)
                existing = [t for t in temp_file.read_text().splitlines() if t.strip() and t.strip() not in tickers] if temp_file.exists() else []
                temp_file.write_text("\\n".join(tickers + existing))
                if "bot" in st.session_state:
                    bot = st.session_state["bot"]
                    existing_live = getattr(bot, "stock_watchlist", [])
                    bot.stock_watchlist = tickers + [t for t in existing_live if t not in tickers]
                st.success(f"Injected {len(tickers)} stock(s): {', '.join(tickers)}")
            else:
                st.warning("No valid tickers entered.")
    with col2:
        st.subheader("Crypto")
        crypto_input = st.text_area("Symbols (e.g. BTC or BTC/USD)", height=100, key="manual_crypto_input", placeholder="BTC\\nETH\\nSOL")
        if st.button("Inject Crypto", key="inject_crypto_btn"):
            symbols = [s.strip().upper() for s in crypto_input.replace(",", "\\n").splitlines() if s.strip()]
            pairs = [s if "/" in s else f"{s}/USD" for s in symbols]
            if pairs:
                temp_file = Path(cfg.TEMP_CRYPTO_FILE)
                temp_file.parent.mkdir(parents=True, exist_ok=True)
                existing = [p for p in temp_file.read_text().splitlines() if p.strip() and p.strip() not in pairs] if temp_file.exists() else []
                temp_file.write_text("\\n".join(pairs + existing))
                if "bot" in st.session_state:
                    bot = st.session_state["bot"]
                    existing_live = getattr(bot, "crypto_watchlist", [])
                    bot.crypto_watchlist = pairs + [p for p in existing_live if p not in pairs]
                st.success(f"Injected {len(pairs)} crypto pair(s): {', '.join(pairs)}")
            else:
                st.warning("No valid symbols entered.")
    stocks_file = Path(cfg.TEMP_STOCKS_FILE)
    crypto_file = Path(cfg.TEMP_CRYPTO_FILE)
    if stocks_file.exists():
        content = stocks_file.read_text().strip()
        if content:
            st.info(f"\ud83d\udcc8 Active scanned stocks: {', '.join(content.splitlines())}")
    if crypto_file.exists():
        content = crypto_file.read_text().strip()
        if content:
            st.info(f"\ud83e\ude99 Active scanned crypto: {', '.join(content.splitlines())}")
"""
