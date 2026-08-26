import argparse


def basic():
    # =====================================================================
    # 1. BASIC LISTS (Arrays)
    # =====================================================================
    log_step("\n--- 1. BASIC LISTS ---")

    # Creation
    basic_list = ["131", "798", "465", "0"]
    log_step(
        f"1. Created basic_list = {basic_list}\n"
    )

    # Adding (Append)
    log_step('basic_list.append("989")')
    basic_list.append("989")
    log_step(
        f"2. After append '989' = {basic_list}\n"
    )

    # Removing
    log_step(
        "removed_item = basic_list.pop(3) # Removes by index (removes '0')"
    )
    removed_item = basic_list.pop(
        3
    )  # Removes by index (removes '0')
    log_step(
        f"3. After pop(3) [removed '{removed_item}'] = {basic_list}\n"
    )

    basic_list.remove("798")  # Removes by value
    log_step('basic_list.remove("798")')  # Re
    log_step(
        f"4. After remove('798') = {basic_list}\n"
    )

    # Searching
    search_val = "465"
    if search_val in basic_list:
        idx = basic_list.index(search_val)
    log_step('search_val = "465"')
    log_step("if search_val in basic_list:")
    log_step(
        "\tidx = basic_list.index(search_val)"
    )
    log_step(
        f"5. Found '{search_val}' at index {idx}\n"
    )

    # Iteration & In-place String Sorting (Your example logic)
    log_step("for i in range(len(basic_list)):")
    log_step(
        "\tbasic_list[i] = str_sort(basic_list[i])"
    )
    for i in range(len(basic_list)):
        basic_list[i] = str_sort(basic_list[i])
    log_step(
        f"6. Each inner string sorted = {basic_list}\n"
    )

    # Sorting the List itself
    log_step("basic_list.sort()")
    basic_list.sort()
    log_step(
        f"7. Final basic_list sorted = {basic_list}\n"
    )


def save_log_to_file(filename, content_list):
    """Takes a list of string lines and writes them to a text file."""
    try:
        with open(
            filename, "w", encoding="utf-8"
        ) as file:
            for line in content_list:
                file.write(line + "\n")
        print(
            f"\n[SUCCESS] Reference guide saved to '{filename}'"
        )
    except IOError as e:
        print(
            f"\n[ERROR] Could not write to file: {e}"
        )


cheat_sheet_lines = []


# 2. A helper to print and store lines simultaneously
def log_step(text):
    print(text)  # Prints to your VS Code terminal
    cheat_sheet_lines.append(
        text
    )  # Saves it for the text file


def quickref():
    log_step(
        "=================================================="
    )
    log_step(
        "               QUICK CHOICE GUIDE                 "
    )
    log_step(
        "=================================================="
    )
    log_step("LIST vs DICT")
    log_step("")
    log_step(
        "[] = LIST = ordered, index-based, good for sequences"
    )
    log_step(
        "    symbols = ['AAPL', 'MSFT', 'NVDA']"
    )
    log_step("    symbols[0] -> 'AAPL'")
    log_step("    symbols.append('AMZN')")
    log_step("    symbols.sort()")
    log_step("")
    log_step(
        "{} = DICT = key-based, fast lookup by name"
    )
    log_step(
        "    trade = {'symbol': 'AAPL', 'pnl': 250.00}"
    )
    log_step("    trade['symbol'] -> 'AAPL'")
    log_step("    trade['pnl'] = 500.00")
    log_step("    trade['new_key'] = value")
    log_step("")
    log_step("When to pick which:")
    log_step(
        "- use a list when you want order, iteration, or a sequence"
    )
    log_step(
        "- use a dict when you want direct lookup by name/key"
    )
    log_step(
        "- use list of dicts when you store many records"
    )
    log_step(
        "- use dict of lists when you group records by category"
    )
    log_step("")
    log_step("BIG-O MEMORY RULES")
    log_step("- one loop -> O(n)")
    log_step("- loop inside loop -> O(n^2)")
    log_step(
        "- loop inside loop inside loop -> O(n^3)"
    )
    log_step("- list search by value -> O(n)")
    log_step(
        "- dict lookup by key -> O(1) average"
    )
    log_step("- factorial recursion -> O(n)")
    log_step(
        "- naive Fibonacci recursion -> O(2^n)"
    )
    log_step(
        "=================================================="
    )
    log_step("")


