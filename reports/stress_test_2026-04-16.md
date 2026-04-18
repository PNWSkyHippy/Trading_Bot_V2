# Full Adversarial Strategy Stress Test

**Date:** 2026-04-16 21:25  
**Framework:** Backtest Expert 5-Dimension (0-100)  
**Capital:** $10,000 per symbol  
**Slippage base:** 0.05% per side (0.10% round-trip)  

---

## Mean Reversion

> Fades extreme z-score deviations back to mean  
> Timeframe: `1h` | Parameters: 3

### Score: **37/100 — Abandon**

| Dimension | Score | Max |
|-----------|------:|----:|
| Sample Size     | 20 | 20 |
| Expectancy      | 0 | 20 |
| Risk Management | 12 | 20 |
| Robustness      | 5 | 20 |
| Exec Realism    | 0 | 20 |

*Note: Exec Realism = 0 until slippage stress confirms edge survives friction.*

### Baseline Portfolio (15 symbols, 1990 trades)

| Metric | Value |
|--------|-------|
| Win Rate | 37.3% |
| Avg Win | 3.596% |
| Avg Loss | 2.169% |
| Profit Factor | 0.999 |
| Expectancy | -0.0187%/trade |
| Avg Max Drawdown | 0.709% |
| Avg Sharpe | -0.42 |
| Avg Return | 0.097% |

#### Per-Symbol Results

| Symbol | Trades | Win Rate | PF | Sharpe | Return |
|--------|--------|----------|----|--------|--------|
| NVDA | 149 | 44.3% | 1.373 | 5.74 | 1.385% |
| PLTR | 166 | 42.8% | 1.234 | 3.76 | 1.06% |
| MRVL | 154 | 38.3% | 1.181 | 2.71 | 0.774% |
| AMZN | 128 | 40.6% | 1.145 | 2.31 | 0.474% |
| INTC | 154 | 39.6% | 1.067 | 1.14 | 0.308% |
| AMD | 160 | 35.6% | 1.065 | 0.99 | 0.292% |
| META | 120 | 35.8% | 1.02 | 0.34 | 0.062% |
| TSLA | 152 | 39.5% | 0.97 | -0.54 | -0.15% |
| AAPL | 102 | 35.3% | 0.95 | -0.92 | -0.123% |
| GOOGL | 118 | 35.6% | 0.915 | -1.65 | -0.266% |
| NOW | 133 | 36.8% | 0.902 | -1.79 | -0.358% |
| AVGO | 153 | 37.3% | 0.897 | -1.93 | -0.44% |
| NET | 153 | 35.9% | 0.875 | -2.37 | -0.611% |
| QQQ | 85 | 34.1% | 0.817 | -3.82 | -0.36% |
| SPY | 63 | 28.6% | 0.579 | -10.23 | -0.597% |

### Slippage Stress Test

| Scenario | Adj Win | Adj Loss | Profit Factor | Expectancy | Survives |
|----------|---------|----------|---------------|------------|---------|
| No slippage (current) | 3.596% | 2.169% | 0.986 | -0.0187% | ❌ |
| 1x realistic (~0.10% RT) | 3.496% | 2.269% | 0.917 | -0.1187% | ❌ |
| 1.5x conservative | 3.446% | 2.319% | 0.884 | -0.1687% | ❌ |
| 2x stress test | 3.396% | 2.369% | 0.853 | -0.2187% | ❌ |
| 3x worst case | 3.296% | 2.469% | 0.794 | -0.3187% | ❌ |

### Parameter Sensitivity (Plateau vs Spike)

*Robust = PF range < 0.30 across values (plateau). Fragile = PF collapses outside narrow range (spike).*

