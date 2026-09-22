def calculate_net_pnl(
    contract_class: str, contracts: int, ticks_moved: int, is_win: bool
) -> dict:
    """
    Calculates gross profit/loss, exact transaction fees, and final net P&L.

    Parameters:
    - contract_class (str): 'MNQ' or 'NQ'
    - contracts (int): Total number of contracts traded
    - ticks_moved (int): Distance of the target or stop in ticks
    - is_win (bool): True if Take Profit was hit, False if Stop Loss was hit
    """
    # Normalize input
    c_type = contract_class.upper().strip()
    if c_type not in ["MNQ", "NQ"]:
        raise ValueError("Contract class must be either 'MNQ' or 'NQ'")

    # Configuration mappings: [Tick Value, Round-Trip Fee Per Contract]
    # (Using standard Tradovate non-membership, standard routing fee schedules)
    configs = {
        "MNQ": {"tick_val": 0.50, "rt_fee": 1.04},
        "NQ": {"tick_val": 5.00, "rt_fee": 3.10},
    }

    tick_val = configs[c_type]["tick_val"]
    rt_fee_per_contract = configs[c_type]["rt_fee"]

    # Financial math
    gross_per_contract = ticks_moved * tick_val
    total_gross = (
        gross_per_contract * contracts if is_win else -(gross_per_contract * contracts)
    )

    total_fees = rt_fee_per_contract * contracts
    net_pnl = total_gross - total_fees

    # Format terminal output using background/blinking terminal styling rules
    # Green background for win, Red background for loss
    bg_color = "\033[42m" if net_pnl >= 0 else "\033[41m"
    reset_code = "\033[0m"
    bold_code = "\033[1m"

    return {
        "Contract": f"{bold_code}{c_type}{reset_code}",
        "Contracts": contracts,
        "Ticks": ticks_moved,
        "Outcome": "WIN" if is_win else "LOSS",
        "Gross P&L": f"${total_gross:,.2f}",
        "Total Fees": f"${total_fees:,.2f}",
        "Net P&L": f"{bg_color}{bold_code} ${net_pnl:,.2f} {reset_code}",
    }


# --- Example Scenarios ---
if __name__ == "__main__":
    import os

    os.system("")  # Enables ANSI escape coloring in standard Windows/Linux terminals

    print("--- TRADING FEE LOG COMPARISON ---")

    # Scenario A: Your 10 Contract MNQ Scalp (50 Ticks)
    mnq_scalp = calculate_net_pnl(
        contract_class="MNQ", contracts=10, ticks_moved=50, is_win=True
    )

    # Scenario B: Single Contract MNQ Swing (500 Ticks)
    mnq_swing = calculate_net_pnl(
        contract_class="MNQ", contracts=1, ticks_moved=500, is_win=True
    )

    # Scenario C: Single Contract Parent NQ Scalp (50 Ticks)
    nq_scalp = calculate_net_pnl(
        contract_class="NQ", contracts=1, ticks_moved=50, is_win=True
    )

    # Display results
    for scenario in [mnq_scalp, mnq_swing, nq_scalp]:
        print(
            f"\n{scenario['Outcome']} Setup for {scenario['Contracts']}x {scenario['Contract']} over {scenario['Ticks']} Ticks:"
        )
        print(f"  Gross: {scenario['Gross P&L']}")
        print(f"  Fees:  {scenario['Total Fees']}")
        print(f"  Net:   {scenario['Net P&L']}")
