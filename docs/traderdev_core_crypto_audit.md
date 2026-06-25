# TraderDev Core Crypto Strategy Audit

Date: 2026-06-17

Goal: stop judging TraderDev/Pine strategies as if they are universal 150-symbol scanners. Test them in the lane they were designed for: mostly BTC/ETH/SOL/BNB crypto, usually 1h, then only promote `strategy + symbol + timeframe + side` combinations that survive local Python backtesting.

## Working Rule

A strategy is not approved globally. Approval is per lane:

```text
strategy_name + symbol + timeframe + direction
```

Example:

```text
btc_v6_chandelier + BTC/USD + 1h + long
```

## First Local Matrix

Command:

```powershell
.\Scripts\run_traderdev_core_matrix.ps1
```

Universe:

```text
BTC/USD, ETH/USD, SOL/USD, BNB/USD
```

Settings:

```text
timeframe: 1h
days: 365
directions: long, short, both
min trades: 2
```

## First Results

### btc_v6_chandelier

Report:

```text
reports\strategy_matrix\btc_v6_chandelier_20260617_074109_traderdev_core.txt
```

Result:

```text
Overall avg PF: 2.407
Edge cells: 6 / 8
Best lanes:
SOL/USD 1h long PF 3.210, WR 60.0%, 5 trades
BTC/USD 1h long PF 2.590, WR 50.0%, 6 trades
BNB/USD 1h long PF 1.420, WR 42.9%, 7 trades
ETH/USD failed in this run
```

Verdict: immediate paper-forward candidate, but sample size is small. Promote only BTC/SOL/BNB long lanes, not ETH and not shorts.

### rsi_dip_simple

Report:

```text
reports\strategy_matrix\rsi_dip_simple_20260617_074114_traderdev_core.txt
```

Result:

```text
Overall avg PF: 0.340
No edge cells
```

Verdict: reject for now.

### bollinger_squeeze

Result: 0 trades in this matrix, despite historical notes saying TraderDev found ETH/BNB/BTC edge.

Verdict: do not reject yet. Diagnose data/timeframe/port parity, because zero trades may mean the local port/backtester is not matching the original Pine assumptions.

### pll_cycle / pll_cycle_martingale

Result: 0 trades in this matrix.

Verdict: do not reject yet. Diagnose port parity and signal generation. Martingale variant also logs that live size-scaling is disabled because loss-streak state is not wired.

## Next Work

1. Find or add the TraderDev API/client configuration. No obvious `TRADERDEV` key or endpoint was found in `.env`, `config.py`, or current environment variables during this pass.
2. Pull six high-ranking Pine scripts that explicitly target BTC/ETH/SOL/BNB, preferably 1h/15m, with stated commission/slippage assumptions.
3. For each script:
   - save original Pine under `pine_scripts/traderdev/`;
   - save source metadata and claimed metrics;
   - port faithfully to `strategies/`;
   - wire into `strategy_matrix.py` and `intelligence/backtester.py`;
   - run BTC/ETH/SOL/BNB-only matrix;
   - accept only lanes that survive local tests with realistic fees.
4. Add approved lanes to a per-strategy symbol allowlist before live/paper production.

## TraderDev Candidate Port Pass - 2026-06-17

Source Pine saved under:

```text
pine_scripts/traderdev/
```

Candidates pulled from TraderDev:

```text
PLL Conservative ETH 1h - gauntlet
  id: 01KV16XFDKWR558RGDE7582GHS
  claim lane: ETHUSDT 1h

Day Trader v3 - SOL 15m
  id: 01KRVN3V3A9GD9Y2RF7N3D91X4
  claim lane: SOLUSDT 15m

Day Trader v3 - BTC 15m Momentum
  id: 01KRVN39G3ZEYNCVG82C6AK7GY
  claim lane: BTCUSDT 15m

GridBot Iter1 ADX15
  id: 01KRRE871SPHJH4FCK82TWMVQ5
  claim lane: BTCUSDT 1h
```

Local Python ports added:

```text
pll_conservative_eth_1h
td_day_trader_v3
td_gridbot_adx15
```

Important backtester fix from this pass:

```text
intelligence/backtester.py now rejects short candle-store hits for long
matrix requests. Before this fix, a 365d request could accept a 300-bar
live-cache slice, causing false zero-trade results on warmup-heavy strategies.
```

Fresh local matrix results:

```text
reports/strategy_matrix/pll_conservative_eth_1h_20260617_112752_traderdev_port_fresh.txt
reports/strategy_matrix/td_day_trader_v3_20260617_112801_traderdev_port_fresh.txt
reports/strategy_matrix/td_gridbot_adx15_20260617_113343_traderdev_port_fresh.txt
```

Summary:

```text
pll_conservative_eth_1h:
  Overall avg PF 0.392.
  Only one edge cell: BNB/USD 1h long PF 1.28, WR 41%, 22 trades.
  ETH/BTC/SOL failed locally. Verdict: watchlist only; do not paper-forward.

td_day_trader_v3:
  Overall avg PF 0.148.
  No edge cells. BTC/SOL claimed lanes failed locally.
  Note: local port uses a single weighted 2.8R target because the current
  backtester does not model Pine's 60% partial at 2R plus 40% at 4R/trailing.
  Verdict: reject as currently ported; only revisit with partial-exit parity.

td_gridbot_adx15:
  Overall avg PF 0.153.
  No edge cells. Shorts were especially weak.
  Verdict: reject as a TraderDev parity lane. Existing local GridBot should
  remain governed by its separate audit path and local modifications.
```