| Parameter | Value | Trades | Win Rate | PF | Sharpe |
|-----------|-------|--------|----------|----|--------|
| **mean_rev_zscore_entry** (⚠️  SPIKE, range=0.54) | | | | | |
| | 1.5 | 152 | 32.9% | 0.865 | -2.62 |
| | 1.75 | 133 | 39.1% | 1.262 | 4.18 |
| | 2.0 | 102 | 35.3% | 0.95 | -0.92 |
| | 2.25 | 86 | 30.2% | 0.718 | -5.9 |
| | 2.5 | 58 | 37.9% | 1.173 | 2.88 |
| **mean_rev_period** (⚠️  SPIKE, range=0.36) | | | | | |
| | 15 | 101 | 43.6% | 1.311 | 4.91 |
| | 20 | 102 | 35.3% | 0.95 | -0.92 |
| | 25 | 113 | 35.4% | 1.019 | 0.34 |
| | 30 | 103 | 35.9% | 0.986 | -0.25 |

---

## Bollinger Breakout

> Breaks outside BB bands — Run C params (sq=0.04, ms=0.70)  
> Timeframe: `5m` | Parameters: 4

### Score: **44/100 — Refine**

| Dimension | Score | Max |
|-----------|------:|----:|
| Sample Size     | 20 | 20 |
| Expectancy      | 7 | 20 |
| Risk Management | 12 | 20 |
| Robustness      | 5 | 20 |
| Exec Realism    | 0 | 20 |

*Note: Exec Realism = 0 until slippage stress confirms edge survives friction.*

### Baseline Portfolio (15 symbols, 354 trades)

| Metric | Value |
|--------|-------|
| Win Rate | 44.3% |
| Avg Win | 2.763% |
| Avg Loss | 1.781% |
| Profit Factor | 1.38 |
| Expectancy | 0.232%/trade |
| Avg Max Drawdown | 0.197% |
| Avg Sharpe | 9.58 |
| Avg Return | 0.14% |

#### Per-Symbol Results

| Symbol | Trades | Win Rate | PF | Sharpe | Return |
|--------|--------|----------|----|--------|--------|
| TSLA | 20 | 60.0% | 3.096 | 70.49 | 0.468% |
| INTC | 32 | 50.0% | 2.175 | 45.58 | 0.54% |
| META | 18 | 61.1% | 2.15 | 45.73 | 0.331% |
| AVGO | 20 | 45.0% | 1.782 | 30.8 | 0.28% |
| GOOGL | 14 | 42.9% | 1.711 | 31.96 | 0.171% |
| NOW | 30 | 43.3% | 1.545 | 27.33 | 0.326% |
| MRVL | 34 | 50.0% | 1.169 | 8.76 | 0.133% |
| ALAB | 40 | 42.5% | 1.157 | 8.85 | 0.137% |
| AMD | 25 | 52.0% | 1.086 | 4.63 | 0.045% |
| NVDA | 17 | 35.3% | 1.076 | 4.55 | 0.024% |
| NET | 40 | 37.5% | 1.021 | 1.27 | 0.017% |
| SPY | 7 | 57.1% | 0.945 | -3.1 | -0.008% |
| PLTR | 30 | 36.7% | 0.908 | -6.03 | -0.063% |
| AMZN | 19 | 26.3% | 0.712 | -19.98 | -0.13% |
| AAPL | 8 | 25.0% | 0.173 | -107.07 | -0.17% |

### Slippage Stress Test

| Scenario | Adj Win | Adj Loss | Profit Factor | Expectancy | Survives |
|----------|---------|----------|---------------|------------|---------|
| No slippage (current) | 2.763% | 1.781% | 1.234 | 0.232% | ✅ |
| 1x realistic (~0.10% RT) | 2.663% | 1.881% | 1.126 | 0.132% | ✅ |
| 1.5x conservative | 2.613% | 1.931% | 1.076 | 0.082% | ✅ |
| 2x stress test | 2.563% | 1.981% | 1.029 | 0.032% | ✅ |
| 3x worst case | 2.463% | 2.081% | 0.941 | -0.068% | ❌ |

### Parameter Sensitivity (Plateau vs Spike)