def listsdicts():
    # =====================================================================
    # 2. LISTS OF DICTIONARIES
    # =====================================================================
    log_step("\n--- 2. LISTS OF DICTIONARIES ---")

    # Creation
    list_of_dicts = [
        {"item": "Tires", "price": 499.00},
        {"item": "Air", "price": 5.00},
    ]
    log_step(
        f"1. Created list_of_dicts = {list_of_dicts}\n"
    )

    # Adding
    log_step(
        'list_of_dicts.append({"item": "Car", "price": 15000.00})'
    )
    list_of_dicts.append(
        {"item": "Car", "price": 15000.00}
    )
    log_step(
        f"2. After append dict = {list_of_dicts}\n"
    )

    # Removing
    log_step(
        'del list_of_dicts[1]  # Removes {"item": "Air", "price": 5.00}'
    )
    del list_of_dicts[
        1
    ]  # Removes {"item": "Air", "price": 5.00}
    log_step(
        f"3. After deleting index 1 = {list_of_dicts}\n"
    )

    # Searching
    log_step('search_item = "Car"')
    log_step("for item in list_of_dicts:")
    log_step('\tif item["item"] == search_item:')
    log_step('\t\tsearch_item = "Car"')
    search_item = "Car"
    for item in list_of_dicts:
        if item["item"] == search_item:
            log_step(
                f"4. Found '{search_item}' with price ${item['price']}\n"
            )

    # Sorting
    log_step(
        'list_of_dicts.sort(key=lambda x: x["price"])'
    )
    list_of_dicts.sort(key=lambda x: x["price"])
    log_step(
        f"5. Sorted by price = {list_of_dicts}\n"
    )


def listlists():
    # =====================================================================
    # 2. LIST OF Lists
    # =====================================================================
    log_step("\n--- 5. LIST OF LISTS ---\n")

    # A list of lists representing a gradebook
    gradebook = [
        ["Alice", 88, 92, 82],  # Row 0
        ["Zed", 99, 90, 88, 100],  # Row 1
        ["Charlie", 92, 90, 95],  # Row 2
        ["Eric", 93, 91],  # Row 3
        ["Bob", 88, 80, 75],  # Row 4
    ]

    log_step("gradebook = [")
    log_step('\t["Alice", 88, 92, 82],')  # Row 0
    log_step('\t["Zed", 99, 90, 88, 100],')
    log_step('\t["Charlie", 92, 90, 95]')  # Row 2
    log_step('\t ["Eric", 93, 91],')  # Row 3
    log_step('\t["Bob", 88, 80, 75],')  # Row 1

    log_step("]\n")

    print(gradebook)

    log_step(
        "\nAccess Charlie" "s second score (90)"
    )
    log_step(
        "# Outer index 2 (Charlie), Inner index 2 (second test score)"
    )
    log_step(
        "print(gradebook[2][2])  # Output: 90"
    )

    # 1. Access Charlie's second score (90)
    # Outer index 2 (Charlie), Inner index 2 (second test score)
    print(gradebook[2][2])  # Output: 90

    log_step("\nAdd a new student (a new row)")
    log_step(
        'gradebook.append(["David", 88, 84, 91])'
    )

    # 2. Add a new student (a new row)
    gradebook.append(["David", 88, 84, 91])
    log_step("gradebook after append")
    print(gradebook)

    log_step("\nUpdate Bob" "s first score to 82")
    log_step("gradebook[1][1] = 82")

    # 3. Update Bob's first score to 82
    gradebook[1][1] = 82
    log_step("gradebook after update")
    print(gradebook)

    # 4. remove a list
    log_step("\nRemove a list")
    log_step("del gradebook[0]")

    del gradebook[0]
    log_step("After remove")
    print(gradebook)

    # 5. Searching
    log_step(
        "\nSearch for the first Grade listed for David"
    )
    log_step('search_item = "David"')
    log_step("for user_entry in grades:")
    log_step("\tif user_item[0] == search_item:")
    log_step("\t\tresult = user_item[1]")
    search_item = "David"
    for user_entry in gradebook:
        if user_entry[0] == search_item:
            log_step(
                f"Found '{search_item}' with price {user_entry[1]}\n"
            )

    # Sorting
    log_step("\n#Sorting our outer list")
    log_step("gradebook.sort()")
    gradebook.sort()
    log_step(f"Sorted by name = {gradebook}\n")

    log_step(
        "\nSorting inner the list of grades for each student"
    )
    log_step("\ntmp_list = []")
    log_step("for user_entry in gradebook:")
    log_step(
        "\tfor i in range(1,len(user_entry)):"
    )
    log_step("\t\ttmp_list.append(user_entry[i])")
    log_step("\ttmp_list.sort()")
    log_step("\tfor i in range(len(tmp_list)):")
    log_step("\t\tuser_entry[i+1] = tmp_list[i]")
    log_step("\ttmp_list.clear()\n")
    tmp_list = []
    for user_entry in gradebook:
        for i in range(1, len(user_entry)):
            tmp_list.append(user_entry[i])
        tmp_list.sort()
        for i in range(len(tmp_list)):
            user_entry[i + 1] = tmp_list[i]

        tmp_list.clear()
    print(
        f"Sorted grades per user:\n\t{gradebook}"
    )


