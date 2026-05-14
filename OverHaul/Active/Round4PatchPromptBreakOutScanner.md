Patch BreakoutScanner.py.

Problem AlertSystem._build_candle_data() tries to enrich outgoing bot payloads with market context using BTC history, but it currently checks:

hasattr(self, "price_history")
self.price_history.get(...)
This is wrong because self is AlertSystem, and AlertSystem does not own price_history. The BTC price history lives inside BreakoutDetector:

scanner.detector.price_history
As a result, market_pct_change is never populated. RSI may be present, but BTC market context is always missing.

Required fix Wire AlertSystem to the detector history so _build_candle_data() can read BTC price history correctly.

Preferred implementation

Update AlertSystem.init to accept an optional detector reference: def init(self, config: ConfigManager, detector=None):

Store it: self.detector = detector

In MarketScanner.init, when constructing AlertSystem, pass the detector: self.alert_system = AlertSystem(self.config, detector=self.detector)

In AlertSystem._build_candle_data(), replace the broken BTC lookup logic:

remove hasattr(self, "price_history")
remove self.price_history.get(...)
Instead, read from: self.detector.price_history if self.detector exists

Use logic like

detector_history = getattr(self.detector, "price_history", {}) if self.detector else {}
then lookup: BTC/USD BTC-USD BTCUSDT
If BTC history has at least 2 points, compute: market_pct_change = ((latest - oldest) / oldest) * 100
Important

Do not change RSI logic.
Do not change sender call signature.
Do not change any bot payload field names.
Only fix detector wiring and BTC market context enrichment.
Why this matters Right now soft checks that rely on market context always SKIP. This does not block trading while MIN_SOFT_PASSES = 0, but it breaks payload quality and will matter if soft checks are re-enabled later.

Verify

python -m py_compile BreakoutScanner.py
Restart scanner
Confirm no runtime errors from AlertSystem init
Optionally log one outgoing candle_data payload and confirm market_pct_change appears when BTC history exists
Expected

_build_candle_data() can access BTC history correctly
market_pct_change is populated when BTC history is available
payload enrichment is improved without changing the rest of the pipeline
And yes — once you paste breakout_receiver.py, I can do the same style review/prompt for that too. After that we can look at adaptive_regime.py.