*Robust = PF range < 0.30 across values (plateau). Fragile = PF collapses outside narrow range (spike).*

| Parameter | Value | Trades | Win Rate | PF | Sharpe |
|-----------|-------|--------|----------|----|--------|
| **bb_breakout_std** (✅ PLATEAU, range=0.00) | | | | | |
| | 1.75 | 8 | 25.0% | 0.173 | -107.07 |
| | 2.0 | 8 | 25.0% | 0.173 | -107.07 |
| | 2.25 | 8 | 25.0% | 0.173 | -107.07 |
| | 2.5 | 8 | 25.0% | 0.173 | -107.07 |
| **bb_squeeze_threshold** (✅ PLATEAU, range=0.00) | | | | | |
| | 0.03 | 8 | 25.0% | 0.173 | -107.07 |
| | 0.04 | 8 | 25.0% | 0.173 | -107.07 |
| | 0.05 | 8 | 25.0% | 0.173 | -107.07 |
| | 0.06 | 8 | 25.0% | 0.173 | -107.07 |
| **bb_breakout_min_score** (✅ PLATEAU, range=0.00) | | | | | |
| | 0.6 | 8 | 25.0% | 0.173 | -107.07 |
| | 0.65 | 8 | 25.0% | 0.173 | -107.07 |
| | 0.7 | 8 | 25.0% | 0.173 | -107.07 |
| | 0.75 | 8 | 25.0% | 0.173 | -107.07 |

---

## Ema Crossover

> Fast(9)/Slow(21) EMA cross with EMA50 trend filter  
> Timeframe: `1h` | Parameters: 4

### Score: **42/100 — Refine**

| Dimension | Score | Max |
|-----------|------:|----:|
| Sample Size     | 20 | 20 |
| Expectancy      | 5 | 20 |
| Risk Management | 12 | 20 |
| Robustness      | 5 | 20 |
| Exec Realism    | 0 | 20 |

*Note: Exec Realism = 0 until slippage stress confirms edge survives friction.*

### Baseline Portfolio (15 symbols, 1370 trades)

| Metric | Value |
|--------|-------|
| Win Rate | 38.4% |
| Avg Win | 3.663% |
| Avg Loss | 2.217% |
| Profit Factor | 1.049 |
| Expectancy | 0.0409%/trade |
| Avg Max Drawdown | 0.604% |
| Avg Sharpe | 0.52 |
| Avg Return | 0.152% |

#### Per-Symbol Results

| Symbol | Trades | Win Rate | PF | Sharpe | Return |
|--------|--------|----------|----|--------|--------|
| NVDA | 107 | 44.9% | 1.604 | 8.48 | 1.428% |
| AVGO | 105 | 44.8% | 1.419 | 6.47 | 1.066% |
| AMD | 97 | 40.2% | 1.128 | 2.18 | 0.353% |
| NOW | 84 | 42.9% | 1.111 | 1.83 | 0.276% |
| INTC | 109 | 37.6% | 1.093 | 1.49 | 0.302% |
| TSLA | 119 | 42.0% | 1.087 | 1.47 | 0.29% |
| NET | 106 | 42.5% | 1.037 | 0.66 | 0.107% |
| MRVL | 116 | 37.9% | 1.002 | 0.04 | 0.005% |
| QQQ | 55 | 34.5% | 0.997 | -0.05 | -0.004% |
| PLTR | 117 | 35.0% | 0.99 | -0.18 | -0.041% |
| GOOGL | 74 | 37.8% | 0.931 | -1.29 | -0.139% |
| SPY | 41 | 31.7% | 0.918 | -1.62 | -0.076% |
| AMZN | 84 | 35.7% | 0.858 | -2.6 | -0.334% |
| META | 80 | 35.0% | 0.823 | -3.53 | -0.442% |
| AAPL | 76 | 34.2% | 0.742 | -5.54 | -0.513% |

### Slippage Stress Test

