# Full Adversarial Strategy Stress Test

**Date:** 2026-04-18 23:47  
**Framework:** Backtest Expert 5-Dimension (0-100)  
**Capital:** $10,000 per symbol  
**Slippage base:** 0.05% per side (0.10% round-trip)  

---

## Mean Reversion

> Fades extreme z-score deviations back to mean  
> Timeframe: `1h` | Parameters: 3

### Score: **48/100 — Refine**

| Dimension | Score | Max |
|-----------|------:|----:|
| Sample Size     | 20 | 20 |
| Expectancy      | 6 | 20 |
| Risk Management | 12 | 20 |
| Robustness      | 10 | 20 |
| Exec Realism    | 0 | 20 |

*Note: Exec Realism = 0 until slippage stress confirms edge survives friction.*

### Baseline Portfolio (5 symbols, 712 trades)

| Metric | Value |
|--------|-------|
| Win Rate | 39.0% |
| Avg Win | 3.902% |
| Avg Loss | 2.271% |
| Profit Factor | 1.108 |
| Expectancy | 0.1365%/trade |
| Avg Max Drawdown | 0.655% |
| Avg Sharpe | 1.67 |
| Avg Return | 0.385% |

#### Per-Symbol Results

| Symbol | Trades | Win Rate | PF | Sharpe | Return |
|--------|--------|----------|----|--------|--------|
| NVDA | 149 | 44.3% | 1.373 | 5.74 | 1.385% |
| AMZN | 129 | 40.3% | 1.138 | 2.2 | 0.454% |
| AMD | 161 | 35.4% | 1.044 | 0.68 | 0.199% |
| META | 121 | 35.5% | 1.02 | 0.34 | 0.062% |
| TSLA | 152 | 39.5% | 0.966 | -0.62 | -0.173% |

### Long-Term (5yr Daily) Score: 42/100 — Refine

WR=38.9%  PF=0.966  Sharpe=-0.39  Trades=297

### Year-by-Year Performance

| Year | Trades | Win Rate | PF | Sharpe | Return |
|------|--------|----------|----|--------|--------|
| 2024 ✅ | 260 | 39.8% | 1.163 | 2.88 | 0.272% |
| 2025 ✅ | 260 | 39.8% | 1.163 | 2.88 | 0.272% |
| 2026 ✅ | 260 | 39.8% | 1.163 | 2.88 | 0.272% |

*Positive expectancy in 3/3 years tested.*

### Slippage Stress Test

| Scenario | Adj Win | Adj Loss | Profit Factor | Expectancy | Survives |
|----------|---------|----------|---------------|------------|---------|
| No slippage (current) | 3.902% | 2.271% | 1.099 | 0.1365% | ✅ |
| 1x realistic (~0.10% RT) | 3.802% | 2.371% | 1.025 | 0.0365% | ✅ |
| 1.5x conservative | 3.752% | 2.421% | 0.991 | -0.0135% | ❌ |
| 2x stress test | 3.702% | 2.471% | 0.958 | -0.0635% | ❌ |
| 3x worst case | 3.602% | 2.571% | 0.896 | -0.1635% | ❌ |

---

## Bollinger Breakout

> Breaks outside BB bands — Run C params (sq=0.04, ms=0.70)  
> Timeframe: `5m` | Parameters: 4

### Score: **45/100 — Refine**

| Dimension | Score | Max |
|-----------|------:|----:|
| Sample Size     | 19 | 20 |
| Expectancy      | 8 | 20 |
| Risk Management | 13 | 20 |
| Robustness      | 5 | 20 |
| Exec Realism    | 0 | 20 |

*Note: Exec Realism = 0 until slippage stress confirms edge survives friction.*

### Baseline Portfolio (10 symbols, 197 trades)

| Metric | Value |
|--------|-------|
| Win Rate | 45.7% |
| Avg Win | 2.867% |
| Avg Loss | 1.711% |
| Profit Factor | 1.481 |
| Expectancy | 0.3811%/trade |
| Avg Max Drawdown | 0.155% |
| Avg Sharpe | 19.69 |
| Avg Return | 0.178% |

#### Per-Symbol Results

