import sqlite3
import sys
import os
import copy
import argparse
from pathlib import Path
from local_functions import (
    colorize,
    clean_ansi,
    colors,
    ANSI_ESCAPE_RE,
)

# Standard library approach to handle Windows initialization safely
if sys.platform == "win32":
    os.system(
        ""
    )  # Crucial trick: This forces the Windows terminal engine to enable ANSI parsing natively


# Initialize Windows Terminal engine for ANSI sequences
if sys.platform == "win32":
    os.system("")


output_file = ""
EQUALSTR = "=" * 128 + "\n"
BL_EQUALSTR = colorize(EQUALSTR, "blue")
tot_losers = 0
tot_winners = 0

# Fi path to the trading bot DB
if os.name == "nt":
    DB_PATH = os.path.join(
        os.path.dirname(__file__),
        "..\\..",
        "data",
        "trading_bot.db",
    )
else:
    DB_PATH = os.path.join(
        os.path.dirname(__file__),
        "../..",
        "data",
        "trading_bot.db",
    )


def print_outfile(text, output_file):
    """
    Print to Stdout or file name provided. Backwards compatible wrapper.
    If output_file is provided, text is appended to that file.
    Otherwise text is printed to stdout.
    """
    if output_file:
        # Automatically strip ANSI colors before writing to the text file
        clean_text = clean_ansi(text)
        with open(output_file, "a", encoding="utf-8") as file:
            file.write(clean_text)
    else:
        print(text, end="")


def connect():
    """Open  up the database or quit if ccant"""
    try:
        conn = sqlite3.connect(DB_PATH)
    except sqlite3.OperationalError as e:
        print(f"Database error: {DB_PATH}")
        sys.exit()
    conn.row_factory = sqlite3.Row
    return conn


def get_closed_trades(conn):
    """Read from he database using SQL"""
    c = conn.cursor()
    c.execute(
        "SELECT * FROM trades WHERE status=? ORDER BY exit_time DESC",
        ("closed",),
    )
    return [dict(r) for r in c.fetchall()]


def proc_dict(loc_trade_list, strat_name, key, output_file):
    """Process the provided dictionary of trades"""
    # Initialize Locals
    counter = 1
    col_pnl = ""
    total_pnl = 0

    tot_winners = 0
    tot_losers = 0
    trade_count = 0
    tot_wins = 0.0
    tot_losses = 0.0
    max_win = 0.0
    max_loss = 0.0
    avg_win = 0.0
    avg_loss = 1000000000.0

    # Print  Tttle , header graphics and column headers
    print_outfile(
        f"List of {colorize(strat_name, 'red')} Trades\n",
        output_file,
    )
    print_outfile(BL_EQUALSTR, output_file)
    print_outfile(
        colorize(
            f"{'Id:':<16}{'Entry':<24}{'Exit':<24}{'Symbol':<16}{'Direct':<9}{'Entry Price':<15}{'Exit Price':<17}{'PnL':<10}\n",
            "magenta",
        ),
        output_file,
    )
    print_outfile(BL_EQUALSTR, output_file)

    # Search the dict for Key  provided
    for trade_dict in loc_trade_list:
        if trade_dict[key] == strat_name or strat_name == "ALL":
            #  entry contains strat were after total the PnL
            total_pnl += trade_dict["pnl"]
            # Running total the umber of wins or losses and tracj the total of each
            if trade_dict["pnl"] >= 0:
                tot_winners += 1
                tot_wins += trade_dict["pnl"]
            else:
                tot_losers += 1
                tot_losses += trade_dict["pnl"]
            # Track the biggst win and biggest loss
            if max_win < trade_dict["pnl"]:
                max_win = trade_dict["pnl"]
            if max_loss > trade_dict["pnl"]:
                max_loss = trade_dict["pnl"]
            # Track the number of trades processed
            trade_count += 1
            # Combine 3 sections onto one line then print it
            if trade_dict["pnl"] < 0:
                col_pnl = colorize(
                    f"{float(trade_dict['pnl']):8.2f}",
                    "red",
                )
            else:
                col_pnl = colorize(
                    f"{float(trade_dict['pnl']):8.2f}",
                    "green",
                )
            if counter % 3 == 0:
                print_outfile(  # 3rd pass - end building 3 rows
                    f"{trade_dict['trade_id'][-12:]:<7}"
                    f"\t{trade_dict['entry_time'][0:16]:<10}"
                    f"\t{trade_dict['exit_time'][0:16]:<10}"
                    f"{colorize(f'\t{trade_dict["symbol"]:<10}', 'cyan')}"
                    f"\t{trade_dict['direction']:<5}"
                    f"\t{float(trade_dict['entry_price']):>8.2f}"
                    f"\t{float(trade_dict['exit_price']):>8.2f}  "
                    f"\t{col_pnl}\t\n",
                    output_file,
                )
                counter += 1
            else:
                print_outfile(  # Pass 1 and 2 builde side by side
                    f"{trade_dict['trade_id'][-12:]:<7}"
                    + f"\t{trade_dict['entry_time'][0:16]:<10}"
                    + f"\t{trade_dict['exit_time'][0:16]:<10}"
                    + f"{colorize(f'\t{trade_dict["symbol"]:<10}', 'cyan')}"
                    + f"\t{trade_dict['direction']:<5}"
                    + f"\t{trade_dict['entry_price']:>8.2f}"
                    + f"\t{trade_dict['exit_price']:>8.2f}"
                    + f"\t{col_pnl}\t\n",
                    output_file,
                )
                counter += 1
    if tot_winners == 0:
        avg_wins = -1
    else:
        avg_wins = tot_wins / tot_winners
    if tot_losers == 0:
        avg_loss = -1
    else:
        avg_loss = tot_losses / tot_losers

    ret_dict = {}
    ret_dict["loss_pct"] = colorize(
        f"{(tot_losers / trade_count) * 100:.0f}",
        "red",
    )
    ret_dict["win_pct"] = colorize(
        f"{(tot_winners / trade_count) * 100:>3.0f}",
        "green",
    )
    ret_dict["trade_count"] = f"{trade_count:<12}"

    if total_pnl >= 0:
        ret_dict["total_pnl"] = colorize(f"{total_pnl:<14.2f}", "green")
    else:
        ret_dict["total_pnl"] = colorize(f"{total_pnl:<14.2f}", "red")
    ret_dict["max_win"] = colorize(f"{max_win:<14.2f}", "green")
    ret_dict["max_loss"] = colorize(f"{max_loss:>3.2f}", "red")
    ret_dict["avg_wins"] = colorize(f"{avg_wins:<12.2f}", "green")
    ret_dict["avg_loss"] = colorize(f"{avg_loss:<14.2f}", "red")
    ret_dict["tot_wins"] = colorize(f"{tot_winners:>3}", "green")
    ret_dict["tot_losers"] = colorize(f"{tot_losers:<11}", "red")
    #   print(ret_dict)

    return ret_dict


