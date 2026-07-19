# P1-A real-strategy profile ledger comparison

Run date: 2026-07-19

Command:

```powershell
venv312\Scripts\python.exe Scripts\test_backtester_p1a_live_strategy_deltas.py
```

The cases were selected from a read-only query of Hostinger's live
`strategy_*_enabled` state and trade history. Every case loaded the genuine
strategy class and historical candle data, then produced independent
`RunLedger` streams under `isolated_v1` and `live_parity_v2`.

| Strategy | Historical case | isolated_v1 trades | live_parity_v2 trades | isolated_v1 return | live_parity_v2 return | Ledger changed |
|---|---:|---:|---:|---:|---:|---:|
| bmr_357 | SAND/USD 15m | 6 | 6 | -0.10% | -0.10% | No |
| bollinger_breakout | RIVN 5m | 22 | 16 | -0.03% | -0.03% | Yes |
| hammer_reversal | RIVN 5m | 0 | 0 | 0.00% | 0.00% | No |
| orb_breakout | ALAB 15m | 8 | 6 | +0.08% | +0.10% | Yes |
| pll_cycle | BTC/USD 1h | 61 | 64 | -0.71% | -0.91% | Yes |
| scalp_master | MSFT 5m | 9 | 6 | -0.03% | -0.01% | Yes |
| vwap_momentum | NIO 1h | 29 | 19 | -0.15% | -0.05% | Yes |

`hammer_reversal` legitimately produced no trades on this historical case;
that zero-delta result is retained rather than replaced with a cherry-picked
fixture. `marc_strategy` and `vdmr_strategy` had enabled database keys but are
not instantiated by `StrategyEngine`, so they are stale configuration records,
not currently executing live strategies.

This is behavior-delta evidence, not a profitability conclusion. The result
sign and magnitude are path- and sample-dependent.
