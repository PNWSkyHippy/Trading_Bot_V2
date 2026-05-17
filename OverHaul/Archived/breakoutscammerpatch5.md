Claude patch brief — breakoutscanner.py follow-up
Please make a surgical patch to BreakoutScanner.py.
Do not refactor unrelated code.
Do not change alert thresholds, scoring weights, or UI layout.
Fix only the issues below.

1) Preserve encryption of sensitive config keys on save
Current bug:

ConfigManager.load() decrypts sensitive values into memory
ConfigManager.save() dumps self.config directly
any later .set() call can write secrets back to scanner_config.json in plaintext
Required fix:

ensure sensitive keys remain encrypted when saving
never downgrade previously encrypted values to plaintext
safest acceptable solution:
add _encrypt_cfg()
re-encrypt sensitive keys on save if a Fernet key exists
if a value was originally encrypted and no Fernet key is available, preserve the original ciphertext instead of blanking or rewriting plaintext
goal: toggling harmless settings like enable_auto_trade must not expose API keys/passwords
2) Use signal.direction as the single source of truth everywhere downstream
Current bug:

several functions still infer long/short from momentum_score
this can break pattern-driven shorts and GUI labeling
Required fix:

after a BreakoutSignal is created, downstream code must use signal.direction and never re-derive direction from momentum
patch these locations:
classify_signal()
WatchlistManager.check()
ScannerGUI.add_alert()
use uppercase only for display, not for logic storage
logic should work off normalized lowercase "long" / "short"
3) Make short favorable-move tracking consistent end-to-end
Current bug:

escalation uses favorable_move_pct()
but watchlist promotion and GUI best-move tracking still use raw move for shorts
Required fix:

in WatchlistManager.check(), set:
sig.best_move_pct = favorable_move_pct(sig.direction, mpct)
in GUI storage, track favorable best move correctly for shorts
keep raw move_pct if you want for display, but favorable “best move” should always mean positive = good
fail/status coloring must use the true signal direction
4) Make crypto history/tracking exchange-aware
Current bug:

crypto mover may come from Coinbase, but history and tracking still use primary exchange only
Required fix:

allow CryptoDataFetcher.get_historical_data() to accept either:
an exchange instance, or
an exchange name
in _scan_cryptos(), fetch OHLCV history from the same exchange that produced the mover when possible
in update_signal_tracking(), use the tracked signal’s broker/exchange when available instead of always scanner.crypto_fetcher.exchange
if the original exchange is unavailable, fall back cleanly to primary exchange
5) Handle CoinGecko-injected crypto symbols more cleanly
Current bug:

CoinGecko price objects can be dropped in _scan_cryptos() because "COINGECKO" is not a CCXT exchange key
Required fix:

if broker is COINGECKO, allow fallback to a supported CCXT exchange for history only
do not skip the symbol solely because broker label is non-CCXT
only skip if no exchange can provide symbol history at all
6) Remove or delegate dead duplicate enrichment code
Current state:

enrichment now lives in BreakoutDetector._build_enrichment()
MarketScanner._build_signal_enrichment() appears unused duplicate code
Required fix:

either remove MarketScanner._build_signal_enrichment() if unused
or convert it into a thin wrapper that delegates to self.detector._build_enrichment(pd)
avoid maintaining two enrichment implementations
7) Fix local TradingEngine short-side execution
Current bug:

TradingEngine.execute_signal() always sends buy orders
Required fix:

for stock and crypto:
long → buy
short → sell / sell-short as appropriate for current broker abstraction
if broker does not support shorts, return a clear error rather than silently buying
Output requirements
After patching, provide:

a concise summary of each fix
exact functions changed
any behavior assumptions
confirmation that no scoring thresholds or alert escalation levels were changed
