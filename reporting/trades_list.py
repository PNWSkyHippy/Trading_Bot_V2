
import sqlite3
import sys
import os
import copy
import argparse
from pathlib import Path

Soutput_file = ""

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
    try:
        conn = sqlite3.connect(DB_PATH)
    except sqlite3.OperationalError as e:
        print(f'Database error: {DB_PATH}')
        sys.exit()
    conn.row_factory = sqlite3.Row
    return conn

EQUALSTR = "=" * 50 + "\n"


def get_closed_trades(conn):
    c = conn.cursor()
    c.execute(
        'SELECT * FROM trades WHERE status=? ORDER BY exit_time DESC',
        ('closed',)
    )
    return [dict(r) for r in c.fetchall()]

def proc_strat(loc_trade_list, strat_name, output_file):
        """ Process the provided dictionary of trades """
    counter = 0
    total_pnl = 0
    trade_count = 0
    print_outfile(f'List of {strat_name} Trades\n', output_file)
    print_outfile(EQUALSTR, output_file)
    counter = 1
    prompt_one = ""
    prompt_two = ""
    prompt_three = ""
    prompt_four = ""
    prompt_five = ""
    print_outfile(f'Id:\t\tEntry\t\t\tExit\t\t\tSymbol\t\tDirct\tEntry Price\tExit Price\t PnL\n', output_file)
    for trade_dict in loc_trade_list:
        if trade_dict['strategy_name'] == strat_name  or strat_name == "ALL":
            total_pnl += trade_dict["pnl"]
            trade_count += 1
            if counter % 3 == 0:
                print_outfile(
			f'{trade_dict["trade_id"][-12:]:<7}'
                        f'\t{trade_dict["entry_time"][0:16]:<10}'
                        f'\t{trade_dict["exit_time"][0:16]:<10}'
                        f'\t{trade_dict["symbol"]:<10}'
                        f'\t{trade_dict["direction"]:<5}'
                        f'\t{float(trade_dict["entry_price"]):<8.5f}'
                        f'\t{float(trade_dict["exit_price"]):<8.5f}  '
                        f'\t{trade_dict["pnl"]: 8.2f}\t\n', output_file
                    )
                counter += 1
            else:
                print_outfile(
			f'{trade_dict["trade_id"][-12:]:<7}' +
                        f'\t{trade_dict["entry_time"][0:16]:<10}' +
                        f'\t{trade_dict["exit_time"][0:16]:<10}' +
                        f'\t{trade_dict["symbol"]:<10}' +
                        f'\t{trade_dict["direction"]:<5}' +
                        f'\t{trade_dict["entry_price"]:<8.5f}' +
                        f'\t{trade_dict["exit_price"]:<8.5f}' +
                        f'\t{trade_dict["pnl"]: 8.2f}\t\n', output_file
                    )
                counter += 1

    return trade_count, total_pnl

def proc_symbols(loc_trade_list, symbol_name, output_file):
    counter = 1
    total_pnl = 0
    trade_count = 0
    print_outfile(f'List of {symbol_name} Trades\n', output_file)
    print_outfile(EQUALSTR, output_file)
    print_outfile(f'Id:\t\tEntry\t\t\tExit\t\t\tSymbol\t\tDirct\tEntry Price\tExit Price\t PnL\n', output_file)
    for trade_dict in loc_trade_list:
        if trade_dict['symbol'] == symbol_name or symbol_name == "ALL":
            total_pnl += trade_dict["pnl"]
            trade_count += 1
            if counter % 3 == 0:
                print_outfile(
			f'{trade_dict["trade_id"][-12:]:<7}'
                        f'\t{trade_dict["entry_time"][0:16]:<10}'
                        f'\t{trade_dict["exit_time"][0:16]:<10}'
                        f'\t{trade_dict["symbol"]:<10}'
                        f'\t{trade_dict["direction"]:<5}'
                        f'\t{float(trade_dict["entry_price"]):<8.5f}'
                        f'\t{float(trade_dict["exit_price"]):<8.5f}  '
                        f'\t{trade_dict["pnl"]: 8.2f}\t\n', output_file
                    )
                counter += 1
            else:
                print_outfile(
			f'{trade_dict["trade_id"][-12:]:<7}' +
                        f'\t{trade_dict["entry_time"][0:16]:<10}' +
                        f'\t{trade_dict["exit_time"][0:16]:<10}' +
                        f'\t{trade_dict["symbol"]:<10}' +
                        f'\t{trade_dict["direction"]:<5}' +
                        f'\t{trade_dict["entry_price"]:<8.5f}' +
                        f'\t{trade_dict["exit_price"]:<8.5f}' +
                        f'\t{trade_dict["pnl"]: 8.2f}\t\n', output_file
                    )
                counter += 1


    return trade_count, total_pnl


def main():

    conn = connect()
    try:
        trades_list = get_closed_trades(conn)
        conn.close()
    except sqlite3.OperationalError as e:
        print(f'Database error: {e}')
        conn.close()
        sys.exit(1)

    parser = argparse.ArgumentParser(description="List PnL  based on search criteria")
    parser.add_argument("-o","--outfile", help="<report filename>")
    parser.add_argument(
            "-s","--strategy", 
            help="--strategy ALL or a <comma seperated list of strategies>"
    )
    parser.add_argument(
            "-t", "--ticker", 
            help="--ticker ALL or a <Comma seperated list if stock/crypto tickers>"
    )
    args = parser.parse_args()
    if not args.strategy and not args.ticker:
        parser.print_help()
        parser.exit(
            2,
            "\nError: provide --strategy, --ticker, or both.\n"
        )


    output_file = args.outfile
    strat_list = args.strategy.split(",") if args.strategy else []
    ticker_list = args.ticker.split(",") if args.ticker else []

    dict_of_trades_by_strat = {}
    for trade in trades_list:
        strat_name = trade["strategy_name"]
        dict_of_trades_by_strat.setdefault(strat_name, []).append(copy.deepcopy(trade)) # Deep copy of trade

    for strat in dict_of_trades_by_strat:
        # "fetch the list of dicts" — this is what you were missing
        trade_list = dict_of_trades_by_strat[strat]
        strat_name = trade_list[0]["strategy_name"]

        if (len(strat_list) >= 1) and ((strat_name in strat_list) or (strat_list[0] == "ALL")):
             trade_count, total_pnl = proc_strat(trade_list, strat_name, output_file)
             print_outfile(EQUALSTR, output_file)
             print_outfile(f'Total Trades:  {trade_count}\tTotal P&L: {total_pnl:.2f}\n', output_file)
             print_outfile(EQUALSTR + "\n\n", output_file)

    dict_of_trades_by_symbol = {}
    for trade in trades_list:
        symbol_name = trade["symbol"]
        dict_of_trades_by_symbol.setdefault(symbol_name, []).append(trade)


    for symbol in dict_of_trades_by_symbol:


        trade_list = dict_of_trades_by_symbol[symbol]
        symbol_name = trade_list[0]["symbol"]
        if (len(ticker_list) >= 1) and ((symbol_name in ticker_list) or (ticker_list[0] == "ALL")):
            trade_count, total_pnl = proc_symbols(trade_list, symbol_name, output_file)
            print_outfile(EQUALSTR, output_file)
            print_outfile(f'Total Trades:  {trade_count}\tTotal P&L: {total_pnl:.2f}\n', output_file)
            print_outfile(EQUALSTR + "\n\n", output_file)



if __name__ == "__main__":
  main()

