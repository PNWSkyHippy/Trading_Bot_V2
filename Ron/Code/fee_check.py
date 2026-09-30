# scripts\fee_check.py

trade_entry = 0
trade_exit = 0
trade_qty = 0
trade_fees = 0.62
total_entry = 0.0
total_exit = 0.0
total_fees = 0.0
gross_PnL = 0.0
net_PnL = 0.0
trade_type = -1
trade_direction = -1


# Error check an inputted number, ie > 0 and actually a number
def get_positive_float(prompt):
    while True:
        try:
            value = float(input(prompt))
            if value > 0:
                return value
            print("Must be greater than zero.")
        except ValueError:
            print("Invalid — please enter a number.")


while True:
    # Get choice for Stocks or crypto , until a
    # valid entry is received
    try:
        trade_type = int(input("(1) for Crypto or (2) for Stocks: "))
        if trade_type in range(1, 3):
            break  # valid — exit the loop
        print("Please enter 1 or 2.")
    except ValueError:
        print("That's not a number. Please enter 1 or 2.")

#  set proper tax rate based on choice , crypto or stocks
if trade_type == 2:
    trade_fees = 0.02
else:
    trade_fees = 0.62


while True:  # Get choice for Trade direction, long or short
    try:
        trade_direction = int(
            input("Trade direction (1) for long, " + "(2) for short): ")
        )
        if trade_direction in range(1, 3):
            break  # valid — exit the loop
        print("Please enter 1 or 2.")
    except ValueError:
        print("That's not a number. Please enter 1 or 2.")


# Gather trade details from the user
trade_entry = get_positive_float("Enter the trade entry price: ")
trade_exit = get_positive_float("Enter the trade exit price: ")
trade_qty = get_positive_float("Enter the trade quantity: ")


# echo entered values back to user
print(
    f"Entry Value: {trade_entry}, Exit Value: {trade_exit}," + f"Quantity: {trade_qty}"
)

# Calculate the cost of entry  exit, and fees and echo result to the user
total_entry = trade_entry * trade_qty
total_exit = trade_exit * trade_qty
total_fees = total_entry * trade_fees / 100
print(
    f"Total Entry: {total_entry:.2f}, Total Exit: {total_exit:.2f}, "
    + f"Total Fees: {total_fees:.2f}"
)

# Calculate Gross profit based on a short or a long trade
if trade_direction == 1:
    gross_PnL = total_exit - total_entry
elif trade_direction == 2:
    gross_PnL = total_entry - total_exit

# a calculate net profit and echo to the user
net_PnL = gross_PnL - total_fees
print(
    f"Gross P&L: {gross_PnL:.2f}, Net P&L: {net_PnL:.2f}, Total Fees: "
    + f"{total_fees:.2f}"
)