| Scenario | Adj Win | Adj Loss | Profit Factor | Expectancy | Survives |
|----------|---------|----------|---------------|------------|---------|
| No slippage (current) | 3.663% | 2.217% | 1.03 | 0.0409% | ✅ |
| 1x realistic (~0.10% RT) | 3.563% | 2.317% | 0.959 | -0.0591% | ❌ |
| 1.5x conservative | 3.513% | 2.367% | 0.925 | -0.1091% | ❌ |
| 2x stress test | 3.463% | 2.417% | 0.893 | -0.1591% | ❌ |
| 3x worst case | 3.363% | 2.517% | 0.833 | -0.2591% | ❌ |

### Parameter Sensitivity (Plateau vs Spike)

*Robust = PF range < 0.30 across values (plateau). Fragile = PF collapses outside narrow range (spike).*

| Parameter | Value | Trades | Win Rate | PF | Sharpe |
|-----------|-------|--------|----------|----|--------|
| **ema_fast_period** (✅ PLATEAU, range=0.29) | | | | | |
| | 7 | 80 | 37.5% | 1.037 | 0.69 |
| | 9 | 76 | 34.2% | 0.742 | -5.54 |
| | 12 | 71 | 33.8% | 0.755 | -5.09 |
| | 14 | 70 | 38.6% | 0.908 | -1.77 |
| **ema_slow_period** (⚠️  SPIKE, range=0.36) | | | | | |
| | 18 | 80 | 37.5% | 0.974 | -0.49 |
| | 21 | 76 | 34.2% | 0.742 | -5.54 |
| | 26 | 71 | 35.2% | 0.786 | -4.43 |
| | 30 | 66 | 40.9% | 1.098 | 1.74 |
| **ema_trend_period** (✅ PLATEAU, range=0.00) | | | | | |
| | 40 | 76 | 34.2% | 0.742 | -5.54 |
| | 50 | 76 | 34.2% | 0.742 | -5.54 |
| | 60 | 76 | 34.2% | 0.742 | -5.54 |

---

## Scalp Master

> RSI(7) reversal with volume spike — 8 symbol whitelist  
> Timeframe: `5m` | Parameters: 3

### Score: **44/100 — Refine**

| Dimension | Score | Max |
|-----------|------:|----:|
| Sample Size     | 17 | 20 |
| Expectancy      | 8 | 20 |
| Risk Management | 14 | 20 |
| Robustness      | 5 | 20 |
| Exec Realism    | 0 | 20 |

*Note: Exec Realism = 0 until slippage stress confirms edge survives friction.*

### Baseline Portfolio (6 symbols, 147 trades)

| Metric | Value |
|--------|-------|
| Win Rate | 41.3% |
| Avg Win | 2.063% |
| Avg Loss | 0.907% |
| Profit Factor | 1.857 |
| Expectancy | 0.3196%/trade |
| Avg Max Drawdown | 0.131% |
| Avg Sharpe | 27.29 |
| Avg Return | 0.134% |

#### Per-Symbol Results

| Symbol | Trades | Win Rate | PF | Sharpe | Return |
|--------|--------|----------|----|--------|--------|
| GOOGL | 18 | 38.9% | 3.1 | 54.63 | 0.222% |
| AMZN | 19 | 52.6% | 3.03 | 65.6 | 0.264% |
| PLTR | 28 | 46.4% | 1.757 | 31.76 | 0.255% |
| META | 18 | 44.4% | 1.29 | 15.1 | 0.069% |
| IREN | 34 | 32.4% | 1.098 | 4.8 | 0.043% |
| ALAB | 30 | 33.3% | 0.868 | -8.16 | -0.051% |

### Slippage Stress Test

| Scenario | Adj Win | Adj Loss | Profit Factor | Expectancy | Survives |
|----------|---------|----------|---------------|------------|---------|
| No slippage (current) | 2.063% | 0.907% | 1.6 | 0.3196% | ✅ |
| 1x realistic (~0.10% RT) | 1.963% | 1.007% | 1.372 | 0.2196% | ✅ |
| 1.5x conservative | 1.913% | 1.057% | 1.273 | 0.1696% | ✅ |
| 2x stress test | 1.863% | 1.107% | 1.184 | 0.1196% | ✅ |
| 3x worst case | 1.763% | 1.207% | 1.028 | 0.0196% | ✅ |

