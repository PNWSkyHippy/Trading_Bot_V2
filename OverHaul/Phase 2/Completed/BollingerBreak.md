	This one is the most live-evidence-backed strategy in the entire batch — for better or worse. The audit is refreshingly honest about real losses.

My read on Bollinger Breakout
Overall verdict: Watchlist — running under close monitoring, minimal code fixes needed
Issues I found
Critical — 1) Not registered
Same as every other strategy.

Critical — 2) Not in TIME_STOP_EXEMPT
Stock BB breakout with squeeze gate:

Squeeze means bands were tight before entry
Expansion after squeeze can be slow to develop
Generic 2h perf_time_stop at 24 bars on 5m = 2 hours
A 3% TP target after a genuine squeeze release can take more than 2 hours
Time stop likely killing developing trades.

Critical — 3) Missing metadata in both _make_signal() calls
Both long and short pass only:

return self._make_signal(
    symbol    = symbol,
    direction = "long",
    score     = score,
    reason    = "..."
)
No stop, no TP, no metadata dict. Executor falls back to defaults.

Critical — 4) verbose_log() with extra= called multiple places
self.verbose_log(
    symbol, "Bollinger Band squeeze ...",
    squeeze, band_width, f"<{squeeze_thr}",
    extra=f"upper={upper:.4f} lower={lower:.4f} mid={mid:.4f}"
)
And:

self.verbose_log(
    symbol, "OBV direction check",
    ...,
    extra=f"rising={obv_rising} falling={obv_falling}"
)
If extra= is not a valid parameter in verbose_log(), these throw TypeError on every signal evaluation. The strategy may be silently failing on most bars.

Important — 5) self.logger override
self.logger = logging.getLogger("BollingerBreakout")
Same issue as other strategies.

Important — 6) reviewer_exempt not set
Important — 7) stock_enabled not explicitly declared
crypto_enabled = False is set. But stock_enabled is not declared.

Depending on what BaseStrategy.__init__() defaults stock_enabled to, this strategy might not be recognized as stock-enabled by the engine.

Important — 8) candle_limit not set
EMA50 needs 50 bars, ADX 14, RSI 14, BB 20+. Need roughly 60+ bars minimum. If candle_limit defaults too low, signals might fire before indicators are well-initialized.

Important — 9) ml_exempt and auto_disable_exempt likely not real framework fields
Same issue as other strategies — but auto_disable_exempt in particular carries a safety meaning. If it silently does nothing, the risk it was created to protect against is real.

Important — 10) _bars_held injection needed
Same pattern.

Medium — 11) OBV check fires before the "shorts disabled" guard
Current order:

Calculate OBV (including for short direction)
Calculate EMA50
Calculate RSI
Check squeeze gate
Check ADX gate
Check for short signal
Check shorts_enabled
The return None for shorts_enabled is at the end. All the OBV/EMA/RSI computation runs even for short signals that will be discarded. Minor efficiency issue.

Minor — 12) getattr(self, "shorts_enabled", True) defensive but wrong default
if not getattr(self, "shorts_enabled", True):
If shorts_enabled attribute is somehow missing, this defaults to True, which would re-enable shorts unexpectedly. Should default to False:

if not getattr(self, "shorts_enabled", False):
What is genuinely good
Most honest audit documentation in the entire batch — real loss numbers, real WR data
Evidence-based decisions: shorts disabled, crypto disabled, squeeze as hard gate, ADX raised to 30
Live data-driven: not just backtest theory
Blacklists are real — based on actual loss patterns
The auto_disable_exempt concept is the right idea even if implementation uncertain
Squeeze gate moved from score bonus to hard gate based on 72-combo sweep — correct
ADX moved to config-driven — correct
Claude patch prompt
Patch strategies/bollinger_breakout.py and register it in the bot framework.

This strategy is currently running live in stocks-only long-only mode
with ADX≥30 + squeeze as hard gates following a live loss audit.
Do NOT change any entry logic, filters, blacklists, or disable flags.
Fixes are purely integration wiring and metadata completeness.

Files to inspect and patch:
- strategies/bollinger_breakout.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- strategies/base_strategy.py
  (inspect: reviewer_exempt, ml_exempt, auto_disable_exempt, stock_enabled,
   verbose_log signature)

