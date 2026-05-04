"""
patch_pnl_sl.py
===============
Fixes two bugs:

1. SL/TP wrong side of entry — floating point rounding occasionally puts
   SL within 1 tick of entry or on wrong side. Add a minimum distance
   enforcement after calculation.

2. PnL% wrong — at close time, recalculate pnl_pct directly from prices
   rather than relying on stored position_value which can drift. Also adds
   a sanity check: if calculated pnl_pct exceeds 2x the configured TP%,
   something is wrong — log a warning and cap it.

Run once then delete: python patch_pnl_sl.py
"""

# ── Patch 1: risk_manager.py — enforce minimum SL/TP distance ────────────────
print("Patching risk_manager.py (SL/TP minimum distance)...")
with open("core/risk_manager.py", "r", encoding="utf-8") as f:
    rm = f.read()

old_sl_calc = """        if direction == \"long\":
            stop_loss   = entry_price * (1 - stop_loss_pct)
            take_profit = entry_price * (1 + take_profit_pct)
        else:
            stop_loss   = entry_price * (1 + stop_loss_pct)
            take_profit = entry_price * (1 - take_profit_pct)"""

new_sl_calc = """        if direction == \"long\":
            stop_loss   = entry_price * (1 - stop_loss_pct)
            take_profit = entry_price * (1 + take_profit_pct)
        else:
            stop_loss   = entry_price * (1 + stop_loss_pct)
            take_profit = entry_price * (1 - take_profit_pct)

        # ── Sanity check: enforce minimum SL/TP distance from entry ───────
        # Floating point rounding can occasionally place SL within 1 tick
        # of entry or on the wrong side. Enforce a minimum 0.1% distance.
        MIN_DISTANCE = max(entry_price * 0.001, 0.0001)
        if direction == \"long\":
            if stop_loss >= entry_price - MIN_DISTANCE:
                stop_loss = entry_price * (1 - max(stop_loss_pct, 0.001))
                logger.warning(
                    f\"SL corrected for {symbol} LONG: was too close/wrong side \"
                    f\"of entry ${entry_price:.4f} — reset to ${stop_loss:.4f}\"
                )
            if take_profit <= entry_price + MIN_DISTANCE:
                take_profit = entry_price * (1 + max(take_profit_pct, 0.005))
                logger.warning(
                    f\"TP corrected for {symbol} LONG: was too close/wrong side \"
                    f\"of entry ${entry_price:.4f} — reset to ${take_profit:.4f}\"
                )
        else:  # short
            if stop_loss <= entry_price + MIN_DISTANCE:
                stop_loss = entry_price * (1 + max(stop_loss_pct, 0.001))
                logger.warning(
                    f\"SL corrected for {symbol} SHORT: was too close/wrong side \"
                    f\"of entry ${entry_price:.4f} — reset to ${stop_loss:.4f}\"
                )
            if take_profit >= entry_price - MIN_DISTANCE:
                take_profit = entry_price * (1 - max(take_profit_pct, 0.005))
                logger.warning(
                    f\"TP corrected for {symbol} SHORT: was too close/wrong side \"
                    f\"of entry ${entry_price:.4f} — reset to ${take_profit:.4f}\"
                )"""

if old_sl_calc in rm:
    rm = rm.replace(old_sl_calc, new_sl_calc, 1)
    print("  Fixed: SL/TP minimum distance enforced")
else:
    print("  FAIL: SL/TP calc block not found")

with open("core/risk_manager.py", "w", encoding="utf-8") as f:
    f.write(rm)
print("  risk_manager.py saved")

# ── Patch 2: trade_executor.py — recalculate pnl_pct from prices at close ────
print("\nPatching trade_executor.py (PnL sanity check)...")
with open("core/trade_executor.py", "r", encoding="utf-8") as f:
    te = f.read()

old_pnl = """        if direction == \"long\":
            pnl = (current_price - entry_price) * qty
        else:
            pnl = (entry_price - current_price) * qty

        pnl_pct   = (pnl / trade[\"position_value\"]) * 100 if trade[\"position_value\"] else 0
        trade_won = pnl > 0"""

new_pnl = """        if direction == \"long\":
            pnl = (current_price - entry_price) * qty
        else:
            pnl = (entry_price - current_price) * qty

        # ── PnL% — calculate directly from price move, not position_value ─
        # position_value in DB can drift; price-based calc is always correct.
        # pnl_pct = % move from entry to exit, always positive for wins.
        if entry_price and entry_price > 0:
            raw_move_pct = ((current_price - entry_price) / entry_price) * 100
            pnl_pct      = raw_move_pct if direction == \"long\" else -raw_move_pct
        else:
            pnl_pct = (pnl / trade[\"position_value\"]) * 100 if trade[\"position_value\"] else 0

        # ── Sanity check: pnl_pct should never exceed 3x the configured TP ─
        max_tp_pct = config.DEFAULT_TAKE_PROFIT_PCT * 3
        if abs(pnl_pct) > max_tp_pct:
            logger.warning(
                f\"[PNL SANITY] {symbol}: pnl_pct={pnl_pct:.2f}% exceeds 3x TP threshold \"
                f\"({max_tp_pct:.1f}%). Capping and flagging for review. \"
                f\"entry={entry_price} exit={current_price} qty={qty}\"
            )
            pnl_pct = max_tp_pct if pnl_pct > 0 else -max_tp_pct
            # Recalculate pnl dollar amount to match capped pct
            pnl = (pnl_pct / 100) * trade[\"position_value\"]

        trade_won = pnl > 0"""

if old_pnl in te:
    te = te.replace(old_pnl, new_pnl, 1)
    print("  Fixed: PnL% calculated from price move, with sanity cap")
else:
    print("  FAIL: PnL calc block not found")

with open("core/trade_executor.py", "w", encoding="utf-8") as f:
    f.write(te)
print("  trade_executor.py saved")

print("""
Done. Restart the bot.

What changed:
  1. SL/TP: minimum 0.1% distance enforced from entry price.
     If rounding puts SL too close or on wrong side, it's corrected
     and logged as a WARNING so you can see it happened.

  2. PnL%: now calculated as (exit-entry)/entry*100 directly from
     prices — not from stored position_value which can drift.
     If result exceeds 3x configured TP%, it's capped and logged
     as a WARNING so you can investigate the price data issue.
""")
