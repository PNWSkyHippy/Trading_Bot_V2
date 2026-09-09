import pandas as pd
import numpy as np
import sys

# Load your 1,007 trades log
df = pd.read_csv(sys.argv[1])

# 🧮 Fixed exchange cost overhead per trade from your data
total_trades = 1007
total_fees = 13238.85
avg_fee_per_trade_cash = total_fees / total_trades  # ~$13.15 per trade round-trip

# Testing ranges
initial_sl_ranges = np.arange(0.5, 3.0, 0.2)     
trail_trigger_ranges = np.arange(1.0, 6.0, 0.2)  
trailing_distances = [1.0, 1.5, 2.0]            

best_profit = -float('inf')
best_initial_sl = None
best_trigger = None
best_trail_dist = None
best_winrate = 0

for sl in initial_sl_ranges:
    for trigger in trail_trigger_ranges:
        for trail in trailing_distances:
            if trail >= trigger:
                continue
                
            simulated_pnl = []
            
            for idx, trade in df.iterrows():
                mae = abs(trade['MAEpct'])
                mfe = trade['MFEpct']
                entry_value = trade['EntryPrice'] * trade['Quantity']
                
                # Dynamic percentage translation of the fee for this specific position size
                trade_fee_pct = (avg_fee_per_trade_cash / entry_value) * 100.0 if entry_value > 0 else 0.2
                
                # --- PATH A: IMMEDIATE ADVERSE MOVEMENT ---
                # Price moved immediately against us and hit the initial SL 
                # before it ever had a chance to reach our trailing trigger threshold
                if mae >= sl and mfe < trigger:
                    sl_cash_loss = entry_value * ((sl + trade_fee_pct) / 100.0)
                    simulated_pnl.append(-sl_cash_loss)
                    
                # --- PATH B: PROFIT REACHED & RATCHET TRIGGERS ---
                # The breakout successfully cleared your activation milestone first
                elif mfe >= trigger:
                    final_exit_pct = mfe - trail
                    post_fee_exit_pct = final_exit_pct - trade_fee_pct
                    
                    # If it aggressively reverses past your initial floor, your physical order catches it at SL
                    if post_fee_exit_pct < -sl:
                        simulated_pnl.append(-entry_value * ((sl + trade_fee_pct) / 100.0))
                    else:
                        simulated_pnl.append(entry_value * (post_fee_exit_pct / 100.0))
                        
                # --- PATH C: STAGNANT / NATURAL EXITS ---
                # Trade stayed alive without hitting the narrow SL or reaching the trigger
                else:
                    simulated_pnl.append(trade['PNL'])
            
            # Performance optimization math
            total_pnl = sum(simulated_pnl)
            wins = sum(1 for x in simulated_pnl if x > 0)
            winrate = wins / len(simulated_pnl)
            
            if total_pnl > best_profit:
                best_profit = total_pnl
                best_initial_sl = sl
                best_trigger = trigger
                best_trail_dist = trail
                best_winrate = winrate

print(f"🥇 True Post-Fee Optimal Settings Found!")
print(f"-------------------------------------------")
print(f"Initial Stop Loss: {best_initial_sl:.2f}%")
print(f"Activation Threshold (Trigger): {best_trigger:.2f}% MFE")
print(f"Trailing Distance: {best_trail_dist:.2f}%")
print(f"-------------------------------------------")
print(f"Simulated Win Rate: {best_winrate*100:.1f}%")
print(f"Simulated True Net Profit: ${best_profit:.2f}")