def tuples():
    # =====================================================================
    # 3. LISTS OF TUPLES
    # =====================================================================
    log_step("\n--- 3. LISTS OF TUPLES ---")

    # Creation
    log_step(
        'list_of_tuples = [("Tires", 499.00), ("Air", 5.00)]'
    )
    list_of_tuples = [
        ("Tires", 499.00),
        ("Air", 5.00),
    ]
    log_step(
        f"1. Created list_of_tuples = {list_of_tuples}\n"
    )

    # Adding
    log_step(
        'list_of_tuples.append(("Car", 15000.00))'
    )
    list_of_tuples.append(("Car", 15000.00))
    log_step(
        f"2. After append tuple = {list_of_tuples}\n"
    )

    # Removing
    log_step(
        "del list_of_tuples[1]"
    )  # Removes ("Air", 5.00) at index 1
    del list_of_tuples[
        1
    ]  # Removes ("Air", 5.00) at index 1
    log_step(
        f"3. After deleting index 1 = {list_of_tuples}\n"
    )

    # Searching (Checking if a key exists inside any tuple)
    log_step('search_target = "Car"')
    log_step("for item in list_of_tuples:")
    log_step("\tif item[0] == search_target:")
    search_target = "Car"
    for item in list_of_tuples:
        if item[0] == search_target:
            log_step(
                f"4. Found target '{search_target}' with value ${item[1]}\n"
            )

    # Sorting (Tuples are immutable, but the list containing them can be sorted by an index)
    log_step(
        "list_of_tuples.sort(key=lambda x: x[1])"
    )
    list_of_tuples.sort(
        key=lambda x: x[1]
    )  # Sort by price (index 1 of the tuple)
    log_step(
        f"5. Sorted by price (index 1) = {list_of_tuples}\n"
    )


def listsmixed():

    # =====================================================================
    # 4. LISTS OF MIXED DATA TYPES
    # =====================================================================
    log_step(
        "\n--- 4. LISTS OF MIXED DATA TYPES ---"
    )

    # Creation
    mixed_list = ["Apple", 45, True, "Banana", 12]
    log_step(
        f"1. Created mixed_list = {mixed_list}"
    )

    # Adding
    mixed_list.insert(
        2, "New Element"
    )  # Insert at a specific index
    log_step(
        f"2. After insert at index 2 = {mixed_list}"
    )

    # Removing
    mixed_list.pop()  # Pops the very last item (12)
    log_step(
        f"3. After popping last item = {mixed_list}"
    )

    # Searching
    if True in mixed_list:
        log_step(
            "4. Successfully found Boolean value True in list"
        )

    # Sorting (Mixed types fail standard .sort() due to TypeError, so we use string representation)
    mixed_list.sort(key=str)
    log_step(
        f"5. Sorted safely using key=str rule = {mixed_list}"
    )


def dicts():
    # =====================================================================
    # 5. BASIC DICTIONARIES (Key-Value Pairs)
    # =====================================================================
    log_step("\n--- 6. BASIC DICTIONARIES ---")

    # Creation
    basic_dict = {"Car": 15000.00, "Air": 5.00}
    log_step(
        f"1. Created basic_dict = {basic_dict}"
    )

    # Adding / Modifying
    basic_dict["Tires"] = 499.00
    log_step(
        f"2. After adding key 'Tires' = {basic_dict}"
    )
    basic_dict["Air"] = 6.50
    log_step(
        f"3. After modifying key 'Air' = {basic_dict}"
    )

    # Removing
    removed_val = basic_dict.pop("Air")
    log_step(
        f"4. After popping key 'Air' (Value was {removed_val}) = {basic_dict}"
    )

    # Searching
    search_key = "Car"
    if search_key in basic_dict:
        log_step(
            f"5. Key '{search_key}' found! Value is: {basic_dict[search_key]}"
        )

    # Sorting (Dicts are sorted by extracting items, sorting them, and converting back to dict)
    sorted_dict = dict(sorted(basic_dict.items()))
    log_step(
        f"6. Rebuilt dict sorted alphabetically by Keys = {sorted_dict}"
    )


def dictlists():
    # =====================================================================
    # 6. DICTIONARIES OF LISTS
    # =====================================================================
    log_step("\n--- 7. DICTIONARIES OF LISTS ---")

    # Creation
    dict_of_lists = {
        "fruits": ["Banana", "Apple"],
        "tools": ["Wrench"],
    }
    log_step(
        f"Created dict_of_lists = {dict_of_lists}\n"
    )

    # Adding to an internal list
    log_step(
        'dict_of_lists["fruits"].append("Cherry")'
    )
    dict_of_lists["fruits"].append("Cherry")
    log_step(
        f"After appending 'Cherry' to 'fruits' list = {dict_of_lists}\n"
    )

    # Removing from an internal list
    log_step(
        'dict_of_lists["fruits"].remove("Banana")'
    )
    dict_of_lists["fruits"].remove("Banana")
    log_step(
        f"After removing 'Banana' from 'fruits' list = {dict_of_lists}\n"
    )

    # Searching inside the inner lists
    log_step(
        "for category, items in dict_of_lists.items():"
    )
    log_step('\tif "Apple" in items:')
    for category, items in dict_of_lists.items():
        if "Apple" in items:
            log_step(
                f"Found 'Apple' inside the '{category}' list!\n"
            )

    # Sorting the inner lists
    log_step("for key in dict_of_lists:")
    log_step("\tdict_of_lists[key].sort()")
    for key in dict_of_lists:
        dict_of_lists[key].sort()
    log_step(
        f"After sorting all inner lists alphabetically = {dict_of_lists}\n"
    )