| Symbol | Trades | Win Rate | PF | Sharpe | Return |
|--------|--------|----------|----|--------|--------|
| META | 19 | 57.9% | 2.291 | 49.69 | 0.374% |
| GOOGL | 14 | 50.0% | 2.086 | 42.9 | 0.244% |
| NOW | 29 | 44.8% | 1.934 | 39.71 | 0.498% |
| TSLA | 21 | 52.4% | 1.919 | 40.97 | 0.315% |
| AMD | 25 | 52.0% | 1.486 | 22.65 | 0.23% |
| NVDA | 17 | 41.2% | 1.256 | 14.17 | 0.074% |
| NET | 38 | 39.5% | 1.125 | 7.34 | 0.099% |
| AMZN | 14 | 35.7% | 1.082 | 4.6 | 0.024% |
| SPY | 8 | 50.0% | 1.008 | 0.47 | 0.001% |
| AAPL | 12 | 33.3% | 0.626 | -25.64 | -0.081% |

### Slippage Stress Test

| Scenario | Adj Win | Adj Loss | Profit Factor | Expectancy | Survives |
|----------|---------|----------|---------------|------------|---------|
| No slippage (current) | 2.867% | 1.711% | 1.41 | 0.3811% | ✅ |
| 1x realistic (~0.10% RT) | 2.767% | 1.811% | 1.286 | 0.2811% | ✅ |
| 1.5x conservative | 2.717% | 1.861% | 1.229 | 0.2311% | ✅ |
| 2x stress test | 2.667% | 1.911% | 1.175 | 0.1811% | ✅ |
| 3x worst case | 2.567% | 2.011% | 1.074 | 0.0811% | ✅ |

### Parameter Sensitivity (Plateau vs Spike)

*Robust = PF range < 0.30 across values (plateau). Fragile = PF collapses outside narrow range (spike).*

| Parameter | Value | Trades | Win Rate | PF | Sharpe |
|-----------|-------|--------|----------|----|--------|
| **bb_breakout_std** (✅ PLATEAU, range=0.00) | | | | | |
| | 1.75 | 12 | 33.3% | 0.626 | -25.64 |
| | 2.0 | 12 | 33.3% | 0.626 | -25.64 |
| | 2.25 | 12 | 33.3% | 0.626 | -25.64 |
| | 2.5 | 12 | 33.3% | 0.626 | -25.64 |
| **bb_squeeze_threshold** (✅ PLATEAU, range=0.00) | | | | | |
| | 0.03 | 12 | 33.3% | 0.626 | -25.64 |
| | 0.04 | 12 | 33.3% | 0.626 | -25.64 |
| | 0.05 | 12 | 33.3% | 0.626 | -25.64 |
| | 0.06 | 12 | 33.3% | 0.626 | -25.64 |
| **bb_breakout_min_score** (✅ PLATEAU, range=0.00) | | | | | |
| | 0.6 | 12 | 33.3% | 0.626 | -25.64 |
| | 0.65 | 12 | 33.3% | 0.626 | -25.64 |
| | 0.7 | 12 | 33.3% | 0.626 | -25.64 |
| | 0.75 | 12 | 33.3% | 0.626 | -25.64 |

---

## Ema Crossover

> Fast(9)/Slow(21) EMA cross with EMA50 trend filter  
> Timeframe: `1h` | Parameters: 4

### Score: **42/100 — Refine**

| Dimension | Score | Max |
|-----------|------:|----:|
| Sample Size     | 20 | 20 |
| Expectancy      | 0 | 20 |
| Risk Management | 12 | 20 |
| Robustness      | 10 | 20 |
| Exec Realism    | 0 | 20 |

*Note: Exec Realism = 0 until slippage stress confirms edge survives friction.*

### Baseline Portfolio (10 symbols, 839 trades)

| Metric | Value |
|--------|-------|
| Win Rate | 37.9% |
| Avg Win | 3.47% |
| Avg Loss | 2.136% |
| Profit Factor | 1.016 |
| Expectancy | -0.0113%/trade |
| Avg Max Drawdown | 0.612% |
| Avg Sharpe | -0.12 |
| Avg Return | 0.078% |

#### Per-Symbol Results

