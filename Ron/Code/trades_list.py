# ...existing code...
import sqlite3
import sys
import os
import copy
import argparse
import csv
import re

from pathlib import Path
from local_functions import colorize, clean_ansi, colors, ANSI_ESCAPE_RE, date_check,STAT_LABEL_VALUE_RE

# Global Constants
extended = False
csv_true  = False  

EQUALSTR = "=" * 175 + "\n"
BL_EQUALSTR = colorize(EQUALSTR, "blue")
# Find path to the trading bot DB
if os.name == "nt":
    DB_PATH = os.path.join(os.path.dirname(__file__), '..\\..', 'data',
                    'trading_bot.db')
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), '../..', 'data',
                    'trading_bot.db')
# End Globals

def print_outfile(text, output_file):
    """
    Print to Stdout or file name provided. Backwards compatible wrapper.
    If output_file is provided, text is appended to that file.
    Otherwise text is printed to stdout.
    """
    if output_file:
        clean_text = clean_ansi(text)
        try:
            if csv_true:
                with open(output_file + ".csv", 'a', newline='') as csvfile:
                    spamwriter = csv.writer(csvfile, delimiter=',',
                                quotechar=' ', quoting=csv.QUOTE_MINIMAL)
                    for line in clean_text.splitlines():
                        stripped = line.strip()
                        if not stripped or set(stripped) == {'='}:
                            spamwriter.writerow([])
                        elif stripped.count(':') >= 2:
                            # summary lines like "Total Trades: 54   Total P&L: -1320.00 ..."
                            pairs = STAT_LABEL_VALUE_RE.findall(stripped)
                            row = [part.strip() for label, value in pairs for part in (label, value)]
                            spamwriter.writerow(row or stripped.split())
                        else:
                            spamwriter.writerow(stripped.split())
            else:
                with open(output_file, "a", encoding="utf-8") as file:
                    file.write(clean_text)
        except OSError as e:
            print(f'Error writing to output file: {e}')
            sys.exit(1)
    else:
        print(text, end="")

def connect():
    """ Open  up the database or quit if cant """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("SELECT 1 FROM trades LIMIT 1")
    except sqlite3.OperationalError as e:
        print(f'Database error: {DB_PATH}: {e}')
        sys.exit()
    return conn

def get_closed_trades(conn):
    """  Read from he database using SQL """
    c = conn.cursor()
    c.execute(
        'SELECT * FROM trades WHERE status=? ORDER BY exit_time DESC',
        ('closed',)
    )
    return [dict(r) for r in c.fetchall()]

def get_open_trades(conn):
    c = conn.cursor()
    c.execute(
        'SELECT * FROM trades WHERE status=? ORDER BY entry_time DESC',
        ('open',)
    )
    return [dict(r) for r in c.fetchall()]


def proc_dict(loc_trade_list, strat_name,key,  output_file, start_date,end_date):
    """ Process the provided dictionary of trades """
    # Initialize Locals
    col_pnl =  ""
    total_pnl = 0
    tot_winners = 0
    tot_losers = 0
    trade_count = -1
    tot_wins = 0.0
    tot_losses = 0.0
    max_win = 0.0
    max_loss = 0.0
    avg_win = 0.0
    passes = 1
    avg_loss = 1000000000.0
    # One entry per symbol processed by this proc_dict call:
    # {"AAPL": 12.50, "MSFT": -3.25, ...}
    sym_total_pnl = {}
 
    # Search the dict for Key  provided
    trade_count = 0
    for trade in loc_trade_list:
        tid_slice = -(len(trade["trade_id"])) if extended else -16
        tid_pad = 4 + (tid_slice * -1)