def dictdicts():
    # =====================================================================
    # 7. DICTIONARIES OF DICTIONARIES (Nested Dicts)
    # =====================================================================
    log_step(
        "\n--- 8. DICTIONARIES OF DICTIONARIES ---"
    )

    # Creation
    dict_of_dicts = {
        "User1": {
            "name": "Linda",
            "role": "Admin",
        },
        "User2": {
            "name": "Alex",
            "role": "Guest",
        },
    }
    log_step(
        f"1. Created dict_of_dicts = {dict_of_dicts}\n"
    )

    # Adding an entire sub-dictionary or a new inner value
    log_step(
        'dict_of_dicts["User3"] = {"name": "Charlie", "role": "User"}'
    )
    log_step(
        'dict_of_dicts["User1"]["status"] = "Active"'
    )
    dict_of_dicts["User3"] = {
        "name": "Charlie",
        "role": "User",
    }
    dict_of_dicts["User1"][
        "status"
    ] = "Active"  # Adding a new property to User1
    log_step(
        f"2. After updates = {dict_of_dicts}\n"
    )

    # Removing an inner property
    del dict_of_dicts["User2"]["role"]
    log_step('del dict_of_dicts["User2"]["role"]')
    log_step(
        f"3. After removing 'role' from User2 = {dict_of_dicts}\n"
    )

    # Searching deep values
    log_step(
        "for user_id, profile in dict_of_dicts.items():"
    )
    log_step(
        '\tif profile.get("name") == "Linda":'
    )
    for user_id, profile in dict_of_dicts.items():
        if profile.get("name") == "Linda":
            log_step(
                f"4. Deep Search: Found 'Linda' under the main key '{user_id}'\n"
            )

    # Sorting main dictionary based on an inner nested value (e.g., sort by the inner "name" value)
    sorted_nested = dict(
        sorted(
            dict_of_dicts.items(),
            key=lambda x: x[1]["name"],
        )
    )
    log_step(
        'sorted_nested = dict(sorted(dict_of_dicts.items(), key=lambda x: x[1]["name"]))'
    )
    log_step(
        f"5. Main dict sorted by inner 'name' key = {sorted_nested}\n"
    )


def dictlistdict():

    # =====================================================================
    # 8. DICTIONARY OF LISTS OF DICTIONARIES
    # =====================================================================
    log_step(
        "\n--- 9. DICT OF LISTS OF DICTS ---"
    )

    # Creation
    complex_structure_1 = {
        "August": [
            {"item": "Tires", "price": 499.00},
            {"item": "Air", "price": 5.00},
        ]
    }
    log_step(
        f"1. Created structure = {complex_structure_1}\n"
    )

    # Adding a dictionary item to the inner list
    complex_structure_1["August"].append(
        {"item": "Car", "price": 15000.00}
    )
    log_step(
        'complex_structure_1["August"].append({"item": "Car", "price": 15000.00})'
    )
    log_step(
        f"2. After adding new item dict to August list = {complex_structure_1}\n"
    )

    # Removing a specific dictionary from the inner list by index
    popped_dict = complex_structure_1[
        "August"
    ].pop(
        1
    )  # Removes index 1 ("Air")
    log_step(
        'popped_dict = complex_structure_1["August"].pop(1)'
    )
    log_step(
        f"3. After popping index 1 (Removed {popped_dict}) = {complex_structure_1}\n"
    )

    log_step(
        "for month, items_list in complex_structure_1.items():"
    )
    log_step("\tfor record in items_list:")
    log_step('\t\tif record["item"] == "Car":')
    # Searching for a specific dict match within the list
    for (
        month,
        items_list,
    ) in complex_structure_1.items():
        for record in items_list:
            if record["item"] == "Car":
                log_step(
                    f"4. Found record! Cost of Car in {month} is ${record['price']}\n"
                )

    # Sorting the inner list of dictionaries by an inner property (e.g., price)
    complex_structure_1["August"].sort(
        key=lambda x: x["price"]
    )
    log_step(
        '   complex_structure_1["August"].sort(key=lambda x: x["price"])'
    )
    log_step(
        f"5. Inner list sorted by 'price' key = {complex_structure_1}\n"
    )