========================================================
REQUIRED FIXES — IN PRIORITY ORDER
========================================================

1) Register in backtester.py strategy_map
Add if not already present:
    "bollinger_breakout": ("strategies.bollinger_breakout", "BollingerBreakout"),

2) Register in strategy_engine.py
Add if not already present:
    from strategies.bollinger_breakout import BollingerBreakout
    BollingerBreakout(),

3) Add bollinger_breakout to TIME_STOP_EXEMPT in backtester.py
Squeeze + ADX30 BB breakout needs time to develop.
2h generic perf_time_stop can kill developing post-squeeze expansions.
Add:
    "bollinger_breakout",

4) Confirm _bars_held injection before check_custom_exit()
Standard injection pattern — confirm it applies here.

5) CRITICAL: Fix verbose_log() extra= parameter calls
Multiple calls in analyze() use extra= which may not be a valid parameter.
Check base_strategy.py verbose_log() signature.

Affected lines:
    self.verbose_log(symbol, "Bollinger Band squeeze ...", squeeze, band_width,
                     f"<{squeeze_thr}", extra=f"upper=...")
    self.verbose_log(symbol, "OBV direction check", ..., extra=f"rising=...")

If extra= is not a valid parameter:
- Remove extra= from all calls
- Inline the extra info into the value string instead:
    self.verbose_log(
        symbol, "Bollinger Band squeeze ...",
        squeeze,
        f"{band_width:.4f} [up={upper:.4f} lo={lower:.4f} mid={mid:.4f}]",
        f"<{squeeze_thr}",
    )
    self.verbose_log(
        symbol, "OBV direction check",
        obv_rising or obv_falling,
        f"now={round(obv_now,0)} prev={round(obv_prev,0)} "
        f"rising={obv_rising} falling={obv_falling}",
        "check",
    )

6) Add metadata to both _make_signal() calls
Both long and short signals pass no metadata.

For long signal:
    return self._make_signal(
        symbol          = symbol,
        direction       = "long",
        score           = score,
        reason          = "...",
        stop_loss_pct   = config.DEFAULT_STOP_LOSS_PCT,
        take_profit_pct = config.DEFAULT_TAKE_PROFIT_PCT,
        metadata        = {
            "strategy_name":               "bollinger_breakout",
            "bb_upper":                    round(float(upper), 4),
            "bb_lower":                    round(float(lower), 4),
            "bb_mid":                      round(float(mid), 4),
            "band_width":                  round(float(band_width), 4),
            "squeeze":                     bool(squeeze),
            "adx":                         round(adx_val, 2) if adx_val else None,
            "rsi":                         round(float(rsi_now), 2),
            "obv_rising":                  bool(obv_rising),
            "ema50":                       round(float(ema50_val), 4),
            "volume_ratio":                vol_ratio,   # compute below
            "preferred_initial_stop_mode": "percent",
            "preferred_trail_mode":        "percent",
        }
    )

Also compute volume_ratio before the signal blocks:
    vol_series = candles["volume"]
    vol_ma = vol_series.rolling(20).mean().iloc[-1]
    vol_ratio = round(float(vol_series.iloc[-1] / vol_ma), 3) if vol_ma > 0 else None

For short signal, same metadata pattern with appropriate field values.

7) Fix self.logger override
Inspect base_strategy.py for self.logger usage.
Either:
A. Remove: self.logger = logging.getLogger("BollingerBreakout")
B. Rename to self._bb_log and update all self.logger. calls in this file

8) Add missing framework flags to __init__
Add:
    self.stock_enabled   = True          # explicitly declare (crypto is already False)
    self.candle_limit    = 60            # need EMA50 + ADX14 + BB20 + buffer
    self.reviewer_exempt = True
    self.time_stop_profile = "strategy_defined"

9) Fix auto_disable_exempt and ml_exempt flags
Inspect base_strategy.py.

If auto_disable_exempt is NOT a recognized framework attribute:
- Do NOT remove it silently — it exists to protect against a real risk
- Add a comment explaining what it's supposed to do:
    # auto_disable_exempt = True
    # INTENT: prevents bot from auto-disabling based on pre-2026-05-16 WR data
    # (22% WR from old config — new config is ADX30+squeeze, zero trades yet)
    # RISK: if this flag does nothing, the bot may auto-disable on first trade
    # TODO: add this flag to base_strategy.py with auto_disable logic support
    self.auto_disable_exempt = True