#    return trade_count, total_pnl, max_win, max_loss, avg_wins, avg_loss, tot_winners, tot_losers


def print_col_headers(trades_lst):
    """
    Prints the list of column headers in the trades table given switch -N
    We're processinaaaaaaaag a list of dictionaries of Trade information
    """
    final_list = ""
    local_counter = 1

    for key_lst in trades_lst:
        for my_key in key_lst:
            # Always append the current key with left-alignment padding
            final_list += f"{my_key:<20}"

            # Print and clear the row every 5 items
            if local_counter % 5 == 0:
                print(final_list)
                final_list = ""

            local_counter += 1

    # Print any leftover columns if the total count isn't perfectly divisible by 5
    if final_list:
        print(final_list)
    return


def build_hdr_list(trades_lst2):
    """Collect the column header names in trades table"""
    # Flattens the nested structure into a single list of keys in one line
    return [my2_key for key2_lst in trades_lst2 for my2_key in key2_lst]


def main():

    # Connect to DB and load the trades table into the trades_list dictionary
    conn = connect()
    try:
        trades_list = get_closed_trades(conn)
        conn.close()
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
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

    parser.add_argument(
        "-o",
        "--outfile",
        metavar="",
        help="\tpath and name of output file",
    )
    parser.add_argument(
        "-1",
        "--list1",
        metavar="",
        help="ALL or a <comma seperated list of values found in first provided key>",
    )
    parser.add_argument(
        "-2",
        "--list2",
        metavar="",
        help="ALL or a <Comma seperated list of valuws found in second providd key>",
    )
    parser.add_argument(
        "-3",
        "--list3",
        metavar="",
        help="ALL or a <Comma seperated list of valuws found in second providd key>",
    )
    parser.add_argument(
        "-k",
        "--key",
        metavar="",
        help="ALL or a <Comma seperated list of DB table keys to index and search>",
    )
    parser.add_argument(
        "-N",
        "--Names",
        action="store_true",
        help="If given prints a list of all trade table key names you can use",
    )
    args = parser.parse_args()

    if args.Names:
        print_col_headers(trades_list)
        sys.exit(2)

    if (not args.list1 and not args.list2 and not args.list3) or (
        not (len(args.key) >= 1)
    ):
        parser.print_help()
        parser.exit(
            2,
            "\nError: provide --key key1,key2 and (--list1 (ALL) or --list2 (ALL)or both).\n",
        )

    output_file = args.outfile
    strat_list = args.list1.split(",") if args.list1 else []
    ticker_list = args.list2.split(",") if args.list2 else []
    asset_list = args.list3.split(",") if args.list3 else []
    key_list = args.key.split(",") if args.key else ["None"]

    for keys in key_list:
        if keys not in hdr_list:
            print(
                f"\nError: {keys} is not a valid entry. please run with -N to see a list of valid choices\n"
            )
            sys.exit()

    dict_of_trades_by_list1 = {}
    dict_of_trades_by_list2 = {}
    dict_of_trades_by_list3 = {}
    if (not args.Names) and (len(key_list) < 1):
        print(f"\nError: Please provide at least 1 key , seperated by a ,\n")
        sys.exit()

    key1 = key_list[0]
    key2 = key_list[1] if (len(key_list) > 1) else []
    key3 = key_list[2] if (len(key_list) > 2) else []

    for trade in trades_list:
        strat_name = trade[key1]
        dict_of_trades_by_list1.setdefault(strat_name, []).append(
            copy.deepcopy(trade)
        )  # Deep copy of trade

    res_dict = {}
    for strat in dict_of_trades_by_list1:
        # "fetch the list of dicts" — this is what you were missing
        trade_list = dict_of_trades_by_list1[strat]
        strat_name = trade_list[0][key1]
        if (len(strat_list) >= 1) and (
            (strat_name in strat_list) or (strat_list[0] == "ALL")
        ):
            res_dict = proc_dict(
                trade_list,
                strat_name,
                key1,
                output_file,
            )
            print_outfile(BL_EQUALSTR, output_file)
            print_outfile(
                f"{'Total Trades:':>13} {res_dict['trade_count']} {'Total P&L:':<11}  {res_dict['total_pnl']}{'Max Win:':<10} {res_dict['max_win']}"
                f"{'Max Loss:':>10}{'':<5}{res_dict['max_loss']}\n"
                f"{'Avg Win:':>13} {res_dict['avg_wins']} {' Avg Loss:':<11}  {res_dict['avg_loss']}"
                f"{'':<4}W/L: {res_dict['tot_wins']}/{res_dict['tot_losers']}{'':<7}W/L%{'':<5}{res_dict['win_pct']}%/{res_dict['loss_pct']}%\n",
                output_file,
            )
            print_outfile(BL_EQUALSTR + "\n\n", output_file)

    res_dict.clear()
    if (len(key_list)) > 1:
        for trade in trades_list:
            symbol_name = trade[key2]
            dict_of_trades_by_list2.setdefault(symbol_name, []).append(trade)

        for symbol in dict_of_trades_by_list2:
            trade_list = dict_of_trades_by_list2[symbol]
            symbol_name = trade_list[0][key2]
            if (len(ticker_list) >= 1) and (
                (symbol_name in ticker_list) or (ticker_list[0] == "ALL")
            ):
                res_dict = proc_dict(
                    trade_list,
                    symbol_name,
                    key2,
                    output_file,
                )
                print_outfile(BL_EQUALSTR, output_file)
                print_outfile(
                    f"{'Total Trades:':>13} {res_dict['trade_count']} {'Total P&L:':<11}  {res_dict['total_pnl']}{'Max Win:':<10} {res_dict['max_win']}"
                    f"{'Max Loss:':<10}{'':<5}{res_dict['max_loss']}\n"
                    f"{'Avg Win:':>13} {res_dict['avg_wins']} {' Avg Loss:':<11}  {res_dict['avg_loss']}"
                    f"{'':<4}W/L: {res_dict['tot_wins']}/{res_dict['tot_losers']}{'':<7}W/L%{'':<5}{res_dict['win_pct']}%/{res_dict['loss_pct']}%\n",
                    output_file,
                )
                print_outfile(
                    BL_EQUALSTR + "\n\n",
                    output_file,
                )

    #                print_outfile(BL_EQUALSTR, output_file)
    res_dict.clear()
    if (len(key_list)) > 2:
        for trade in trades_list:
            asset_name = trade[key3]
            dict_of_trades_by_list3.setdefault(asset_name, []).append(trade)

        for asset in dict_of_trades_by_list3:
            trade_list = dict_of_trades_by_list3[asset]
            asset_name = trade_list[0][key3]
            if (len(asset_list) >= 1) and (
                (asset_name in asset_list) or (asset_list[0] == "ALL")
            ):
                res_dict = proc_dict(
                    trade_list,
                    asset_name,
                    key3,
                    output_file,
                )
                print_outfile(BL_EQUALSTR, output_file)
                print_outfile(
                    f"{'Total Trades:':>13} {res_dict['trade_count']:<6} {'Total P&L:':<11} {res_dict['total_pnl']}{'Max Win:':<10} {res_dict['max_win']}"
                    f"{'Max Loss:':<10}{'':<5}{res_dict['max_loss']}\n"
                    f"{'Avg Win:':>13} {res_dict['avg_wins']:<6} {' Avg Loss:':<11}  {res_dict['avg_loss']}"
                    f"{'':<4}W/L: {res_dict['tot_wins']}/{res_dict['tot_losers']}{'':<7}W/L%{'':<5}{res_dict['win_pct']}%/{res_dict['loss_pct']}%\n",
                    output_file,
                )
                print_outfile(
                    BL_EQUALSTR + "\n\n",
                    output_file,
                )


if __name__ == "__main__":
    main()