def dictdictlist():
    # =====================================================================
    # 9. DICTIONARY OF DICTIONARIES OF LISTS
    # =====================================================================
    log_step(
        "\n---10. DICT OF DICTS OF LISTS ---"
    )

    # Creation
    complex_structure_2 = {
        "2026-08-10": {
            "AdminActions": [
                "login",
                "backup_db",
            ],
            "GuestActions": ["browse"],
        }
    }
    log_step(
        f"1. Created structure = {complex_structure_2}\n"
    )

    # Adding to the deepest list

    complex_structure_2["2026-08-10"][
        "AdminActions"
    ].append("logout")
    log_step(
        'complex_structure_2["2026-08-10"]["AdminActions"].append("logout")'
    )
    log_step(
        f"2. After appending 'logout' to AdminActions = {complex_structure_2}\n"
    )

    # Removing from the deepest list
    complex_structure_2["2026-08-10"][
        "AdminActions"
    ].remove("login")
    log_step(
        'complex_structure_2["2026-08-10"]["AdminActions"].remove("login")'
    )
    log_step(
        f"3. After removing 'login' from AdminActions = {complex_structure_2}\n"
    )

    log_step(
        "for date, categories in complex_structure_2.items():"
    )
    log_step(
        "\tfor group, actions in categories.items():"
    )
    log_step('\t\tif "backup_db" in actions:')
    # Searching the deepest elements
    for (
        date,
        categories,
    ) in complex_structure_2.items():
        for group, actions in categories.items():
            if "backup_db" in actions:
                log_step(
                    f"4. Deep Search: Found 'backup_db' action inside {date} -> {group}\n"
                )

    # Sorting the deepest list
    complex_structure_2["2026-08-10"][
        "AdminActions"
    ].sort()
    log_step(
        'complex_structure_2["2026-08-10"]["AdminActions"].sort()'
    )
    log_step(
        f"5. Deepest inner list sorted alphabetically = {complex_structure_2}\n"
    )


def patterns():

    # ========================week then py 103 in 2 =============================================
    # 10. ACCESS PATTERNS YOU WILL ACTUALLY USE
    # =====================================================================
    log_step(
        "\n--- 11. ACCESS PATTERNS YOU WILL ACTUALLY USE ---"
    )

    # 1) List access
    log_step(
        'sample_list = ["AAPL", "MSFT", "NVDA"]'
    )
    sample_list = ["AAPL", "MSFT", "NVDA"]
    log_step(
        f"1. sample_list[0] = {sample_list[0]}\n"
    )

    # 2) Dict access
    log_step(
        'sample_dict = {"symbol": "AAPL", "pnl": 250.00}'
    )
    sample_dict = {
        "symbol": "AAPL",
        "pnl": 250.00,
    }
    log_step(
        f"2. sample_dict['symbol'] = {sample_dict['symbol']}\n"
    )

    # 3) List inside dict
    log_step(
        'grouped = {"AAPL": [10, 20, 30], "MSFT": [5, 15]}'
    )
    grouped = {
        "AAPL": [10, 20, 30],
        "MSFT": [5, 15],
    }
    log_step(
        f"3. grouped['AAPL'] = {grouped['AAPL']}"
    )
    log_step(
        f"   grouped['AAPL'][1] = {grouped['AAPL'][1]}\n"
    )

    # 4) Dict inside list
    log_step(
        'trades = [{"symbol": "AAPL", "pnl": 25.00}, {"symbol": "MSFT", "pnl": -10.00}]'
    )
    trades = [
        {"symbol": "AAPL", "pnl": 25.00},
        {"symbol": "MSFT", "pnl": -10.00},
    ]
    log_step(
        f"4. trades[0]['symbol'] = {trades[0]['symbol']}"
    )
    log_step(
        f"   trades[1]['pnl'] = {trades[1]['pnl']}\n"
    )

    # 5) Loop through list of dicts
    log_step("for trade in trades:")
    for trade in trades:
        log_step(
            f"   ↳ trade['symbol'] = {trade['symbol']} | pnl = {trade['pnl']}"
        )

    # 6) Loop through dict items
    log_step(
        "\nfor key, values in grouped.items():"
    )
    for key, values in grouped.items():
        log_step(
            f"   ↳ key = {key} | values = {values}"
        )
    log_step("\n")