### Parameter Sensitivity (Plateau vs Spike)

*Robust = PF range < 0.30 across values (plateau). Fragile = PF collapses outside narrow range (spike).*

| Parameter | Value | Trades | Win Rate | PF | Sharpe |
|-----------|-------|--------|----------|----|--------|
| **scalp_rsi_oversold** (⚠️  SPIKE, range=1.70) | | | | | |
| | 30 | 16 | 56.2% | 1.752 | 34.64 |
| | 33 | 19 | 47.4% | 1.451 | 22.34 |
| | 35 | 18 | 44.4% | 1.29 | 15.1 |
| | 38 | 19 | 52.6% | 2.62 | 52.08 |
| | 40 | 19 | 57.9% | 2.992 | 60.35 |
| **scalp_min_volume_ratio** (⚠️  SPIKE, range=1.34) | | | | | |
| | 1.1 | 22 | 40.9% | 1.326 | 16.47 |
| | 1.2 | 18 | 44.4% | 1.29 | 15.1 |
| | 1.3 | 17 | 52.9% | 2.362 | 50.72 |
| | 1.5 | 12 | 50.0% | 2.631 | 55.8 |
| **scalp_rsi_period** (⚠️  SPIKE, range=0.69) | | | | | |
| | 5 | 18 | 55.6% | 1.977 | 38.83 |
| | 7 | 18 | 44.4% | 1.29 | 15.1 |
| | 9 | 18 | 44.4% | 1.846 | 35.29 |
| | 11 | 15 | 40.0% | 1.874 | 35.46 |

---

## Swing Trader

> ADX(20+) trend + RSI(40) pullback, wide SL/TP  
> Timeframe: `1h` | Parameters: 4

### Score: **32/100 — Abandon**

| Dimension | Score | Max |
|-----------|------:|----:|
| Sample Size     | 15 | 20 |
| Expectancy      | 0 | 20 |
| Risk Management | 12 | 20 |
| Robustness      | 5 | 20 |
| Exec Realism    | 0 | 20 |

*Note: Exec Realism = 0 until slippage stress confirms edge survives friction.*

### Baseline Portfolio (15 symbols, 102 trades)

| Metric | Value |
|--------|-------|
| Win Rate | 34.8% |
| Avg Win | 4.8% |
| Avg Loss | 2.943% |
| Profit Factor | 1.401 |
| Expectancy | -0.2484%/trade |
| Avg Max Drawdown | 0.206% |
| Avg Sharpe | -7.87 |
| Avg Return | -0.028% |

#### Per-Symbol Results

| Symbol | Trades | Win Rate | PF | Sharpe | Return |
|--------|--------|----------|----|--------|--------|
| PLTR | 7 | 71.4% | 5.313 | 31.37 | 0.488% |
| SPY | 3 | 66.7% | 4.528 | 26.21 | 0.19% |
| META | 4 | 50.0% | 2.72 | 16.37 | 0.211% |
| AAPL | 8 | 37.5% | 1.984 | 11.38 | 0.192% |
| NVDA | 6 | 33.3% | 1.209 | 3.25 | 0.051% |
| NFLX | 12 | 41.7% | 1.023 | 0.37 | 0.007% |
| TSLA | 6 | 33.3% | 1.013 | 0.22 | 0.003% |
| IWM | 3 | 33.3% | 0.901 | -1.68 | -0.016% |
| GOOGL | 9 | 33.3% | 0.822 | -3.36 | -0.055% |
| BAC | 10 | 30.0% | 0.581 | -10.12 | -0.205% |
| XOM | 10 | 30.0% | 0.469 | -13.07 | -0.192% |
| AMD | 9 | 11.1% | 0.243 | -26.4 | -0.457% |
| JPM | 8 | 25.0% | 0.144 | -39.95 | -0.308% |
| QQQ | 4 | 25.0% | 0.059 | -50.23 | -0.15% |
| AMZN | 3 | 0.0% | 0.0 | -62.41 | -0.182% |