| Symbol | Trades | Win Rate | PF | Sharpe | Return |
|--------|--------|----------|----|--------|--------|
| NVDA | 107 | 44.9% | 1.604 | 8.48 | 1.428% |
| AMD | 97 | 40.2% | 1.128 | 2.18 | 0.353% |
| TSLA | 119 | 42.0% | 1.087 | 1.47 | 0.29% |
| NET | 106 | 43.4% | 1.076 | 1.32 | 0.219% |
| QQQ | 55 | 34.5% | 0.997 | -0.05 | -0.004% |
| GOOGL | 74 | 37.8% | 0.931 | -1.29 | -0.139% |
| SPY | 41 | 31.7% | 0.918 | -1.62 | -0.076% |
| AMZN | 84 | 35.7% | 0.858 | -2.6 | -0.334% |
| META | 80 | 35.0% | 0.823 | -3.53 | -0.442% |
| AAPL | 76 | 34.2% | 0.742 | -5.54 | -0.513% |

### Long-Term (5yr Daily) Score: 42/100 — Refine

WR=36.5%  PF=0.896  Sharpe=-1.21  Trades=274

### Year-by-Year Performance

| Year | Trades | Win Rate | PF | Sharpe | Return |
|------|--------|----------|----|--------|--------|
| 2024 ✅ | 259 | 42.8% | 1.084 | 1.53 | 0.126% |
| 2025 ✅ | 259 | 42.8% | 1.084 | 1.53 | 0.126% |
| 2026 ✅ | 259 | 42.8% | 1.084 | 1.53 | 0.126% |

*Positive expectancy in 3/3 years tested.*

### Slippage Stress Test

| Scenario | Adj Win | Adj Loss | Profit Factor | Expectancy | Survives |
|----------|---------|----------|---------------|------------|---------|
| No slippage (current) | 3.47% | 2.136% | 0.991 | -0.0113% | ❌ |
| 1x realistic (~0.10% RT) | 3.37% | 2.236% | 0.92 | -0.1113% | ❌ |
| 1.5x conservative | 3.32% | 2.286% | 0.886 | -0.1613% | ❌ |
| 2x stress test | 3.27% | 2.336% | 0.854 | -0.2113% | ❌ |
| 3x worst case | 3.17% | 2.436% | 0.794 | -0.3113% | ❌ |

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

### Score: **42/100 — Refine**

| Dimension | Score | Max |
|-----------|------:|----:|
| Sample Size     | 17 | 20 |
| Expectancy      | 7 | 20 |
| Risk Management | 13 | 20 |
| Robustness      | 5 | 20 |
| Exec Realism    | 0 | 20 |

*Note: Exec Realism = 0 until slippage stress confirms edge survives friction.*

### Baseline Portfolio (6 symbols, 147 trades)

| Metric | Value |
|--------|-------|
| Win Rate | 38.8% |
| Avg Win | 2.023% |
| Avg Loss | 0.925% |
| Profit Factor | 1.612 |
| Expectancy | 0.2188%/trade |
| Avg Max Drawdown | 0.131% |
| Avg Sharpe | 19.29 |
| Avg Return | 0.08% |

#### Per-Symbol Results

| Symbol | Trades | Win Rate | PF | Sharpe | Return |
|--------|--------|----------|----|--------|--------|
| AMZN | 17 | 58.8% | 3.191 | 72.5 | 0.262% |
| GOOGL | 20 | 30.0% | 2.29 | 38.3 | 0.166% |
| PLTR | 26 | 46.2% | 1.336 | 16.71 | 0.117% |
| IREN | 36 | 33.3% | 1.079 | 3.86 | 0.036% |
| META | 17 | 35.3% | 1.067 | 3.77 | 0.016% |
| ALAB | 31 | 29.0% | 0.709 | -19.39 | -0.119% |

### Slippage Stress Test

| Scenario | Adj Win | Adj Loss | Profit Factor | Expectancy | Survives |
|----------|---------|----------|---------------|------------|---------|
| No slippage (current) | 2.023% | 0.925% | 1.387 | 0.2188% | ✅ |
| 1x realistic (~0.10% RT) | 1.923% | 1.025% | 1.189 | 0.1188% | ✅ |
| 1.5x conservative | 1.873% | 1.075% | 1.105 | 0.0688% | ✅ |
| 2x stress test | 1.823% | 1.125% | 1.027 | 0.0188% | ✅ |
| 3x worst case | 1.723% | 1.225% | 0.892 | -0.0812% | ❌ |