def cheatcode():
    # =====================================================================
    # 11. LISTS VS DICTS CHEAT CARD
    # =====================================================================
    log_step(
        "\n--- 12. LISTS VS DICTS CHEAT CODE ---"
    )
    log_step(
        "1. Use a LIST when you care about ORDER and POSITION"
    )
    log_step(
        "   trades = ['AAPL', 'MSFT', 'NVDA']"
    )
    log_step("   trades[0] -> 'AAPL'")
    log_step("   trades.append('AMZN')")
    log_step("   trades.pop(1)")
    log_step("   trades.sort()")

    log_step("")
    log_step(
        "2. Use a DICT when you care about NAMES and LOOKUPS"
    )
    log_step(
        "   trade = {'symbol': 'AAPL', 'pnl': 250.00}"
    )
    log_step("   trade['symbol'] -> 'AAPL'")
    log_step("   trade['pnl'] = 500.00")
    log_step("   trade.pop('pnl')")
    log_step(
        "   for key, value in trade.items():"
    )

    log_step("")
    log_step("3. Append belongs to LISTS")
    log_step("   my_list.append('new item')")
    log_step("   my_list.insert(0, 'first')")

    log_step("")
    log_step(
        "4. Direct assignment belongs to DICTS"
    )
    log_step("   my_dict['new_key'] = value")
    log_step("   my_dict['symbol'] = 'TSLA'")

    log_step("")
    log_step("5. Common trading patterns")
    log_step(
        "   trades[0]['symbol']       -> dict inside list"
    )
    log_step(
        "   grouped['AAPL'][0]       -> list inside dict"
    )
    log_step(
        "   for trade in trades:      -> iterate list of dicts"
    )
    log_step(
        "   for k, v in grouped.items(): -> iterate dict of lists"
    )

    log_step("")
    log_step("6. Memory rule")
    log_step("   [] = list = position-based")
    log_step("   {} = dict = key-based")
    log_step("   append() = list only")
    log_step(
        "   my_dict['new_key'] = value = dict only"
    )
    log_step(
        "   pop() works on both, but list uses index/value and dict uses key"
    )


def mapping():
    # =====================================================================
    # 12. MAPPING (Python 102 / 103 core)
    # =====================================================================
    log_step(
        "\n--- 13. MAPPING (TRANSFORMING DATA) ---"
    )
    log_step(
        "Mapping means taking one structure and turning it into another one."
    )
    log_step(
        "This is one of the biggest Python 102 / 103 ideas."
    )

    trades = [
        {"symbol": "AAPL", "pnl": 120.0},
        {"symbol": "MSFT", "pnl": -15.0},
        {"symbol": "NVDA", "pnl": 240.0},
        {"symbol": "AMZN", "pnl": 50.0},
    ]
    log_step(f"1. trades = {trades}\n")

    # list comprehension: map each trade to a single value
    log_step(
        'pnl_values = [trade["pnl"] for trade in trades]'
    )
    pnl_values = [
        trade["pnl"] for trade in trades
    ]
    log_step(
        f"2. pnl_values = [trade['pnl'] for trade in trades] -> {pnl_values}\n"
    )

    # filter: keep only profitable trades
    log_step(
        'winners = [trade for trade in trades if trade["pnl"] > 0]'
    )
    winners = [
        trade
        for trade in trades
        if trade["pnl"] > 0
    ]
    log_step(
        f"3. winners = [trade for trade in trades if trade['pnl'] > 0] -> {winners}\n"
    )

    # dict comprehension: turn list of dicts into a dict keyed by symbol
    log_step(
        'symbol_to_pnl = {trade["symbol"]: trade["pnl"] for trade in trades}'
    )
    symbol_to_pnl = {
        trade["symbol"]: trade["pnl"]
        for trade in trades
    }
    log_step(
        f"4. symbol_to_pnl = {{trade['symbol']: trade['pnl'] for trade in trades}} -> {symbol_to_pnl}\n"
    )

    # another common pattern: build a summary dict of counts or totals
    log_step(
        'profitable_symbols = {trade["symbol"] for trade in trades if trade["pnl"] > 0}'
    )
    profitable_symbols = {
        trade["symbol"]
        for trade in trades
        if trade["pnl"] > 0
    }
    log_step(
        f"5. profitable_symbols = {{trade['symbol'] for trade in trades if trade['pnl'] > 0}} -> {profitable_symbols}\n"
    )

    log_step("")
    log_step("7. Quick rule")
    log_step("   [x for x in items] -> new list")
    log_step(
        "   {k: v for item in items} -> new dict"
    )
    log_step("   if condition -> filter")
    log_step(
        "   for trade in trades -> iterate list of dicts"
    )
    log_step(
        "   trade['symbol'] -> access a dict inside a list"
    )


