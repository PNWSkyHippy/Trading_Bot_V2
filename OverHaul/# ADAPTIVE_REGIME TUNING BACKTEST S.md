# ADAPTIVE_REGIME TUNING BACKTEST SPEC
**Goal:** Add granular reporting so adaptive_regime can be evaluated by mode, side, symbol class, and exit reason instead of only aggregate PnL.

## Current problem
adaptive_regime combines:
- trend mode
- mean reversion mode

Current backtest output aggregates everything together, hiding:
- which mode produced entries
- which mode wins/loses
- whether longs or shorts carry the edge
- whether exits are working as intended

## Required additions

### 1. Persist entry metadata into BacktestTrade
BacktestTrade should include optional fields:
- entry_mode              # "trend" or "mean_rev"
- regime                  # same as adaptive metadata if present
- entry_rsi
- entry_adx
- entry_atr
- entry_timeframe
- exit_reason             # already exists, keep using

Populate from signal.metadata when present.

### 2. Add mode breakdown to result report
For each backtest result, print:

#### By mode
- trend trades
- trend win rate
- trend total pnl
- trend avg pnl
- mean_rev trades
- mean_rev win rate
- mean_rev total pnl
- mean_rev avg pnl

#### By side
- long trades / WR / PF / PnL
- short trades / WR / PF / PnL

#### By exit reason
Count and PnL for:
- stop_loss
- take_profit
- adaptive_ema_cross_exit
- adaptive_bb_midline_exit
- adaptive_rsi_exit
- backtest_end

### 3. Add CSV export of every trade
Export one row per trade with:
- symbol
- strategy_name
- timeframe
- direction
- entry_date
- exit_date
- bars_held
- entry_price
- exit_price
- pnl
- pnl_pct
- fees
- exit_reason
- entry_mode
- regime
- entry_rsi
- entry_adx
- entry_atr

### 4. Add aggregate mode summary for run_all()
When running `--all --strategy adaptive_regime`, print an aggregate footer:

- total trend trades
- trend WR / PF / total pnl
- total mean_rev trades
- mean_rev WR / PF / total pnl
- total long trades
- total short trades
- best exit reason by expectancy
- worst exit reason by expectancy

### 5. Add minimum-sample warnings
If a symbol has:
- fewer than 10 trades total, or
- fewer than 5 trades in a mode

mark output:
`LOW SAMPLE — DO NOT TRUST`

### 6. Add median metrics
Current PF averages are distorted by 999 no-loss cases.
Add:
- median return %
- median profit factor
- median win rate
for run_all() summaries.

### 7. Fix stop mode label
Current report prints:
`Stop Mode: 2-Bar Trailing (N=bar)`
This is clearly formatting wrong.
Show actual lookback integer:
`Stop Mode: 2-Bar Trailing (N=2)`

## Nice-to-have
### 8. Add filters for mode-only runs
CLI flags:
- `--mode trend`
- `--mode mean_rev`
- `--side long`
- `--side short`

So we can test:
- trend-only longs
- trend-only shorts
- mean_rev-only longs
- mean_rev-only shorts

## Acceptance criteria
1. Every adaptive_regime trade can be classified by mode and side
2. Report shows trend vs mean_rev performance separately
3. Report shows long vs short performance separately
4. Report shows exit-reason distribution
5. CSV export supports manual review in Excel
6. Low-sample runs are explicitly labeled
7. Stop label shows actual N correctly