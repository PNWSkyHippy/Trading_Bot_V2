users = [  # list: access by numeric position
    {
        "name": "Ron",
        "score": 95,
    },  # dictionary: access by key
    {"name": "Sam", "score": 88},
]

print(
    "List of dictioaries\n"
    + "users = [\n"  # list: access by numeric position
    + '\t{"name":  "Ron", "score": 95},\n'  # dictionary: access by key
    + '\t{"name": "Sam", "score": 88},\n'
    + "]\n"
)


print(
    f"users[0] = {users[0]}"
)  # first dictionary
print(
    f'users[0]["name"] = {users[0]["name"]}'
)  # "Ron"
print(
    f'users[1]["score"] = {users[1]["score"]}'
)  # 88


# And a dictionary containing lists:
classes = {
    "students": ["Ron", "Sam"],
    "grades": [95, 88],
}

print(
    "\n\n#And a dictionary containing lists:\n"
    + "classes = {\n"
    + '\t"students": ["Ron", "Sam"],\n'
    + '\t"grades": [95, 88],\n'
    + "}"
)


print(
    f'classes["students"][0] = {classes["students"][0]}\n'
)  # "Ron"

# A good practice project would be a tiny paper-trade journal: a list of trade dictionaries, with functions to add trades
# and calculate total P&L. That directly reinforces what you learned using data you already understand extremely well.
# Use print() after every operation so you can see what each expression returns:

trades = [
    {
        "symbol": "BTC/USD",
        "pnl": 25.50,
        "won": True,
    },
    {
        "symbol": "ETH/USD",
        "pnl": -12.00,
        "won": False,
    },
]

print("List of dictionary objects")

print(
    "trades = [\n"
    + '\t{"symbol": "BTC/USD", "pnl": 25.50, "won": True},\n'
    + '\t{"symbol": "ETH/USD", "pnl": -12.00, "won": False},\n'
    + "]\n"
)


for trade in trades:
    print(
        f"trade['symbol'] = {trade['symbol']} trade['pnl'] = {trade['pnl']}"
    )
    print(trade["symbol"], trade["pnl"])

print(f"trades = {trades}\n")
print(f"trades[0] = {trades[0]}\n")
print(
    f'trades[0]["symbol"] = {trades[0]["symbol"]}\n\n'
)


for trade in trades:
    if trade["symbol"] == "ETH/USD":
        print(
            f'"Found:", trade) = "Found:", {trade}'
        )

winners = [
    trade for trade in trades if trade["won"]
]
print(
    'winners = [trade for trade in trades if trade["won"]]'
)
print(f"Winners:  {winners}")


print(
    'total_pnl = sum(trade["pnl"] for trade in trades)\n'
    + '\tprint("Total P&L:", total_pnl\n)'
    + "======================================================\n\n"
)

print(
    'total_pnl = sum(trade["pnl"] for trade in trades)'
)
total_pnl = sum(trade["pnl"] for trade in trades)
print("Total P&L:\n\n", total_pnl)
# Then deliberately break expressions—try trades["symbol"] or trades[0][0]—and study the errors. Understanding why those fail will
# drive home the distinction between numeric list indexes and dictionary keys very quickly.

my_list = [1, 2, 3]
print(
    "my_list = {my_list}\ntype(my_list) = {type(my_list)}"
)
print("for nums in my_list:")
for nums in my_list:
    print(f"nums = {nums}")

my_dict = {"a": 1, "b": 2, "c": 3}
print(
    f"\nmy_dict = {my_dict}\ntype(my_dict) = {type(my_dict)}"
)
print(
    "for my_keys, my_values in my_dict.items():"
)
for my_keys, my_values in my_dict.items():
    print(
        f"my_keys = {my_keys} my_values = {my_values}"
    )


my_list_of_dicts = [{"a": 1}, {"b": 2}, {"c": 3}]
print(
    f"\nmy_list_of_dicts = {my_list_of_dicts}\ntype(my_list_of_dicts) = {type(my_list_of_dicts)}"
)
print("for trade in my_list_of_dicts:")
for trade in my_list_of_dicts:
    print(f"trade = {trade}")
    for my_keys, my_values in trade.items():
        print(
            f"my_keys = {my_keys} my_values = {my_values}"
        )

my_dict_of_lists = {
    "a": [1, 2, 3],
    "b": [1, 2, 4],
    "c": [3, 2, 1],
}
print(
    f"\nmy_dict_of_lists = {my_dict_of_lists}\ntype(my_dict_of_lists) = {type(my_dict_of_lists)}\n"
)
print(f"my_dict = {my_dict} my_dict = s[my_dict]")
for my_dict in my_dict_of_lists:
    for my_values in my_dict_of_lists[my_dict]:
        print(f"my_values = {my_values}")


my_dict_of_dicts = {
    "a": {"x": 1},
    "b": {"y": 2},
    "c": {"z": 3},
}
print(
    f"my_dict_of_dicts = {my_dict_of_dicts}\ntype(my_dict_of_dicts) = {type(my_dict_of_dicts)}\n"
)

my_list_of_lists_of_dicts = [
    [{"a": 1}],
    [{"b": 2}],
    [{"c": 3}],
]
print(
    f"my_list_of_lists_of_dicts = {my_list_of_lists_of_dicts}\ntype(my_list_of_lists_of_dicts) = "
    f"{type(my_list_of_lists_of_dicts)}\n"
)
print(
    f"my_list_of_lists_of_dicts[0] = {my_list_of_lists_of_dicts[0]}\ntype(my_list_of_lists_of_dicts[0]) "
    f"= {type(my_list_of_lists_of_dicts[0])}\n"
)
print(
    f"my_list_of_lists_of_dicts[0][0] = {my_list_of_lists_of_dicts[0][0]}\ntype(my_list_of_lists_of_dicts[0][0])"
    f" = {type(my_list_of_lists_of_dicts[0][0])}\n"
)


my_dict_of_lists_of_dicts = {
    "a": [{"x": 1}],
    "b": [{"y": 2}],
    "c": [{"z": 3}],
}
print(
    "my_dict_of_lists_of_dicts = {my_dict_of_lists_of_dicts}\ntype(my_dict_of_lists_of_dicts) = {type(my_dict_of_lists_of_dicts)}\n"
    + f'type(my_dict_of_lists_of_dicts["a"]) = {type(my_dict_of_lists_of_dicts["a"])}\n'
    + f'type(my_dict_of_lists_of_dicts["a"][0]) = {type(my_dict_of_lists_of_dicts["a"][0])}\n'
    + f'my_dict_of_lists_of_dicts["a"][0] = {my_dict_of_lists_of_dicts["a"][0]}\n'
)


my_dict_of_lists_of_lists_of_dicts = {
    "a": {"x": [1]},
    "b": {"y": [2]},
    "c": {"z": [3]},
}
print(
    "my_dict_of_lists_of_lists_of_dicts = {my_dict_of_lists_of_lists_of_dicts}\ntype(my_dict_of_lists_of_"
    + f"lists_of_dicts) = {type(my_dict_of_lists_of_lists_of_dicts)}\n"
    + f'type(my_dict_of_lists_of_lists_of_dicts["a"]) = {type(my_dict_of_lists_of_lists_of_dicts["a"])}\n'  # dict
    + f'type(my_dict_of_lists_of_lists_of_dicts["a"]["x"]) = {type(my_dict_of_lists_of_lists_of_dicts["a"]["x"])}\n'  # list
    + f'type(my_dict_of_lists_of_lists_of_dicts["a"]["x"][0]) = {type(my_dict_of_lists_of_lists_of_dicts["a"]["x"][0])}'  # int
)