def cheatcard():

    # =====================================================================
    # 13. COMPLEXITY + RECURSION CHEAT CARD
    # =====================================================================
    log_step(
        "\n--- 14. COMPLEXITY + RECURSION CHEAT CARD ---"
    )
    log_step("1. One loop -> O(n)")
    log_step("   for x in items:")
    log_step(
        "   -> linearly scans the collection"
    )

    log_step("")
    log_step("2. Loop inside loop -> O(n^2)")
    log_step("   for i in items:")
    log_step("       for j in items:")
    log_step(
        "   -> each outer step triggers a full inner pass"
    )

    log_step("")
    log_step(
        "3. Loop inside loop inside loop -> O(n^3)"
    )
    log_step("   for i in items:")
    log_step("       for j in items:")
    log_step("           for k in items:")
    log_step("   -> growth blows up fast")

    log_step("")
    log_step("4. List search by value -> O(n)")
    log_step("   if target in my_list:")
    log_step(
        "   -> Python may walk through the whole list"
    )

    log_step("")
    log_step(
        "5. Dict lookup by key -> O(1) average"
    )
    log_step("   my_dict['AAPL']")
    log_step(
        "   -> direct hash lookup, usually instant"
    )

    log_step("")
    log_step(
        "6. Factorial recursion is a good memory anchor"
    )
    log_step("   def factorial(n):")
    log_step("       if n <= 1: return 1")
    log_step("       return n * factorial(n - 1)")
    log_step(
        "   -> one recursive call each step -> O(n)"
    )

    log_step("")
    log_step(
        "7. Naive Fibonacci recursion is a classic exponential case"
    )
    log_step(
        "   fib(n) calls fib(n-1) and fib(n-2)"
    )
    log_step(
        "   -> tree-like branching -> O(2^n)"
    )

    log_step("")
    log_step("8. Memory rule")
    log_step("   list scan = O(n)")
    log_step("   dict lookup = O(1)")
    log_step(
        "   nested loops = O(n^2), O(n^3), etc."
    )
    log_step(
        "   recursion = depends on branching and depth"
    )


def comprehensions():
    log_step(
        "\n--- 15. COMPREHENSIONS ie shorthand list/set/dict generator loops---"
    )
    log_step(
        "name is comprehensions — same syntax family covers four variants:\n"
    )

    log_step(
        "[... for ... in ... if ...] → list comprehension"
    )
    log_step(
        "{... for ... in ... if ...} → set comprehension"
    )
    log_step(
        "{k: v for ... in ... if ...} → dict comprehension (colon is what makes it a dict)"
    )
    log_step(
        "(... for ... in ... if ...) → generator expression (lazy, doesn't build the whole list in memory)\n"
    )

    log_step(
        "The a if cond else b one-liner from earlier is a different feature called a conditional"
    )
    log_step(
        "expression (people often call it the 'ternary operator' informally, though Python's own docs"
    )
    log_step(
        "just say conditional expression).\n"
    )

    log_step(
        "For 'what's legal' — the full grammar allows chaining multiple for and if clauses in one comprehension,"
    )
    log_step(
        "e.g. [x for x in a for y in b if cond], which is how nested loops with filters collapse into one line."
    )
    log_step(
        "That's the part worth reading directly rather than me describing it.\n"
    )

    log_step("Official docs, most useful first")
    log_step(
        'Python Tutorial §5.1.4 "List Comprehensions" — the friendly intro with the chained-for/if'
    )
    log_step(
        "examples: https://docs.python.org/3/tutorial/datastructures.html#list-comprehensions"
    )
    log_step(
        'Language Reference "Displays for lists, sets and dictionaries" — the actual formal grammar, if you want to know'
    )
    log_step(
        "exactly what's legal: https://docs.python.org/3/reference/expressions.html#displays-for-lists-sets-and-dictionaries"
    )
    log_step(
        'Language Reference "Conditional expressions" — the a if cond else b form:'
    )
    log_step(
        "https://docs.python.org/3/reference/expressions.html#conditional-expressions\n"
    )


# Helper function to sort individual strings (used in your example)
def str_sort(s):
    return "".join(sorted(s))


