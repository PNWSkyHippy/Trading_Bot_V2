import csv
import argparse
import sys
cur_balance = 0
with open(sys.argv[1], newline="", encoding="utf-8-sig") as file:
    rows = csv.reader(file)
    next(rows)  # Skip the column headings.
    balances =  [float(row[5].replace("$", "").replace(",", "")) for row in rows if row]
    total_balance = sum(balances)
    num_balances = len(balances)
    if num_balances:
        avg_balance = total_balance / num_balances
    else:
        avg_balance = 0
    cur_balance = balances[-1]

#    highest_row = max(rows, key=lambda row: float(row[5]))
max_drawdown = max(balances) - 2500        
drawdwn_remains = cur_balance - max_drawdown
print(f"Highest recorded balance: ${max(balances):,.2f}\nLowest recorded balance: ${min(balances):,.2f}")
print(f"Total Balancees: ${total_balance:,.2f}\nAverage balance: ${avg_balance:,.2f}\nNum balancse {num_balances}")
print(f"Curent Balance is: {cur_balance}")
print(f"Max Drawdown is {max_drawdown}\nDrawdow Remaining  is {drawdwn_remains:.2f}")