If auto_disable_exempt IS a recognized framework attribute:
- Keep it as is
- Add the same comment for clarity

If ml_exempt is NOT a recognized framework attribute:
- Remove it

10) Fix shorts_enabled default fallback
Current:
    if not getattr(self, "shorts_enabled", True):

If `shorts_enabled` is missing, defaults to True — would re-enable shorts unexpectedly.
Change to:
    if not getattr(self, "shorts_enabled", False):

11) Minor: Move OBV/EMA/RSI computation to after the short-disabled guard
Current flow computes OBV, EMA50, RSI before checking shorts_enabled.
If shorts are disabled and no long breakout fires, this computation is wasted.

Reorder to check long_breakout first, then only compute confirmations for it.
This is optimization only — do not change if it creates any risk of logic change.
Only apply if the reorder is clearly safe.

========================================================
DO NOT CHANGE
========================================================

- Any entry logic, filters, or thresholds
- Squeeze hard gate (must remain a hard gate, not score bonus)
- ADX threshold (must remain config-driven at bb_adx_min=30)
- Shorts disabled (shorts_enabled=False must remain)
- Crypto disabled (crypto_enabled=False must remain)
- BOLLINGER_BLACKLIST or BOLLINGER_CRYPTO_BLACKLIST
- auto_disable_exempt = True (see item 9 above)
- OBV + EMA50 + RSI direction filters
- All blacklist comments and audit documentation

========================================================
VALIDATION
========================================================

Compile:
python -m py_compile strategies/bollinger_breakout.py

Run stock basket with new config:
python intelligence/backtester.py --all \
    --strategy bollinger_breakout --days 30 --tf 5m \
    --asset-class stock \
    --initial-stop signal_structural --trail-stop none

This is especially important because the audit identified:
- 47.5% stop-loss hit rate pre-audit config
- ADX30+squeeze sweep showed PF 1.28 vs PF 1.07 for ADX20 no-squeeze

After the patch, check:
1. Trade count — ADX30+squeeze should produce ~30-40% fewer signals than before
2. Exit reasons — generic lifecycle stops should NOT dominate
   (if hard_time_stop appears often, TIME_STOP_EXEMPT was not applied)
3. WR target — goal is >=35% on new config
4. Verify no shorts fire (shorts_enabled=False)
5. Verify no crypto trades if run with --asset-class crypto

Compare vs audit baseline:
Pre-audit live: 22.2% WR, -$135/day on stocks
Post-patch target: >=35% WR on new ADX30+squeeze config

Check metadata presence:
In logs, verify metadata fields appear for long signals:
- bb_upper, bb_lower, band_width, squeeze, adx, rsi, obv_rising

Deliverables:
1. Patched strategy file
2. Patched backtester.py (TIME_STOP_EXEMPT + registration)
3. Patched strategy_engine.py
4. Confirmation verbose_log extra= issue resolved
5. Confirmation auto_disable_exempt handling documented
6. Stock basket results under new config
7. Trade count comparison (should be fewer with ADX30+squeeze)
8. WR check against 35% target
9. Final classification: Disabled / Watchlist / Incubate
My pre-patch classification
Concept: BB breakout — has a fundamental false-breakout problem; squeeze gate and ADX30 are the attempted fix
Code quality: decent with heavy documentation
Implementation completeness: 70% — metadata and framework flags are the gaps
Evidence base: best in the batch for live data — real losses, real WR, real trade count
Salvageable: possibly — the audit changes (squeeze hard gate + ADX30) haven't been validated yet on the new config
Watchlist — this one stays in watchlist until the new ADX30+squeeze config accumulates 50 real trades.

The most important thing about this strategy is that the audit is excellent documentation — you know exactly:

What was wrong: 47.5% stop hits, 2.1% WR on stops = false breakout factory
What was done: squeeze hard gate, ADX30, shorts disabled, crypto disabled
What needs to happen: 50 live trades to validate new config before deciding keep/kill
The code quality of the audit trail is better than the code quality of the strategy itself.