def main():
    def wide_formatter(prog):
        return (
            argparse.RawDescriptionHelpFormatter(
                prog,
                width=110,
                max_help_position=46,
            )
        )

    parser = argparse.ArgumentParser(
        description="Display python lst and dictionaries help",
        epilog="""\
    Usage examples:
    data_structures_reference.py -q -cc -cd
    data_structures_reference.py -o <output file>
    data_structures_reference.py   (Will print to stdout)
    """,
        formatter_class=wide_formatter,
    )

    parser.add_argument(
        "-o",
        "--outfile",
        metavar="",
        help="\tpath and name of output file",
    )
    a = parser.add_argument(
        "-q",
        "--quickref",
        action="store_true",
        help="\tprint quick refernce",
    )
    b = parser.add_argument(
        "-b",
        "--basic",
        action="store_true",
        help="\tprint help on basic lists",
    )
    c = parser.add_argument(
        "-ld",
        "--listsdicts",
        action="store_true",
        help="\tprint help on lists of dicts",
    )
    d = parser.add_argument(
        "-t",
        "--tuples",
        action="store_true",
        help="\tprint help on tuples",
    )
    e = parser.add_argument(
        "-lm",
        "--listsmixed",
        action="store_true",
        help="\tprint help on lists of mixed data",
    )
    f = parser.add_argument(
        "-d",
        "--dicts",
        action="store_true",
        help="\tprint help on dictionaries",
    )
    g = parser.add_argument(
        "-dl",
        "--dictlists",
        action="store_true",
        help="\tprint help on dictioary of lists",
    )
    h = parser.add_argument(
        "-dd",
        "--dictdicts",
        action="store_true",
        help="\tprint help on dictionary of dictionaries",
    )
    i = parser.add_argument(
        "-dld",
        "--dictlistdict",
        action="store_true",
        help="\tprint help on dict of list of dicts",
    )
    j = parser.add_argument(
        "-ddl",
        "--dictdictlist",
        action="store_true",
        help="\tprint help on dict of dict of lists",
    )
    k = parser.add_argument(
        "-p",
        "--patterns",
        action="store_true",
        help="\tprint help on patterns",
    )
    q = parser.add_argument(
        "-cc",
        "--cheatcode",
        action="store_true",
        help="\tprint cheat codes",
    )
    m = parser.add_argument(
        "-m",
        "--mapping",
        action="store_true",
        help="\tprint help on mapping",
    )
    n = parser.add_argument(
        "-cd",
        "--cheatcard",
        action="store_true",
        help="\tprint cheat card",
    )
    o = parser.add_argument(
        "-co",
        "--comprehensions",
        action="store_true",
        help="\tprint comprehensions",
    )
    p = parser.add_argument(
        "-ll",
        "--listlists",
        action="store_true",
        help="\tprint list of lists",
    )
    args = parser.parse_args()

    output_file = (
        args.outfile if args.outfile else "None"
    )

    # Build a list of lists [[arg name, True/False],[],..]
    list_values = [
        (
            [a.dest, args.quickref]
            if args.quickref
            else [a.dest, False]
        ),
        (
            [b.dest, args.basic]
            if args.basic
            else [b.dest, False]
        ),
        (
            [c.dest, args.listsdicts]
            if args.listsdicts
            else [c.dest, False]
        ),
        (
            [d.dest, args.tuples]
            if args.tuples
            else [d.dest, False]
        ),
        (
            [e.dest, args.listsmixed]
            if args.listsmixed
            else [e.dest, False]
        ),
        (
            [f.dest, args.listlists]
            if args.listlists
            else [f.dest, False]
        ),
        (
            [g.dest, args.dicts]
            if args.dicts
            else [g.dest, False]
        ),
        (
            [h.dest, args.dictlists]
            if args.dictlists
            else [h.dest, False]
        ),
        (
            [i.dest, args.dictdicts]
            if args.dictdicts
            else [i.dest, False]
        ),
        (
            [j.dest, args.dictlistdict]
            if args.dictlistdict
            else [j.dest, False]
        ),
        (
            [k.dest, args.dictdictlist]
            if args.dictdictlist
            else [k.dest, False]
        ),
        (
            [q.dest, args.patterns]
            if args.patterns
            else [q.dest, False]
        ),
        (
            [m.dest, args.cheatcode]
            if args.cheatcode
            else [m.dest, False]
        ),
        (
            [n.dest, args.mapping]
            if args.mapping
            else [n.dest, False]
        ),
        (
            [o.dest, args.cheatcard]
            if args.cheatcard
            else [o.dest, False]
        ),
        (
            [p.dest, args.comprehensions]
            if args.comprehensions
            else [p.dest, False]
        ),
    ]
    # If any flags give we only print the else we print everything
    switch_given = False
    for items in list_values:
        if items[1]:
            switch_given = True

    # Dictionary of defined function names to call
    commands = {
        "quickref": quickref,
        "basic": basic,
        "listsdicts": listsdicts,
        "tuples": tuples,
        "listsmixed": listsmixed,
        "listlists": listlists,
        "dicts": dicts,
        "dictlists": dictlists,
        "dictdicts": dictdicts,
        "dictlistdict": dictlistdict,
        "dictdictlist": dictdictlist,
        "patterns": patterns,
        "cheatcode": cheatcode,
        "mapping": mapping,
        "cheatcard": cheatcard,
        "comprehensions": comprehensions,
    }
    log_step(
        "=================================================="
    )
    log_step(
        "          PYTHON DATA STRUCTURES REFERENCE        "
    )
    log_step(
        "=================================================="
    )

    # If 1+ switches given
    if switch_given:
        # Iterate list of switches
        for items in list_values:
            # If switch set to true, call its function
            if items[1]:
                commands[items[0]]()
    else:
        # No switches given, call every function  commands[]
        for com in commands.keys():
            commands[com]()

    log_step(
        "\n=================================================="
    )
    log_step(
        "            ALL STEPS DEMONSTRATED!               "
    )
    log_step(
        "=================================================="
    )

    # I user asked for an output file, save results to  it
    if output_file != "None":
        save_log_to_file(
            output_file, cheat_sheet_lines
        )


if __name__ == "__main__":
    main()
