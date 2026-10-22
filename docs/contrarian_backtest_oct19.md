# Contrarian backtest: October 19, 2026 crypto breakout trades

**Paper backtest results only. This is not live performance, and it is
not a promise that inverting signals will profit in future trading.**

## What was tested

On October 19, 2026, the bot's crypto `breakout_scanner` had a losing
day. This report replays that same day with every signal inverted —
long becomes short, short becomes long — using the contrarian rule
already implemented in the bot (`core/breakout_receiver.py`: after a
signal passes its checklist, the direction flips and the trade's
structural stop is cleared).

## Actual outcome, October 19, 2026 (crypto breakout_scanner)

| | Trades | Wins | Losses | Win rate | Net |
|---|---:|---:|---:|---:|---:|
| Actual | 11 | 4 | 7 | 36.4% | -$189.92 |

The day's loss came almost entirely from two trades:

| Trade | Result |
|---|---:|
| UMXM/USD | -$106.86 |
| PHA/USD | -$82.50 |
| Other 9 trades combined | -$0.56 |

Check: -$106.86 + -$82.50 + -$0.56 = -$189.92, matching the day total.

## Inverted replay (same trades, directions flipped)

The replay holds entry and exit prices fixed and negates each trade's
profit, which is what a direction flip produces at identical prices.

| | Trades | Wins | Losses | Win rate | Net |
|---|---:|---:|---:|---:|---:|
| Actual | 11 | 4 | 7 | 36.4% | -$189.92 |
| Inverted | 11 | 7 | 4 | 63.6% | +$189.92 |
| Swing (inverted minus actual) | | | | | +$379.84 |

By group:

| Group | Actual | Inverted |
|---|---:|---:|
| UMXM/USD | 0W / 1L, -$106.86 | 1W / 0L, +$106.86 |
| PHA/USD | 0W / 1L, -$82.50 | 1W / 0L, +$82.50 |
| Other 9 trades | 4W / 5L, -$0.56 | 5W / 4L, +$0.56 |

## Reading the result honestly

- **Inversion flips this day.** The two big losers become the two big
  winners, and the day goes from -$189.92 to +$189.92.
- **The edge is concentrated, not broad.** $189.36 of the $189.92
  inverted gain comes from just UMXM/USD and PHA/USD. The other nine
  trades flip from -$0.56 to +$0.56 — essentially flat either way.
  Inversion alone does not explain a broad edge here; it explains two
  trades.
- **One day, eleven trades, is far too small to conclude anything
  about the rule.** A single day can flip on two trades, as this one
  does. A real decision needs many days of replayed data, including
  days when the forward signals won.
- **The replay is first-order.** Real flipped trades would face
  different stop-loss and take-profit triggers, spreads, and fees, and
  the live receiver clears a flipped trade's structural stop (falling
  back to the custom crypto stop). Realized flipped profit would not
  equal the mirrored figure exactly.

## Data note

Trade-level rows for October 19 were not retrievable from the
repository or by email, so this replay uses the verified aggregate
decomposition above (day total, named losers, remainder) rather than
invented individual trades. The split of the "other 9 trades" group
(4 wins / 5 losses) follows directly from the day totals once the two
named losses are removed. To rerun this test at per-trade precision,
export the day's trades from the bot database and run:

```
python backtest_contrarian_replay.py --data <export.json>
```

The script accepts a `trades` list of `{symbol, direction, pnl}` rows
and prints the same actual-vs-inverted comparison.

## What changed in the repository (main branch)

- `backtest_contrarian_replay.py` — standalone, paper-only replay
  script. It imports no bot code, opens no database, and places no
  orders. It only reads a trade file and prints the comparison.
- `backtest_data/oct19_crypto_breakout.json` — the October 19
  aggregate dataset used for this report, with its provenance noted
  in the file.
- `docs/contrarian_backtest_oct19.md` — this report.

## Live trading is unchanged

No live behavior was modified. The bot's contrarian master switch
remains on but every per-source contrarian flag remains off, so the
receiver does not flip any live signal. Enabling a source flag for
live trading is a separate decision and was not made here.