#        num = 50 - len(trade["trade_id"])
#        tid_pad = str(num)
        break  # only look at one record
    for trade_dict in loc_trade_list:
        entry_time = trade_dict["entry_time"] or ""
        exit_time = trade_dict["exit_time"] or ""

        if (entry_time[0:16] >= start_date) and (exit_time[0:16] <= end_date):

            if key == "ALL" or trade_dict.get(key, "None") == strat_name or strat_name == "ALL":
                symbol = trade_dict["symbol"]
                trade_pnl = float(trade_dict["pnl"] or 0.0)
                sym_total_pnl[symbol] = sym_total_pnl.get(symbol, 0.0) + trade_pnl
	       #  entry contains strat were after total the PnL
                total_pnl += trade_pnl
                # Running total the number of wins or losses and trace the total of each
                if trade_pnl >= 0:
                    tot_winners += 1
                    tot_wins += trade_pnl
                else:
                    tot_losers += 1
                    tot_losses += trade_pnl
                # Track the biggst win and biggest loss
                if max_win <  trade_pnl:
                    max_win = trade_pnl
                if max_loss > trade_pnl:
                    max_loss = trade_pnl
               # Track the number of trades processed
                trade_count += 1
                if trade_pnl < 0:
                    col_pnl = colorize(f'{trade_pnl:<8.2f}', "red")
                else:
                    col_pnl = colorize(f'{trade_pnl:<8.2f}', "green")
            if (passes == 1):
                print_outfile(f'List of {colorize(strat_name,"red")} Trades\n', output_file)
                print_outfile(BL_EQUALSTR, output_file)
                print_outfile(colorize(f'{"ID":<38}{"Entry":<26}{"Exit":<24}{"Symbol":<16}{"Direct":<9}{"EntryPrice":<15}{"ExitPrice":<17}{"PnL":<16}{"quantity":<14}\n', "magenta"), output_file)
                print_outfile(BL_EQUALSTR, output_file)
                passes += 1
            print_outfile(
                f'{trade_dict["trade_id"][tid_slice:]:<38}'
                f'{entry_time[0:16]:<26}'
                f'{exit_time[0:16]:<10}'
                f'{colorize(f"\t{trade_dict["symbol"]:<10}", "cyan")}'
                f'\t{trade_dict["direction"]:<5}'
                f'\t{float(trade_dict["entry_price"]):>11.2f}'
                f'\t{float(trade_dict["exit_price"]):>9.2f}'
                f'\t{col_pnl}\t{int(trade_dict["quantity"]):>3}\t\n', output_file
            )
    # Select the best and worst complete symbol totals after every matching
    # trade has been accumulated. This also works when every symbol is a loss
    # or every symbol is a profit, without relying on sentinel values.
    # Print  Tttle , header graphics and column headers
 
    if sym_total_pnl:
        high_symbol, high_total = max(
            sym_total_pnl.items(), key=lambda item: item[1]
        )
        low_symbol, low_total = min(
            sym_total_pnl.items(), key=lambda item: item[1]
        )
        high_sym = {"symbol": high_symbol, "total": high_total}
        low_sym = {"symbol": low_symbol, "total": low_total}
    else:
        high_sym = {"symbol": "None", "total": 0.0}
        low_sym = {"symbol": "None", "total": 0.0}
 
    # Prevent div by zero excetions then calculate avg wins and losses
    if tot_winners == 0:
        avg_wins = -1
    else:
        avg_wins = (tot_wins / tot_winners) 
    if tot_losers == 0:
        avg_loss = -1
    else:
        avg_loss = (tot_losses / tot_losers)
    if trade_count == 0:
        trade_count = -1
    # Prepare our return dictionary of results 
    ret_dict = {}
    ret_dict["loss_pct"]  = colorize(f"{(tot_losers  / trade_count) * 100:.0f}", "red")
    ret_dict["win_pct"]  = colorize(f"{(tot_winners  / trade_count) * 100:>3.0f}", "green")
    ret_dict["trade_count"] = f"{trade_count:<14}"
  
    
    # Properly color the Tot PnL red for neg, green for pos
    if total_pnl >= 0:
        ret_dict["total_pnl"] = colorize(f"{total_pnl:<19.2f}", "green")
    else:
        ret_dict["total_pnl"] = colorize(f"{total_pnl:<19.2f}", "red")

    ret_dict["max_win"] = colorize(f"{max_win:<14.2f}", "green")
    ret_dict["max_loss"] = colorize(f"{max_loss:>3.2f}", "red")
    ret_dict["avg_wins"] = colorize(f"{avg_wins:<14.2f}", "green")
    ret_dict["avg_loss"] = colorize(f"{avg_loss:<19.2f}", "red")
    ret_dict["tot_wins"] =  colorize(f"{tot_winners:>3}", "green")
    ret_dict["tot_losers"] = colorize(f"{tot_losers:<11}", "red")
    ret_dict["high_sym"] = high_sym
    ret_dict["low_sym"] = low_sym
    # Pass back our pre color formatted dictionary of results
    return(ret_dict)