### Parameter Sensitivity (Plateau vs Spike)

*Robust = PF range < 0.30 across values (plateau). Fragile = PF collapses outside narrow range (spike).*

| Parameter | Value | Trades | Win Rate | PF | Sharpe |
|-----------|-------|--------|----------|----|--------|
| **scalp_rsi_oversold** (⚠️  SPIKE, range=1.42) | | | | | |
| | 30 | 15 | 46.7% | 1.475 | 23.55 |
| | 33 | 18 | 38.9% | 1.226 | 12.0 |
| | 35 | 17 | 35.3% | 1.067 | 3.77 |
| | 38 | 18 | 44.4% | 2.327 | 44.73 |
| | 40 | 19 | 47.4% | 2.49 | 48.83 |
| **scalp_min_volume_ratio** (⚠️  SPIKE, range=1.73) | | | | | |
| | 1.1 | 21 | 33.3% | 1.12 | 6.49 |
| | 1.2 | 17 | 35.3% | 1.067 | 3.77 |
| | 1.3 | 16 | 43.8% | 2.005 | 40.13 |
| | 1.5 | 12 | 50.0% | 2.794 | 57.9 |
| **scalp_rsi_period** (⚠️  SPIKE, range=0.88) | | | | | |
| | 5 | 17 | 41.2% | 1.513 | 22.67 |
| | 7 | 17 | 35.3% | 1.067 | 3.77 |
| | 9 | 17 | 35.3% | 1.505 | 23.12 |
| | 11 | 15 | 40.0% | 1.943 | 36.8 |

---

## Swing Trader

> ADX(20+) trend + RSI(40) pullback, wide SL/TP  
> Timeframe: `1h` | Parameters: 4

### Score: **32/100 — Abandon**

| Dimension | Score | Max |
|-----------|------:|----:|
| Sample Size     | 10 | 20 |
| Expectancy      | 0 | 20 |
| Risk Management | 12 | 20 |
| Robustness      | 10 | 20 |
| Exec Realism    | 0 | 20 |

*Note: Exec Realism = 0 until slippage stress confirms edge survives friction.*

### Baseline Portfolio (9 symbols, 58 trades)

| Metric | Value |
|--------|-------|
| Win Rate | 29.1% |
| Avg Win | 5.571% |
| Avg Loss | 3.022% |
| Profit Factor | 1.04 |
| Expectancy | -0.5214%/trade |
| Avg Max Drawdown | 0.219% |
| Avg Sharpe | -8.41 |
| Avg Return | -0.049% |

#### Per-Symbol Results

| Symbol | Trades | Win Rate | PF | Sharpe | Return |
|--------|--------|----------|----|--------|--------|
| META | 4 | 50.0% | 2.72 | 16.37 | 0.211% |
| AAPL | 8 | 37.5% | 1.984 | 11.38 | 0.192% |
| NVDA | 6 | 33.3% | 1.209 | 3.25 | 0.051% |
| TSLA | 6 | 33.3% | 1.013 | 0.22 | 0.003% |
| IWM | 3 | 33.3% | 0.901 | -1.68 | -0.016% |
| GOOGL | 9 | 33.3% | 0.822 | -3.36 | -0.055% |
| XOM | 10 | 30.0% | 0.469 | -13.07 | -0.192% |
| AMD | 9 | 11.1% | 0.243 | -26.4 | -0.457% |
| AMZN | 3 | 0.0% | 0.0 | -62.41 | -0.182% |

### Long-Term (5yr Daily) Score: 50/100 — Refine

WR=100.0%  PF=inf  Sharpe=0.0  Trades=1

### Year-by-Year Performance

| Year | Trades | Win Rate | PF | Sharpe | Return |
|------|--------|----------|----|--------|--------|
| 2024 ❌ | 21 | 35.6% | 0.937 | 8.77 | 0.013% |
| 2025 ❌ | 21 | 35.6% | 0.937 | 8.77 | 0.013% |
| 2026 ❌ | 21 | 35.6% | 0.937 | 8.77 | 0.013% |

*Positive expectancy in 0/3 years tested.*

### Slippage Stress Test

