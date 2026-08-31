import sys
import argparse
from local_functions import colorize

config_micros = {
    'MES': {'tick_val': 1.25, 'rt_fee': 1.04},
    'MNQ': {'tick_val': 0.50, 'rt_fee': 1.04},
    'M2K': {'tick_val': 0.50, 'rt_fee': 1.04},
    'MNK': {'tick_val': 2.50, 'rt_fee': 1.04},
    'MET': {'tick_val': 0.05, 'rt_fee': 0.74},
    'MYM': {'tick_val': 0.50, 'rt_fee': 1.04},
    'MGC': {'tick_val': 1.00, 'rt_fee': 1.34},
}

config_minis = {
    'ES':  {'tick_val': 12.50, 'rt_fee': 3.10},
    'NQ':  {'tick_val': 5.00, 'rt_fee': 3.10},
    'RTY':  {'tick_val': 5.00, 'rt_fee': 3.10},
    'NKD':  {'tick_val': 25.00, 'rt_fee': 4.64},
    'ETH':  {'tick_val': 25.00, 'rt_fee': 3.10},
    'YM':  {'tick_val': 5.00, 'rt_fee': 3.10},
    'GC':  {'tick_val': 10.00, 'rt_fee': 3.54}
}

def pair_contracts():
    contract_pairs = {
        micro_symbol: {
            "micro": micro_config,
            "mini_symbol": mini_symbol,
            "mini": mini_config,
        }
        for (micro_symbol, micro_config), (mini_symbol, mini_config)
        in zip(config_micros.items(), config_minis.items())
    }
    return contract_pairs



def calculate_net_pnl(contract_class: str, contracts: int, ticks_moved: int, exp_gross: int, is_win: bool,  usemini:bool) -> dict:
    """
    Calculates gross profit/loss, exact transaction fees, and final net P&L.
    
    Parameters:
    - contract_class (str): MES MNQ M2K MNK MET MYM MGC'
    - contracts (int): Total number of contracts traded
    - ticks_moved (int): Distance of the target or stop in ticks
    - exp_gross (int) expected gross , recalculates ticks _moved
    - is_win (bool): True if Take Profit was hit, False if Stop Loss was hit
    - usemini (bool): Whether to user the associated mii to the micro called
    """

    contract_pairs = pair_contracts()    
    pair = contract_pairs[contract_class]
    # Normalize input
    c_type = contract_class.upper().strip()
    found = False
    if c_type in config_micros.keys():
        found = True
    if not found:
        raise ValueError(f'Contract class must be in this list:/n/t{configs.keys()}')


    # Configuration mappings: [Tick Value, Round-Trip Fee Per Contract]
    # (Using standard Tradovate prop firm, routing fee schedules)
    contract_name = c_type if not usemini else pair["mini_symbol"]

    ctrct_type = "micro" if not usemini else "mini"

    tick_val = pair[ctrct_type]['tick_val']
    rt_fee_per_contract = pair[ctrct_type]['rt_fee']
    gross_per_tick = ticks_moved * pair[ctrct_type]["tick_val"]
    total_rt_fees = ticks_moved * pair[ctrct_type]["rt_fee"]
#    else:
#        tick_val = pair["mini"]['tick_val']
#        rt_fee_per_contract = pair["mini"]['rt_fee']
#        gross_per_tick = ticks_moved * pair["mini"]["tick_val"]
#        total_rt_fees = ticks_moved * pair["mini"]["rt_fee"]
        
        
    # Financial math
    ticks_moved = exp_gross / tick_val / contracts
    gross_per_contract = ticks_moved * tick_val
    total_gross = gross_per_contract * contracts if is_win else -(gross_per_contract * contracts)
    
    total_fees = rt_fee_per_contract * contracts
    net_pnl = total_gross - total_fees
    
    # Format terminal output using background/blinking terminal styling rules
    # Green background for win, Red background for loss
    fg_color = "green" if net_pnl >= 0 else "red"

    net = f'{net_pnl:,.2f}'
    
    return {
        "Contract": contract_name,
        "Contracts": contracts,
        "Ticks": ticks_moved,
        "Outcome": "WIN" if is_win else "LOSS",
        "Gross P&L": f"${total_gross:,.2f}",
        "Total Fees": f"${total_fees:,.2f}",
        "Net P&L": f'{colorize(net,bold=True, text_col=fg_color)}'
    }