### Slippage Stress Test

| Scenario | Adj Win | Adj Loss | Profit Factor | Expectancy | Survives |
|----------|---------|----------|---------------|------------|---------|
| No slippage (current) | 4.8% | 2.943% | 0.871 | -0.2484% | ❌ |
| 1x realistic (~0.10% RT) | 4.7% | 3.043% | 0.824 | -0.3484% | ❌ |
| 1.5x conservative | 4.65% | 3.093% | 0.802 | -0.3984% | ❌ |
| 2x stress test | 4.6% | 3.143% | 0.781 | -0.4484% | ❌ |
| 3x worst case | 4.5% | 3.243% | 0.741 | -0.5484% | ❌ |

### Parameter Sensitivity (Plateau vs Spike)

*Robust = PF range < 0.30 across values (plateau). Fragile = PF collapses outside narrow range (spike).*

| Parameter | Value | Trades | Win Rate | PF | Sharpe |
|-----------|-------|--------|----------|----|--------|
| **swing_adx_min** (⚠️  SPIKE, range=1.21) | | | | | |
| | 15 | 9 | 33.3% | 1.466 | 6.49 |
| | 17 | 8 | 37.5% | 1.984 | 11.38 |
| | 20 | 8 | 37.5% | 1.984 | 11.38 |
| | 23 | 5 | 40.0% | 2.503 | 14.33 |
| | 25 | 4 | 25.0% | 1.295 | 3.72 |
| | 28 | 3 | 33.3% | 1.697 | 7.54 |
| **swing_rsi_oversold** (⚠️  SPIKE, range=2.45) | | | | | |
| | 35 | 5 | 40.0% | 1.758 | 9.42 |
| | 38 | 6 | 33.3% | 1.45 | 6.13 |
| | 40 | 8 | 37.5% | 1.984 | 11.38 |
| | 43 | 10 | 50.0% | 2.636 | 16.14 |
| | 45 | 13 | 61.5% | 3.902 | 23.46 |

---

## Dca Accumulator

> Buy dips 2% below EMA50 with RSI<=45 confirmation  
> Timeframe: `1h` | Parameters: 4

### Score: **47/100 — Refine**

| Dimension | Score | Max |
|-----------|------:|----:|
| Sample Size     | 20 | 20 |
| Expectancy      | 9 | 20 |
| Risk Management | 13 | 20 |
| Robustness      | 5 | 20 |
| Exec Realism    | 0 | 20 |

*Note: Exec Realism = 0 until slippage stress confirms edge survives friction.*

### Baseline Portfolio (10 symbols, 799 trades)

| Metric | Value |
|--------|-------|
| Win Rate | 43.9% |
| Avg Win | 3.414% |
| Avg Loss | 1.873% |
| Profit Factor | 1.494 |
| Expectancy | 0.448%/trade |
| Avg Max Drawdown | 0.537% |
| Avg Sharpe | 5.57 |
| Avg Return | 0.545% |

#### Per-Symbol Results

| Symbol | Trades | Win Rate | PF | Sharpe | Return |
|--------|--------|----------|----|--------|--------|
| SPY | 30 | 56.7% | 2.912 | 15.93 | 0.7% |
| XOM | 53 | 54.7% | 1.795 | 9.5 | 0.748% |
| QQQ | 53 | 45.3% | 1.619 | 7.93 | 0.571% |
| TSLA | 168 | 42.3% | 1.424 | 5.77 | 1.876% |
| META | 98 | 37.8% | 1.313 | 4.3 | 0.676% |
| JPM | 50 | 50.0% | 1.307 | 4.29 | 0.329% |
| AAPL | 57 | 40.4% | 1.291 | 4.08 | 0.353% |
| GOOGL | 73 | 39.7% | 1.211 | 3.21 | 0.316% |
| AMZN | 79 | 36.7% | 1.185 | 2.83 | 0.351% |
| NVDA | 138 | 35.5% | 0.881 | -2.1 | -0.469% |