# ...existing code...
def print_col_headers(trades_lst):
    """
    Prints the list of column headers in the trades table given switch -N
    """
    if not trades_lst:
        return

    final_list = ""
    local_counter = 1

    # Use only one row's keys; all rows have the same columns
    headers = list(trades_lst[0].keys())

    for my_key in headers:
        final_list += f"{my_key:<20}"

        if local_counter % 5 == 0:
            print(f'{colorize(final_list, "blue")}')
            final_list = ""

        local_counter += 1
    # If num of colums not disivble by 5 print the remaining odd headers
    if final_list:
        print(f'{colorize(final_list, "blue")}')
# ...existing code...

def build_hdr_list(trades_lst2):
    """Collect unique column header names from all rows, preserving order."""
    # (Previous bug: returned repeated list due to nested loop — fixed by using single comprehension)
    seen = set()
    headers = []

    for row in trades_lst2:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                headers.append(key)

    return headers

def format_group_summary(res_dict):
    """ color and format the results dictionary """
    lhigh_tot = colorize(f'{res_dict["high_sym"]["total"]:.2f}', "green")
    llow_tot = colorize(f'{res_dict["low_sym"]["total"]:.2f}', "red")
    lhigh_sym = colorize(f'{res_dict["high_sym"]["symbol"]}', 'cyan')
    llow_sym = colorize(f'{res_dict["low_sym"]["symbol"]}', 'cyan')

    return (
        f'{"Total Trades:":>16} {res_dict["trade_count"]}    {"Total P&L:":<13}   {res_dict["total_pnl"]}{"Max Win:":<10} {res_dict["max_win"]}'
        f'{"Max Loss:":>10}{"":<5}{res_dict["max_loss"]}\n'
        f'{"Avg Win:":>16} {res_dict["avg_wins"]}     {"Avg Loss:":<13}  {res_dict["avg_loss"]}'
        f'{"":<4}W/L: {res_dict["tot_wins"]}/{res_dict["tot_losers"]}{"":<6}W/L%:{"":<5}{res_dict["win_pct"]}%/{res_dict["loss_pct"]}%\n'
        f'{"High Sym:":>16} {lhigh_sym:>10} ({lhigh_tot:>16})'
        f'{"Low Sym:":>13} {llow_sym} ({llow_tot })\n'
    )