# --- Example Scenarios ---
if __name__ == "__main__":
    import os
    os.system('') # Enables ANSI escape coloring in standard Windows/Linux terminals

    def wide_formatter(prog):
        return (argparse.RawDescriptionHelpFormatter(prog,width=110,max_help_position=46,))

    parser = argparse.ArgumentParser(
        description="Trading Fee Log Comparison",
        epilog="""\
Usage examples:
  calc_pnl_cost.py -s list of comma separated symbols to display (Default All)
  calc_pnl_cost.py -g gross amount aimed for (Default 250)
""",
        formatter_class=wide_formatter,
    )

    parser.add_argument("-l", "--list",  action="store_true",
        help="\tlist valid symbols to choose from",
    )
   
    parser.add_argument("-s", "--symbols", metavar="",
        help="\tlist of comma separated symbols to display",
    )
    parser.add_argument("-g", "--gross", metavar="",
        help="gross amount aiming for",
    )

    args = parser.parse_args()
    
    gross = float(args.gross) if args.gross else float(250)
    
    symbols = args.symbols.split(",") if args.symbols else False

    if args.list:
        key_list = ""
        for key in config_micros.keys():
            key_list = key_list + key + ", "
        print(f'\nValid Symbols are: {key_list}\n')
        sys.exit(1)
        
    print("--- TRADING FEE LOG COMPARISON ---")
    

    if not  symbols:
        # Scenario A: Your 10 Contract MNQ Scalp (50 Ticks)
        futures_scalp = calculate_net_pnl(contract_class="MNQ", contracts=10, ticks_moved=50, exp_gross=gross, is_win=True, usemini=False)
    
        # Scenario B: Single Contract MNQ Swing (500 Ticks)
        futures_swing = calculate_net_pnl(contract_class="MNQ", contracts=1, ticks_moved=500, exp_gross=gross, is_win=True, usemini=False)
    
        # Scenario C: Single Contract Parent NQ Scalp (50 Ticks)
        futures_miniscalp = calculate_net_pnl(contract_class="MNQ", contracts=1, ticks_moved=50, exp_gross=gross, is_win=True, usemini=True)

        # Display results
        for scenario in [futures_scalp, futures_swing, futures_miniscalp]:
            print(f"\n{scenario['Outcome']} Setup for {scenario['Contracts']}x {scenario['Contract']} over {scenario['Ticks']} Ticks:")
            print(f"  Gross: {scenario['Gross P&L']}")
            print(f"  Fees:  {scenario['Total Fees']}")
            print(f"  Net:   {scenario['Net P&L']}")
    else:
        for sym in symbols:
            if sym not in config_micros:
                raise ValueError(f'Error: {sym} is a invalid choice, run with -l to see valid choices')
            contract_pairs = pair_contracts()
            pair = contract_pairs[sym]
            # Scenario A: Your 10 Contract MNQ Scalp (50 Ticks)
            key = pair.keys()
            futures_scalp = calculate_net_pnl(contract_class=sym, contracts=10, ticks_moved=50, exp_gross=gross, is_win=True, usemini=False)
    
            # Scenario B: Single Contract MNQ Swing (500 Ticks)
            futures_swing = calculate_net_pnl(contract_class=sym, contracts=1, ticks_moved=500, exp_gross=gross, is_win=True, usemini=False)
    
            # Scenario C: Single Contract Parent NQ Scalp (50 Ticks)
            futures_miniscalp = calculate_net_pnl(contract_class=sym, contracts=1, ticks_moved=50, exp_gross=gross, is_win=True, usemini=True)

            # Display results
            for scenario in [futures_scalp, futures_swing, futures_miniscalp]:
                print(f"\n{scenario['Outcome']} Setup for {scenario['Contracts']}x {scenario['Contract']} over {scenario['Ticks']} Ticks:")
                print(f"  Gross: {scenario['Gross P&L']}")
                print(f"  Fees:  {scenario['Total Fees']}")
                print(f"  Net:   {scenario['Net P&L']}")