| Scenario | Adj Win | Adj Loss | Profit Factor | Expectancy | Survives |
|----------|---------|----------|---------------|------------|---------|
| No slippage (current) | 5.571% | 3.022% | 0.757 | -0.5214% | ❌ |
| 1x realistic (~0.10% RT) | 5.471% | 3.122% | 0.719 | -0.6214% | ❌ |
| 1.5x conservative | 5.421% | 3.172% | 0.701 | -0.6714% | ❌ |
| 2x stress test | 5.371% | 3.222% | 0.684 | -0.7214% | ❌ |
| 3x worst case | 5.271% | 3.322% | 0.651 | -0.8214% | ❌ |

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

### Score: **51/100 — Refine**

| Dimension | Score | Max |
|-----------|------:|----:|
| Sample Size     | 20 | 20 |
| Expectancy      | 8 | 20 |
| Risk Management | 13 | 20 |
| Robustness      | 10 | 20 |
| Exec Realism    | 0 | 20 |

*Note: Exec Realism = 0 until slippage stress confirms edge survives friction.*

### Baseline Portfolio (7 symbols, 667 trades)

| Metric | Value |
|--------|-------|
| Win Rate | 40.9% |
| Avg Win | 3.592% |
| Avg Loss | 1.95% |
| Profit Factor | 1.286 |
| Expectancy | 0.3167%/trade |
| Avg Max Drawdown | 0.621% |
| Avg Sharpe | 3.83 |
| Avg Return | 0.544% |

#### Per-Symbol Results

| Symbol | Trades | Win Rate | PF | Sharpe | Return |
|--------|--------|----------|----|--------|--------|
| XOM | 54 | 53.7% | 1.698 | 8.72 | 0.705% |
| TSLA | 168 | 42.3% | 1.424 | 5.77 | 1.876% |
| META | 98 | 37.8% | 1.313 | 4.3 | 0.676% |
| AAPL | 57 | 40.4% | 1.291 | 4.08 | 0.353% |
| GOOGL | 73 | 39.7% | 1.211 | 3.21 | 0.316% |
| AMZN | 79 | 36.7% | 1.185 | 2.83 | 0.351% |
| NVDA | 138 | 35.5% | 0.881 | -2.1 | -0.469% |

### Long-Term (5yr Daily) Score: 47/100 — Refine

WR=38.5%  PF=1.046  Sharpe=0.2  Trades=615

### Year-by-Year Performance

| Year | Trades | Win Rate | PF | Sharpe | Return |
|------|--------|----------|----|--------|--------|
| 2024 ✅ | 243 | 43.2% | 1.517 | 6.78 | 0.417% |
| 2025 ✅ | 243 | 43.2% | 1.517 | 6.78 | 0.417% |
| 2026 ✅ | 243 | 43.2% | 1.517 | 6.78 | 0.417% |

*Positive expectancy in 3/3 years tested.*

### Slippage Stress Test

| Scenario | Adj Win | Adj Loss | Profit Factor | Expectancy | Survives |
|----------|---------|----------|---------------|------------|---------|
| No slippage (current) | 3.592% | 1.95% | 1.275 | 0.3167% | ✅ |
| 1x realistic (~0.10% RT) | 3.492% | 2.05% | 1.179 | 0.2167% | ✅ |
| 1.5x conservative | 3.442% | 2.1% | 1.134 | 0.1667% | ✅ |
| 2x stress test | 3.392% | 2.15% | 1.092 | 0.1167% | ✅ |
| 3x worst case | 3.292% | 2.25% | 1.013 | 0.0167% | ✅ |

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
| mean_reversion | 48 | Refine | 712 | 39.0% | 1.108 | 1.67 | 0.991 | ❌ |
| bollinger_breakout | 45 | Refine | 197 | 45.7% | 1.481 | 19.69 | 1.229 | ✅ |
| ema_crossover | 42 | Refine | 839 | 37.9% | 1.016 | -0.12 | 0.886 | ❌ |
| scalp_master | 42 | Refine | 147 | 38.8% | 1.612 | 19.29 | 1.105 | ✅ |
| swing_trader | 32 | Abandon | 58 | 29.1% | 1.04 | -8.41 | 0.701 | ❌ |
| dca_accumulator | 51 | Refine | 667 | 40.9% | 1.286 | 3.83 | 1.134 | ✅ |

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