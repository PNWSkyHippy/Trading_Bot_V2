

import sqlite3
import sys
import os
import copy
import argparse
from pathlib import Path

output_file = ""
EQUALSTR = "=" * 128 + "\n"

# Fi path to the trading bot DB
if os.name == "nt":
    DB_PATH = os.path.join(os.path.dirname(__file__), '..\\..', 'data',
                       'trading_bot.db')
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), '../..', 'data',
                       'trading_bot.db')


def print_outfile(text, output_file):
    """ Print to Stdout or file name provided """
    if output_file:
        with open(output_file, "a", encoding="utf-8") as file:
            file.write(text)
    else:
        print(text, end="")


def connect():
    """ Open  up the database or quit if ccant """
    try:
        conn = sqlite3.connect(DB_PATH)
    except sqlite3.OperationalError as e:
        print(f'Database error: {DB_PATH}')
        sys.exit()
    conn.row_factory = sqlite3.Row
    return conn



def get_closed_trades(conn):
    """  Read from he database using SQL """
    c = conn.cursor()
    c.execute(
        'SELECT * FROM trades WHERE status=? ORDER BY exit_time DESC',
        ('closed',)
    )
    return [dict(r) for r in c.fetchall()]

tot_losers = 0
tot_winners = 0

def proc_dict(loc_trade_list, strat_name,key,  output_file):
    """ Process the provided dictionary of trades """
    # Initialize Locals
  
    tot_losers = 0
    tot_winners = 0
    counter = 1
    total_pnl = 0
    trade_count = 0
    max_win = 0.0
    max_loss = 0.0
    avg_win = 0.0
    tot_wins = 0.0
    tot_losses = 0.0
    avg_loss = 1000000000.0
    #Print  Tttle , header graphics and column headers
    print_outfile(f'List of {strat_name} Trades\n', output_file)
    print_outfile(EQUALSTR, output_file)
    print_outfile(f'Id:\t\tEntry\t\t\tExit\t\t\tSymbol\t\tDirct\tEntry Price\tExit Price\t PnL\n', output_file)
    print_outfile(EQUALSTR, output_file)

    # Search the dict for Key  provided
    for trade_dict in loc_trade_list:
        if trade_dict[key] == strat_name or strat_name == "ALL":
	    #  entry contains strat were affter, total the PnL
            total_pnl += trade_dict['pnl']
            if trade_dict['pnl'] >= 0:
                tot_winners += 1
                tot_wins += trade_dict['pnl']
            else:
                tot_losers += 1
                tot_losses += trade_dict['pnl']
            if max_win <  trade_dict['pnl']:
                max_win = trade_dict['pnl']
            if max_loss > trade_dict['pnl']:
                max_loss = trade_dict['pnl']
            trade_count += 1
	    # Combine 3 sections onto one line then print it
            if counter % 3 == 0:
                print_outfile( #3rd pass -  end building 3 rows
			f'{trade_dict["trade_id"][-12:]:<7}'
                        f'\t{trade_dict["entry_time"][0:16]:<10}'
                        f'\t{trade_dict["exit_time"][0:16]:<10}'
                        f'\t{trade_dict["symbol"]:<10}'
                        f'\t{trade_dict["direction"]:<5}'
                        f'\t{float(trade_dict["entry_price"]):>8.2f}'
                        f'\t{float(trade_dict["exit_price"]):>8.2f}  '
                        f'\t{trade_dict["pnl"]: 8.2f}\t\n', output_file
                    )
                counter += 1
            else:
                print_outfile(  # Pass 1 and 2 builde side by side 
			f'{trade_dict["trade_id"][-12:]:<7}' +
                        f'\t{trade_dict["entry_time"][0:16]:<10}' +
                        f'\t{trade_dict["exit_time"][0:16]:<10}' +
                        f'\t{trade_dict["symbol"]:<10}' +
                        f'\t{trade_dict["direction"]:<5}' +
                        f'\t{trade_dict["entry_price"]:>8.2f}' +
                        f'\t{trade_dict["exit_price"]:>8.2f}' +
                        f'\t{trade_dict["pnl"]: 8.2f}\t\n', output_file
                    )
                counter += 1
    if tot_winners == 0:
        avg_wins = -1
    else:
        avg_wins = (tot_wins / tot_winners) 
    if tot_losers == 0:
        avg_loss = -1
    else:
        avg_loss = (tot_losses / tot_losers)


    ret_dict = {}
    ret_dict["trade_count"] = trade_count
    ret_dict["total_pnl"] = total_pnl
    ret_dict["max_win"] = max_win
    ret_dict["max_loss"] = max_loss
    ret_dict["avg_wins"] = avg_wins
    ret_dict["avg_loss"] = avg_loss
    ret_dict["tot_wins"] =  tot_winners
    ret_dict["tot_losers"] = tot_losers
 #   print(ret_dict)

    return(ret_dict)