Additional TraderDev search note:

```text
Strict and relaxed 5m searches on BTCUSDT, ETHUSDT, SOLUSDT, and BNBUSDT
found no profitable high-sample candidates with at least 150 trades and
drawdown under 30%.
```

BTC PLL family follow-up:

```text
The BTC PLL family is not one identical strategy. Source fetch confirmed:

PLL Cycle Trader - BTC 1h
  id: 01KRDMZ0JYF2NRV1HH7JD6XV53
  no lockQ gate; center=96, detrend=200, loopBW=0.04, lpfAlpha=0.15,
  SL=4%, TP=12%, 50% equity sizing in Pine.
  TraderDev claim: PF 1.126, WR 44.1%, 331 trades, max DD 30.6%.
  Verdict: not strong enough to port/promote.

PLL Cycle Trader - lockQ + Vol Filter
  id: r_ea53ea3512425d153ef64a89a58b2e
  minLockQ=0.5, volRel < 1.5, same 4%/12% bracket, optional shorts.
  TraderDev claim: PF 1.147, WR 45.0%, 189 trades, max DD 18.0%.
  Verdict: mildly interesting but below promotion threshold.

PLL inv p96 lock1.2 BTC variants
  ids: 01KSKCJF30V5AQ6K20GJ5Z0ENH, 01KSQ5Y4VT63R6NS7KQFT4A55D
  strict lockQ > 1.2, same p96/200/0.04/0.15 and 4%/12%.
  TraderDev claims were weak to negative on BTC.
  Verdict: do not chase unless optimizing a new PLL fork.
```

## TraderDev Exact-Lane Candidate Pass 2 - 2026-06-17

Source Pine saved under:

```text
pine_scripts/traderdev/
```

Additional candidates pulled from TraderDev:

```text
BTC V11 final - bearPersist=120 atrL=4 atrS=2.5
  id: 01KRPF8NGFTDSHCA04701SN1TD
  claim lane: BTCUSDT 1h
  TraderDev claim: PF 2.187, WR 40.4%, 151 trades, max DD 18.1%.

F40D-ADX ETH 1H - fork 2026-06-08
  id: 01KTK46MR1W21EQM0YMFJ945S3
  claim lane: ETHUSDT 1h
  TraderDev claim: PF 2.108, WR 26.0%, 223 trades, max DD 12.9%.

RSI Dip & Spike v4c
  id: 01KSKAX5M4F2CDT1GGGHB9EHRA
  claim lane: SOLUSDT 1h
  TraderDev claim: PF 2.273, WR 75.9%, 112 trades, max DD 1.6%.

V6 BNB F19 + ADX-magnitude sizing (F31)
  id: 01KRC22M0NW4BWK61MA6T3G37S
  claim lane: BNBUSDT 1h
  TraderDev claim: PF 1.682, WR 43.7%, 190 trades, max DD 19.7%.
```

Local Python ports added:

```text
td_btc_v11
td_f40d_adx
td_rsi_dip_spike_v4c
td_v6_bnb_adx
```

Important porting note:

```text
TraderDev BTC V11, ETH F40D, and BNB V6 use dynamic cash sizing and/or
streak sizing in Pine. The local ports intentionally preserve signal and exit
logic only. Position sizing remains under the bot risk manager.
```

Fresh local matrix reports:

```text
reports/strategy_matrix/td_rsi_dip_spike_v4c_20260617_172155_traderdev_lane_fresh.txt
reports/strategy_matrix/td_v6_bnb_adx_20260617_172143_traderdev_lane_fresh.txt
reports/strategy_matrix/td_btc_v11_20260617_172457_traderdev_lane_fresh.txt
reports/strategy_matrix/td_f40d_adx_20260617_172455_traderdev_lane_fresh.txt
```

Summary:

```text
td_rsi_dip_spike_v4c:
  Overall avg PF 0.361.
  SOL/USD 1h long was best but only PF 0.76 with 46 trades.
  No edge cells. Verdict: reject locally despite strong TraderDev SOL claim.

td_v6_bnb_adx:
  Overall avg PF 0.720.
  BNB/USD 1h long/both PF 1.14 with 63 trades.
  Borderline watchlist only; below the PF >= 1.25 paper-forward gate.

td_btc_v11:
  Overall avg PF 0.723.
  BTC/USD intended lane failed locally: both PF 0.74 with 62 trades.
  BNB/USD was best at PF 1.11, still below gate.
  Verdict: reject for BTC; optional BNB watchlist only.

td_f40d_adx:
  Overall avg PF 0.649.
  ETH/USD intended lane failed locally: both PF 0.76 with 112 trades.
  No edge cells. Verdict: reject locally.
```

Decision:

```text
Do not enable any of these four ports in live/paper production yet.
The TraderDev headline edge did not survive the local data/execution model.
The only mildly interesting residue is BNB/USD 1h on td_v6_bnb_adx or
td_btc_v11, but both are below the promotion threshold.
```

## Promotion Criteria

Minimum for paper-forward:

```text
PF >= 1.2
at least 5 trades in 365d, preferably more
not dependent on one lucky outlier
strategy source assumptions match local backtest assumptions
no live-impossible lookahead/repaint behavior
```

Strong candidate:

```text
PF >= 1.5
WR >= 50% OR average win meaningfully larger than average loss
drawdown acceptable
fees/slippage included
stable across BTC/SOL/BNB or extremely strong on one intended symbol
```