### Slippage Stress Test

| Scenario | Adj Win | Adj Loss | Profit Factor | Expectancy | Survives |
|----------|---------|----------|---------------|------------|---------|
| No slippage (current) | 3.414% | 1.873% | 1.426 | 0.448% | ✅ |
| 1x realistic (~0.10% RT) | 3.314% | 1.973% | 1.314 | 0.348% | ✅ |
| 1.5x conservative | 3.264% | 2.023% | 1.263 | 0.298% | ✅ |
| 2x stress test | 3.214% | 2.073% | 1.213 | 0.248% | ✅ |
| 3x worst case | 3.114% | 2.173% | 1.121 | 0.148% | ✅ |

### Parameter Sensitivity (Plateau vs Spike)

*Robust = PF range < 0.30 across values (plateau). Fragile = PF collapses outside narrow range (spike).*

| Parameter | Value | Trades | Win Rate | PF | Sharpe |
|-----------|-------|--------|----------|----|--------|
| **dca_dip_pct** (⚠️  SPIKE, range=0.34) | | | | | |
| | 0.01 | 89 | 39.3% | 1.189 | 2.79 |
| | 0.015 | 79 | 41.8% | 1.282 | 3.99 |
| | 0.02 | 57 | 40.4% | 1.291 | 4.08 |
| | 0.025 | 48 | 41.7% | 1.169 | 2.47 |
| | 0.03 | 41 | 43.9% | 0.948 | -0.84 |
| **dca_rsi_max** (✅ PLATEAU, range=0.10) | | | | | |
| | 40 | 57 | 40.4% | 1.291 | 4.08 |
| | 43 | 57 | 40.4% | 1.291 | 4.08 |
| | 45 | 57 | 40.4% | 1.291 | 4.08 |
| | 48 | 58 | 41.4% | 1.394 | 5.32 |
| | 50 | 58 | 41.4% | 1.394 | 5.32 |

---

## Summary — All Strategies

| Strategy | Score | Verdict | Trades | Win Rate | PF | Sharpe | 1.5x Slip PF | 1.5x Survives |
|----------|------:|---------|--------|----------|----|--------|-------------|--------------|
| mean_reversion | 37 | Abandon | 1990 | 37.3% | 0.999 | -0.42 | 0.884 | ❌ |
| bollinger_breakout | 44 | Refine | 354 | 44.3% | 1.38 | 9.58 | 1.076 | ✅ |
| ema_crossover | 42 | Refine | 1370 | 38.4% | 1.049 | 0.52 | 0.925 | ❌ |
| scalp_master | 44 | Refine | 147 | 41.3% | 1.857 | 27.29 | 1.273 | ✅ |
| swing_trader | 32 | Abandon | 102 | 34.8% | 1.401 | -7.87 | 0.802 | ❌ |
| dca_accumulator | 47 | Refine | 799 | 43.9% | 1.494 | 5.57 | 1.263 | ✅ |

---

### Scoring Framework Reference

| Dimension | Max | Key Thresholds |
|-----------|----:|---------------|
| Sample Size | 20 | 200+ trades = full; <30 = zero |
| Expectancy | 20 | PF 1.5+ = healthy; <1.0 = negative edge |
| Risk Mgmt | 20 | DD <15% best; >40% near zero |
| Robustness | 20 | ≤4 params + 10yr = best; 7+ params = flag |
| Exec Realism | 20 | Slippage tested = full; untested = 0 |

**Verdict:** Deploy ≥70 | Refine 40-69 | Abandon <40


*Generated by full_strategy_stress_test.py*