#    return trade_count, total_pnl, max_win, max_loss, avg_wins, avg_loss, tot_winners, tot_losers


def print_col_headers(trades_lst):
    """ Prints the list of colum headers in the trades table  givn switch -N
        Were processing a list of dictioaries of Trade infomaton
    """
    final_list = ""
    local_counter = 1
    for key_lst in trades_lst:
        for my_key in key_lst:
            if (local_counter % 5) == 0:
                final_list +=  f"{my_key:<20}\n"
                print(final_list)
                final_list = ""
            else:
                final_list +=  f"{my_key:<20}"
            local_counter += 1
        return


def build_hdr_list(trades_lst2):
    """ collect the column header names in trades table """
    col_hdr_lst = []
    for key2_lst in  trades_lst2:
        for my2_key in key2_lst:
            col_hdr_lst.append(my2_key)
    return col_hdr_lst



def main():

    # Connect to DB and load the trades table into the trades_list dictionary
    conn = connect()
    try:
        trades_list = get_closed_trades(conn)
        conn.close()
    except sqlite3.OperationalError as e:
        print(f'Database error: {e}')
        conn.close()
        sys.exit(1)

    hdr_list = build_hdr_list(trades_list)


    def wide_formatter(prog):
        return argparse.RawDescriptionHelpFormatter(
            prog,
            width=110,
            max_help_position=46,
        )


    parser = argparse.ArgumentParser(
        description="List PnL based on search criteria",
    	epilog="""\
Usage examples:
  trades_list.py -k strategy_name -1 emt
  trades_list.py -k strategy_name,symbol -1 emt -2 ESU6
  trades_list.py -k strategy_name -1 ALL -o report.txt
  trades_list.py -N
""",
        formatter_class=wide_formatter,
    )

    parser.add_argument("-o","--outfile", metavar="", help="\tpath and name of output file")
    parser.add_argument("-1","--list1", metavar="",
            help="ALL or a <comma seperated list of values found in first provided key>"
    )
    parser.add_argument("-2","--list2", metavar="",
            help="ALL or a <Comma seperated list of valuws found in second providd key>"
    )
    parser.add_argument("-3","--list3", metavar="",
            help="ALL or a <Comma seperated list of valuws found in second providd key>"
    )
    parser.add_argument("-k","--key", metavar="",
            help="ALL or a <Comma seperated list of DB table keys to index and search>"
    )
    parser.add_argument("-N", "--Names", action='store_true',
            help="If given prints a list of all trade table key names you can use"
    )
    args = parser.parse_args()


    if args.Names:
        print_col_headers(trades_list)
        sys.exit(2)

    if (not args.list1 and not args.list2 and not args.list3) or (not (len(args.key) >= 1)):
        parser.print_help()
        parser.exit(
            2,
            "\nError: provide --key key1,key2 and (--list1 (ALL) or --list2 (ALL)or both).\n"
        )


    output_file = args.outfile
    strat_list = args.list1.split(",") if args.list1 else []
    ticker_list = args.list2.split(",") if args.list2 else []
    asset_list = args.list3.split(",") if args.list3 else []
    key_list  = args.key.split(",") if args.key else ["None"]

    for keys in key_list:
        if keys not in hdr_list:
            print(f'\nError: {keys} is not a valid entry. please run with -N to see a list of valid choices\n')
            sys.exit()

    dict_of_trades_by_list1 = {}
    dict_of_trades_by_list2 = {}
    dict_of_trades_by_list3 = {}
    if (not args.Names) and (len(key_list) <1):
        print(f'\nError: Please provide at least 1 key , seperated by a ,\n')
        sys.exit()

    key1 = key_list[0]
    key2 = key_list[1] if (len(key_list) > 1) else []
    key3 = key_list[2] if (len(key_list) > 2) else []

    for trade in trades_list:
        strat_name = trade[key1]
        dict_of_trades_by_list1.setdefault(strat_name, []).append(copy.deepcopy(trade)) # Deep copy of trade

    win_pxt = 0.0
    res_dict = {}
    max_wins = 0.0
    max_losses = 0.0
    acg_wins = 0.0
    avg_loss = 0.0
    for strat in dict_of_trades_by_list1:
        # "fetch the list of dicts" — this is what you were missing
        trade_list = dict_of_trades_by_list1[strat]
        strat_name = trade_list[0][key1]
        if (len(strat_list) >= 1) and ((strat_name in strat_list) or (strat_list[0] == "ALL")):
            res_dict = proc_dict(trade_list, strat_name, key1, output_file)
            win_pct = (res_dict["tot_wins"] / res_dict["tot_losers"]) * 100
            print_outfile(EQUALSTR, output_file)
            print_outfile(f'Total Trades:  {res_dict["trade_count"]}\tTotal P&L: {res_dict["total_pnl"]:.2f}\tMax Win: {res_dict["max_win"]:.2f}\t\t'
                           f'Max Loss: {res_dict["max_loss"]:.2f}\t\n'
                           f'Avg Win: {res_dict["avg_wins"]:.2f}\t\tAvg Loss: {res_dict["avg_loss"]:.2f}\t'
                           f'W/L({res_dict["tot_wins"]}/{res_dict["tot_losers"]})\t\tWinPct({win_pct:.2f}%)\n',
                           output_file
                          )

            print_outfile(EQUALSTR + "\n\n", output_file)
    res_dict.clear()
    if (len(key_list)) > 1:
        for trade in trades_list:
            symbol_name = trade[key2]
            dict_of_trades_by_list2.setdefault(symbol_name, []).append(trade)


        for symbol in dict_of_trades_by_list2:

            trade_list = dict_of_trades_by_list2[symbol]
            symbol_name = trade_list[0][key2]
            if (len(ticker_list) >= 1) and ((symbol_name in ticker_list) or (ticker_list[0] == "ALL")):
                res_dict = proc_dict(trade_list, symbol_name,key2,  output_file)
                win_pct = (res_dict["tot_wins"] / res_dict["tot_losers"]) * 100
                print_outfile(EQUALSTR, output_file)
                print_outfile(f'Total Trades:  {res_dict["trade_count"]}\tTotal P&L: {res_dict["total_pnl"]:.2f}\tMax Win: {res_dict["max_win"]:.2f}\t\t'
                               f'Max Loss: {res_dict["max_loss"]:.2f}\t\n'
                               f'Avg Win: {res_dict["avg_wins"]:.2f}\t\tAvg Loss: {res_dict["avg_loss"]:.2f}\t'
                               f'W/L({res_dict["tot_wins"]}/{res_dict["tot_losers"]})\t\tWinPct({win_pct:.2f}%)\n',
                               output_file
                              )

                print_outfile(EQUALSTR + "\n\n", output_file)


    res_dict.clear()
    if (len(key_list)) > 2:
        for trade in trades_list:
            asset_name = trade[key3]
            dict_of_trades_by_list3.setdefault(asset_name, []).append(trade)


        for asset in dict_of_trades_by_list3:

            trade_list = dict_of_trades_by_list3[asset]
            asset_name = trade_list[0][key3]
            if (len(asset_list) >= 1) and ((asset_name in asset_list) or (asset_list[0] == "ALL")):
                res_dict = proc_dict(trade_list, asset_name,key3,  output_file)
                win_pct = (res_dict["tot_wins"] / res_dict["tot_losers"]) * 100
                print_outfile(EQUALSTR, output_file)
                print_outfile(f'Total Trades:  {res_dict["trade_count"]}\tTotal P&L: {res_dict["total_pnl"]:.2f}\tMax Win: {res_dict["max_win"]:.2f}\t\t'
                               f'Max Loss: {res_dict["max_loss"]:.2f}\t\n'
                               f'Avg Win: {res_dict["avg_wins"]:.2f}\t\tAvg Loss: {res_dict["avg_loss"]:.2f}\t'
                               f'W/L({res_dict["tot_wins"]}/{res_dict["tot_losers"]})\t\tWinPct({win_pct:.2f}%)\n',
                              output_file
                              )
                print_outfile(EQUALSTR + "\n\n", output_file)


if __name__ == "__main__":
  main()

