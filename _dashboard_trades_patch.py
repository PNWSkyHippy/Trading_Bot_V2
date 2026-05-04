session, cap, positions, summaries, today_trades, all_trades = load_data()
capital      = cap["total_capital"] if cap else 0
daily_pnl    = session["pnl_today"]

# Use locked starting capital — never drifts on restart
starting_cap  = session["starting_capital_today"] if session["starting_capital_today"] > 0 else max(capital - daily_pnl, 1.0)
daily_pnl_pct = (daily_pnl / starting_cap * 100) if starting_cap else 0

# Count trades today directly from DB — session counter can drift across midnight
# if the midnight reset or EOD report doesn't fire (e.g. weekend, restart timing).
trades_today_count = len([t for t in today_trades if t["status"] == "closed"])