def numeric_value(value):
    """
    Return a number only when the whole value is a plain integer or decimal.

    This deliberately leaves dates/times, IDs, and mixed letter/number values
    as text. Numeric values returned directly by sqlite are accepted too.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    value_text = str(value).strip()
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", value_text):
        return None
    return float(value_text)


def value_in_selected(actual, selected):
    """
    Compare a DB value against one or more CLI-supplied strings.

    argparse always supplies strings. Plain numeric values are compared as
    numbers for every field, while dates/times, IDs, and mixed values stay as
    text. A selected numeric value may start with !=, <=, >=, <, or >.
    With no operator, equality is the default.
    """
    actual_str = str(actual)
    actual_num = numeric_value(actual)

    for val in selected:
        val = val.strip()
        for op in ("!=", "<=", ">=", "<", ">"):
            if val.startswith(op):
                if actual_num is None:
                    break
                bound = numeric_value(val[len(op):])
                if bound is None:
                    break
                if op == "!=" and actual_num != bound:
                    return True
                if op == "<=" and actual_num <= bound:
                    return True
                if op == ">=" and actual_num >= bound:
                    return True
                if op == "<" and actual_num < bound:
                    return True
                if op == ">" and actual_num > bound:
                    return True
                break
        else:
            if actual_str == val:
                return True
            selected_num = numeric_value(val)
            if actual_num is not None and selected_num is not None:
                if actual_num == selected_num:
                    return True
    return False


def print_group_summary(group_name, trade_list, key, output_file,start_date,end_date):
    """ Print this grups summary list """
    res_dict = proc_dict(trade_list, group_name, key, output_file,start_date,end_date)
    if int(res_dict["trade_count"]) >= 1:
        print_outfile(BL_EQUALSTR, output_file)
        print_outfile(format_group_summary(res_dict), output_file)
        print_outfile(BL_EQUALSTR + "\n\n", output_file)

def main():

    # Standard library approach to handle Windows initialization safely
    if sys.platform == "win32":
        os.system("") # Crucial trick: This forces the Windows terminal engine to enable ANSI parsing natively

    output_file = ""

    default_key_list = ["strategy_name", "symbol", "exit_reason", "quantity", "broker_order_id"]
    # Connect to DB and load the trades table into the trades_list dictionary

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
  trades_list.py -k entry_price -1 ">=40000"
  trades_list.py -k strategy_name -1 ALL -o report.txt
  trades_list.py -N
""",
        formatter_class=wide_formatter,
    )

    parser.add_argument("-o", "--outfile", metavar="", help="\tpath and name of output file")
    parser.add_argument("-op", "--open", action='store_true', help='List open trades instead of closed')
    parser.add_argument("-csv", "--csv", action='store_true', help="\tuse to have output file be a csv")
        
    parser.add_argument("-1", "--list1", metavar="",
            help="ALL or comma-separated values for the first key; numeric values also accept !=, <, >, <=, >= (quote these in PowerShell)"
    )
    parser.add_argument("-2", "--list2", metavar="",
            help="ALL or a <Comma seperated list of valuws found in second provided key>"
    )
    parser.add_argument("-3", "--list3", metavar="",
            help="ALL or a <Comma seperated list of valuws found in third provided key>"
    )
    parser.add_argument("-4", "--list4", metavar="",
            help="ALL or a <Comma seperated list of valuws found in fourth provided key>"
    )
    parser.add_argument("-5", "--list5", metavar="",
            help="ALL or a <Comma seperated list of valuws found in fifth provided key>"
    )
    parser.add_argument("-s", "--start", metavar="",
            help="Starting date and time. Format YYYY:MM:DDTHH:MM T being a litteral T"
    )
    parser.add_argument("-e", "--end", metavar="",
            help="Ending date and time. Format YYYY:MM:DDTHH:MM T being a litteral T"
    )               
    parser.add_argument("-k", "--key", metavar="",
            help="ALL or a <Comma seperated list of DB table keys to index and search>"
    )
    parser.add_argument("-N", "--Names", action='store_true',
            help="If given, prints a list of all trade table key names you can use"
    )
    parser.add_argument("-A", "--and", dest="and_filter", action='store_true',
            help="If given with multiple --key values, require trades to match ALL selected key/value filters at once (e.g. symbol=MSFT AND direction=long) instead of printing a separate breakdown per key"
    )
    parser.add_argument("-E", "--Ext", action='store_true',
            help="Extended Trade Id , default is shortened Id (Useful when you need the full trade Id for a lookup)"
    )

    args = parser.parse_args()
    global csv_true
    global extended
 
    csv_true = args.csv if args.csv else False
    
    extended = args.Ext if args.Ext else False
    
    mode = 'open' if args.open else 'closed'
    
    conn = connect()
    if mode == 'closed':
        try:
            trades_list = get_closed_trades(conn)
            conn.close()
        except sqlite3.OperationalError as e:
            print(f'Database error: {e}')
            conn.close()
            sys.exit(1)
    else:
        try:
            trades_list = get_open_trades(conn)
            conn.close()
        except sqlite3.OperationalError as e:
            print(f'Database error: {e}')
            conn.close()
            sys.exit(1)
                
    if not trades_list:
        print('No closed trades found.') if (mode == "closed") else print('No open trades found.')
        conn.close()
        return
    
    hdr_list = build_hdr_list(trades_list)

    
    if args.Names:
        print_col_headers(trades_list)
        sys.exit(2)
    DEF_START_DATE = "1980-01-01T00:00"
    DEF_END_DATE = "4050-01-01T00:00"
    
    start_date = args.start if args.start else DEF_START_DATE
    end_date = args.end if args.end else DEF_END_DATE
    if args.start and (date_check(start_date) == False):
        print(f'Invalid start date. use format YYYY-MM-DDTHH:MM')
        sys.exit(4)
    
    if args.end and (date_check(end_date) == False):
        print(f'Invalid end date. use format YYYY-MM-DDTHH:MM')
        sys.exit(4)

    date_range_given = (start_date != DEF_START_DATE or end_date != DEF_END_DATE) 

    output_file = args.outfile 
    if csv_true:
        output_file, extension = output_file.split(".")
        
    # Build a list of list options skipping those not given
    list_values = [
        args.list1.split(",") if args.list1 else [],
        args.list2.split(",") if args.list2 else [],
        args.list3.split(",") if args.list3 else [],
        args.list4.split(",") if args.list4 else [],
        args.list5.split(",") if args.list5 else [],
    ]

    key_list = args.key.split(",") if args.key else []
        

    if len(key_list) > 5:
        print("\nError: maximum of 5 keys is supported.\n")
        sys.exit(1)

    # Verify every key value input is valid
    if date_range_given and (not any(list_values)):
        for j in range(5):
            list_values[j].append("ALL")
        
    if date_range_given and len(key_list) < 1:
        key_list = default_key_list

    if ((not len(list_values)) or (not len(key_list))) and (not date_range_given):
         parser.print_help()
         parser.exit(
             2,
             "\nError: provide --key key1,key2,... and at least one --list option per key given.\n"
         )
          
    for key_name in key_list:
        if key_name not in hdr_list:
            print(f'\nError: {key_name} is not a valid entry. please run with -N to see a list of valid choices\n')
            sys.exit()

    if (not args.Names) and (len(key_list) < 1):
        print(f'\nError: Please provide at least 1 key , separated by a ,\n')
        sys.exit()

    # -A/--and: one combined report where a trade must match every selected
    # key/value filter at once (symbol=MSFT AND direction=long), instead of
    # the default independent per-key breakdown below.
    if args.and_filter and len(key_list) > 1:
        combined_list = []
        for trade in trades_list:
            matches_all = True
            for key_name, selected in zip(key_list, list_values):
                if not selected:
                    continue
                if selected[0] == "ALL":
                    continue
                if not value_in_selected(trade[key_name], selected):
                    matches_all = False
                    break
            if matches_all:
                combined_list.append(copy.deepcopy(trade))

        label_parts = [
            f'{key_name}={",".join(selected)}'
            for key_name, selected in zip(key_list, list_values) if selected
        ]
        combined_label = " & ".join(label_parts) if label_parts else "ALL"
        print_group_summary(combined_label, combined_list, "ALL", output_file, start_date, end_date)
        return

    # Build one generic list of grouped trade dictionaries
    dict_of_trades = []

    for idx, key_name in enumerate(key_list):
        grouped_trades = {}
        for trade in trades_list:
            group_value = trade[key_name]
            grouped_trades.setdefault(group_value, []).append(copy.deepcopy(trade))

        dict_of_trades.append({
            "key": key_name,
            "selected": list_values[idx] if idx < len(list_values) else [],
            "groups": grouped_trades,
        })

    for trade_group in dict_of_trades:
        key_name = trade_group["key"]
        selected_values = trade_group["selected"]
        grouped_trades = trade_group["groups"]

        for group_name, trade_list in grouped_trades.items():
            if not selected_values:
                continue

            if selected_values[0] == "ALL" or value_in_selected(group_name, selected_values):
                print_group_summary(group_name, trade_list, key_name, output_file,start_date, end_date)

if __name__ == "__main__":
    main()
# ...existing code...