# position_sizer.py


def get_user_input(prompt):
    while (
        True
    ):  # Get inputf rom the user until a valid entry is received
        try:
            value = float(input(f"{prompt}"))
            if value > 0:
                return value
            print(
                "Value must be greater than zero. Please try again."
            )  # valid — exit the loop
        except ValueError:
            print(
                "Invalid input. Please enter a numeric value."
            )


account_size = get_user_input(
    "Enter the account size: $"
)
risk_pct_per_trade = get_user_input(
    "Enter the percentage to risk per trade: %"
)
stop_distance_pct = get_user_input(
    "Enter the stop distance percentage: %"
)


max_loss = account_size * (
    risk_pct_per_trade / 100
)
max_position = max_loss / (
    stop_distance_pct / 100
)

LABEL_W = 26
VALUE_W = 24
BORDER = "=" * (
    LABEL_W + VALUE_W + 4
)  # +4 for "| " and " |"
DIVIDER = f"|{'=' * (LABEL_W + VALUE_W + 2)}|"


def row(label, value):
    return f"| {label:<{LABEL_W}}{value:>{VALUE_W}} |"


print(
    f"\n{BORDER}\n"
    f"{row('Account size:', f'${account_size:,.2f}')}\n"
    f"{row('Risk per trade:', f'{risk_pct_per_trade:.2f}%')}\n"
    f"{row('Stop distance:', f'{stop_distance_pct:.2f}%')}\n"
    f"{DIVIDER}\n"
    f"{row('Maximum position size:', f'${max_position:,.2f}')}\n"
    f"{row('Maximum loss:', f'${max_loss:,.2f}')}\n"
    f"{BORDER}"
)
