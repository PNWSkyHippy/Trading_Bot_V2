import sys
import argparse

def print_basic():
    # =====================================================================
    # 1. BASIC LISTS (Arrays)
    # =====================================================================
    log_step("\n--- 1. BASIC LISTS ---")

    # Creation
    basic_list = ["131", "798", "465", "0"]
    log_step(f"1. Created basic_list = {basic_list}")

    # Adding (Append)
    basic_list.append("989")
    log_step(f"2. After append '989' = {basic_list}")

    # Removing
    removed_item = basic_list.pop(3) # Removes by index (removes '0')
    log_step(f"3. After pop(3) [removed '{removed_item}'] = {basic_list}")
    basic_list.remove("798") # Removes by value
    log_step(f"4. After remove('798') = {basic_list}")

    # Searching
    search_val = "465"
    if search_val in basic_list:
        idx = basic_list.index(search_val)
        log_step(f"5. Found '{search_val}' at index {idx}")

    # Iteration & In-place String Sorting (Your example logic)
    for i in range(len(basic_list)):
        log_step(f"   ↳ basic_list[{i}] = {basic_list[i]}")
        basic_list[i] = str_sort(basic_list[i])
    log_step(f"6. Each inner string sorted = {basic_list}")

    # Sorting the List itself
    basic_list.sort()
    log_step(f"7. Final basic_list sorted = {basic_list}")


def save_log_to_file(filename, content_list):
    """Takes a list of string lines and writes them to a text file."""    
    try:
        with open(filename, "w", encoding="utf-8") as file:
            for line in content_list:
                file.write(line + "\n")
        print(f"\n[SUCCESS] Reference guide saved to '{filename}'")
    except IOError as e:
        print(f"\n[ERROR] Could not write to file: {e}")

cheat_sheet_lines = []

# 2. A helper to print and store lines simultaneously 
def log_step(text):
    print(text)                  # Prints to your VS Code terminal
    cheat_sheet_lines.append(text) # Saves it for the text file


def add_quick_reference():
    log_step("==================================================")
    log_step("               QUICK CHOICE GUIDE                 ")
    log_step("==================================================")
    log_step("LIST vs DICT")
    log_step("")
    log_step("[] = LIST = ordered, index-based, good for sequences")
    log_step("    symbols = ['AAPL', 'MSFT', 'NVDA']")
    log_step("    symbols[0] -> 'AAPL'")
    log_step("    symbols.append('AMZN')")
    log_step("    symbols.sort()")
    log_step("")
    log_step("{} = DICT = key-based, fast lookup by name")
    log_step("    trade = {'symbol': 'AAPL', 'pnl': 250.00}")
    log_step("    trade['symbol'] -> 'AAPL'")
    log_step("    trade['pnl'] = 500.00")
    log_step("    trade['new_key'] = value")
    log_step("")
    log_step("When to pick which:")
    log_step("- use a list when you want order, iteration, or a sequence")
    log_step("- use a dict when you want direct lookup by name/key")
    log_step("- use list of dicts when you store many records")
    log_step("- use dict of lists when you group records by category")
    log_step("")
    log_step("BIG-O MEMORY RULES")
    log_step("- one loop -> O(n)")
    log_step("- loop inside loop -> O(n^2)")
    log_step("- loop inside loop inside loop -> O(n^3)")
    log_step("- list search by value -> O(n)")
    log_step("- dict lookup by key -> O(1) average")
    log_step("- factorial recursion -> O(n)")
    log_step("- naive Fibonacci recursion -> O(2^n)")
    log_step("==================================================")
    log_step("")


# Helper function to sort individual strings (used in your example)
def str_sort(s):
    return "".join(sorted(s))

def main():
    def wide_formatter(prog):
            return argparse.RawDescriptionHelpFormatter(
                prog,
                width=110,
                max_help_position=46,
            )


    parser = argparse.ArgumentParser(
        description="Display python lst and dicntionaries help",
        epilog="""\
    Usage examples:
    data_structures_referemce.py -o <output file>
    data_structures_referemce.py   (Will print to stdout)
    """,
        formatter_class=wide_formatter,
        )
    
    parser.add_argument("-o","--outfile", metavar="", help="\tpath and name of output file")
    parser.add_argument("-q","--quickref", action='store_true', help="\tprint quick refernce")    
    parser.add_argument("-b","--basic", action='store_true', help="\tprint help on basic lists")
    parser.add_argument("-ld","--listsdicts", action='store_true', help="\tprint help on lists of dicts")    
    parser.add_argument("-t","--tuples", action='store_true', help="\tprint help on tuples")
    parser.add_argument("-lm","--listsmixed", action='store_true', help="\tprint help on lists of mixed data")
    parser.add_argument("-d","--dicts", action='store_true', help="\tprint help on dictionaries")
    parser.add_argument("-dl","--dictlists", action='store_true', help="\tprint help on dictioary of lists") 
    parser.add_argument("-dd","--dictdicts", action='store_true', help="\tprint help on dictionary of dictionaries")  
    parser.add_argument("-dld","--dictlistdict", action='store_true', help="\tprint help on dict of list of dicts")
    parser.add_argument("-ddl","--dictdictlist", action='store_true', help="\tprint help on dict of dict of lists")
    parser.add_argument("-p","--patterns", action='store_true', help="\tprint help on patterns")
    parser.add_argument("-c","--cheatcode", action='store_true', help="\tprint help on cheat codes")
            
    args = parser.parse_args()
 
    output_file = args.outfile if args.outfile else "None"
    quick_ref = True if args.quickref else False
    basic = True if args.basic else False
    list_dicts = True if args.listsdicts else False
    tuples = True if args.tuples else False
    list_mixed = True if args.listsmixed else False
    dicts = True if args.dicts else False
    dictlists = True if args.dictlists else False
    dictdicts = True if args.dictdicts else False
    dictslistdict = True if args.dictlistdict else False
    dictdictlists = True if args.dictdictlist else False
    patterns = True if args.patterns else False
    cheatcodes = True if args.cheatcode else False

    log_step("==================================================")
    log_step("          PYTHON DATA STRUCTURES REFERENCE        ")
    log_step("==================================================")

    if quick_ref:
        add_quick_reference()
    if basic:
        print_basic()

    # =====================================================================
    # 2. LISTS OF DICTIONARIES
    # =====================================================================
    log_step("\n--- 2. LISTS OF DICTIONARIES ---")

    # Creation
    list_of_dicts = [
        {"item": "Tires", "price": 499.00},
        {"item": "Air", "price": 5.00}
    ]
    log_step(f"1. Created list_of_dicts = {list_of_dicts}")

    # Adding
    list_of_dicts.append({"item": "Car", "price": 15000.00})
    log_step(f"2. After append dict = {list_of_dicts}")

    # Removing
    del list_of_dicts[1]  # Removes {"item": "Air", "price": 5.00}
    log_step(f"3. After deleting index 1 = {list_of_dicts}")

    # Searching
    search_item = "Car"
    for item in list_of_dicts:
        if item["item"] == search_item:
            log_step(f"4. Found '{search_item}' with price ${item['price']}")

    # Sorting
    list_of_dicts.sort(key=lambda x: x["price"])
    log_step(f"5. Sorted by price = {list_of_dicts}")


    # =====================================================================
    # 3. LISTS OF TUPLES
    # =====================================================================
    log_step("\n--- 3. LISTS OF TUPLES ---")

    # Creation
    list_of_tuples = [("Tires", 499.00), ("Air", 5.00)]
    log_step(f"1. Created list_of_tuples = {list_of_tuples}")

    # Adding
    list_of_tuples.append(("Car", 15000.00))
    log_step(f"2. After append tuple = {list_of_tuples}")

    # Removing
    del list_of_tuples[1] # Removes ("Air", 5.00) at index 1
    log_step(f"3. After deleting index 1 = {list_of_tuples}")

    # Searching (Checking if a key exists inside any tuple)
    search_target = "Car"
    for item in list_of_tuples:
        if item[0] == search_target:
            log_step(f"4. Found target '{search_target}' with value ${item[1]}")

    # Sorting (Tuples are immutable, but the list containing them can be sorted by an index)
    list_of_tuples.sort(key=lambda x: x[1]) # Sort by price (index 1 of the tuple)
    log_step(f"5. Sorted by price (index 1) = {list_of_tuples}")


    # =====================================================================
    # 4. LISTS OF MIXED DATA TYPES
    # =====================================================================
    log_step("\n--- 4. LISTS OF MIXED DATA TYPES ---")

    # Creation
    mixed_list = ["Apple", 45, True, "Banana", 12]
    log_step(f"1. Created mixed_list = {mixed_list}")

    # Adding
    mixed_list.insert(2, "New Element") # Insert at a specific index
    log_step(f"2. After insert at index 2 = {mixed_list}")

    # Removing
    mixed_list.pop() # Pops the very last item (12)
    log_step(f"3. After popping last item = {mixed_list}")

    # Searching
    if True in mixed_list:
        log_step(f"4. Successfully found Boolean value True in list")

    # Sorting (Mixed types fail standard .sort() due to TypeError, so we use string representation)
    mixed_list.sort(key=str)
    log_step(f"5. Sorted safely using key=str rule = {mixed_list}")


    # =====================================================================
    # 5. BASIC DICTIONARIES (Key-Value Pairs)
    # =====================================================================
    log_step("\n--- 5. BASIC DICTIONARIES ---")

    # Creation
    basic_dict = {"Car": 15000.00, "Air": 5.00}
    log_step(f"1. Created basic_dict = {basic_dict}")

    # Adding / Modifying
    basic_dict["Tires"] = 499.00
    log_step(f"2. After adding key 'Tires' = {basic_dict}")
    basic_dict["Air"] = 6.50
    log_step(f"3. After modifying key 'Air' = {basic_dict}")

    # Removing
    removed_val = basic_dict.pop("Air")
    log_step(f"4. After popping key 'Air' (Value was {removed_val}) = {basic_dict}")

    # Searching
    search_key = "Car"
    if search_key in basic_dict:
        log_step(f"5. Key '{search_key}' found! Value is: {basic_dict[search_key]}")

    # Sorting (Dicts are sorted by extracting items, sorting them, and converting back to dict)
    sorted_dict = dict(sorted(basic_dict.items()))
    log_step(f"6. Rebuilt dict sorted alphabetically by Keys = {sorted_dict}")


    # =====================================================================
    # 6. DICTIONARIES OF LISTS
    # =====================================================================
    log_step("\n--- 6. DICTIONARIES OF LISTS ---")

    # Creation
    dict_of_lists = {"fruits": ["Banana", "Apple"], "tools": ["Wrench"]}
    log_step(f"1. Created dict_of_lists = {dict_of_lists}")

    # Adding to an internal list
    dict_of_lists["fruits"].append("Cherry")
    log_step(f"2. After appending 'Cherry' to 'fruits' list = {dict_of_lists}")

    # Removing from an internal list
    dict_of_lists["fruits"].remove("Banana")
    log_step(f"3. After removing 'Banana' from 'fruits' list = {dict_of_lists}")

    # Searching inside the inner lists
    for category, items in dict_of_lists.items():
        if "Apple" in items:
            log_step(f"4. Found 'Apple' inside the '{category}' list!")

    # Sorting the inner lists
    for key in dict_of_lists:
        dict_of_lists[key].sort()
    log_step(f"5. After sorting all inner lists alphabetically = {dict_of_lists}")


    # =====================================================================
    # 7. DICTIONARIES OF DICTIONARIES (Nested Dicts)
    # =====================================================================
    log_step("\n--- 7. DICTIONARIES OF DICTIONARIES ---")

    # Creation
    dict_of_dicts = {
        "User1": {"name": "Linda", "role": "Admin"},
        "User2": {"name": "Alex", "role": "Guest"}
    }
    log_step(f"1. Created dict_of_dicts = {dict_of_dicts}")

    # Adding an entire sub-dictionary or a new inner value
    dict_of_dicts["User3"] = {"name": "Charlie", "role": "User"}
    dict_of_dicts["User1"]["status"] = "Active" # Adding a new property to User1
    log_step(f"2. After updates = {dict_of_dicts}")

    # Removing an inner property
    del dict_of_dicts["User2"]["role"]
    log_step(f"3. After removing 'role' from User2 = {dict_of_dicts}")

    # Searching deep values
    for user_id, profile in dict_of_dicts.items():
        if profile.get("name") == "Linda":
            log_step(f"4. Deep Search: Found 'Linda' under the main key '{user_id}'")

    # Sorting main dictionary based on an inner nested value (e.g., sort by the inner "name" value)
    sorted_nested = dict(sorted(dict_of_dicts.items(), key=lambda x: x[1]["name"]))
    log_step(f"5. Main dict sorted by inner 'name' key = {sorted_nested}")


    # =====================================================================
    # 8. DICTIONARY OF LISTS OF DICTIONARIES
    # =====================================================================
    log_step("\n--- 8. DICT OF LISTS OF DICTS ---")

    # Creation
    complex_structure_1 = {
        "August": [
            {"item": "Tires", "price": 499.00},
            {"item": "Air", "price": 5.00}
     ]
    }   
    log_step(f"1. Created structure = {complex_structure_1}")

    # Adding a dictionary item to the inner list
    complex_structure_1["August"].append({"item": "Car", "price": 15000.00})
    log_step(f"2. After adding new item dict to August list = {complex_structure_1}")

    # Removing a specific dictionary from the inner list by index
    popped_dict = complex_structure_1["August"].pop(1) # Removes index 1 ("Air")
    log_step(f"3. After popping index 1 (Removed {popped_dict}) = {complex_structure_1}")

    # Searching for a specific dict match within the list
    for month, items_list in complex_structure_1.items():
        for record in items_list:
            if record["item"] == "Car":
                log_step(f"4. Found record! Cost of Car in {month} is ${record['price']}")

    # Sorting the inner list of dictionaries by an inner property (e.g., price)
    complex_structure_1["August"].sort(key=lambda x: x["price"])
    log_step(f"5. Inner list sorted by 'price' key = {complex_structure_1}")


    # =====================================================================
    # 9. DICTIONARY OF DICTIONARIES OF LISTS
    # =====================================================================
    log_step("\n--- 9. DICT OF DICTS OF LISTS ---")

    # Creation
    complex_structure_2 = {
        "2026-08-10": {
            "AdminActions": ["login", "backup_db"],
            "GuestActions": ["browse"]
        }
    }
    log_step(f"1. Created structure = {complex_structure_2}")

    # Adding to the deepest list
    complex_structure_2["2026-08-10"]["AdminActions"].append("logout")
    log_step(f"2. After appending 'logout' to AdminActions = {complex_structure_2}")

    # Removing from the deepest list
    complex_structure_2["2026-08-10"]["AdminActions"].remove("login")
    log_step(f"3. After removing 'login' from AdminActions = {complex_structure_2}")

    # Searching the deepest elements
    for date, categories in complex_structure_2.items():
        for group, actions in categories.items():
            if "backup_db" in actions:
                log_step(f"4. Deep Search: Found 'backup_db' action inside {date} -> {group}")

    # Sorting the deepest list
    complex_structure_2["2026-08-10"]["AdminActions"].sort()
    log_step(f"5. Deepest inner list sorted alphabetically = {complex_structure_2}")

    # ========================week then py 103 in 2 mongr=============================================
    # 10. ACCESS PATTERNS YOU WILL ACTUALLY USE
    # =====================================================================
    log_step("\n--- 10. ACCESS PATTERNS YOU WILL ACTUALLY USE ---")

    # 1) List access
    sample_list = ["AAPL", "MSFT", "NVDA"]
    log_step(f"1. sample_list[0] = {sample_list[0]}")

    # 2) Dict access
    sample_dict = {"symbol": "AAPL", "pnl": 250.00}
    log_step(f"2. sample_dict['symbol'] = {sample_dict['symbol']}")

    # 3) List inside dict
    grouped = {"AAPL": [10, 20, 30], "MSFT": [5, 15]}
    log_step(f"3. grouped['AAPL'] = {grouped['AAPL']}")
    log_step(f"   grouped['AAPL'][1] = {grouped['AAPL'][1]}")

    # 4) Dict inside list
    trades = [{"symbol": "AAPL", "pnl": 25.00}, {"symbol": "MSFT", "pnl": -10.00}]
    log_step(f"4. trades[0]['symbol'] = {trades[0]['symbol']}")
    log_step(f"   trades[1]['pnl'] = {trades[1]['pnl']}")

    # 5) Loop through list of dicts
    for trade in trades:
        log_step(f"   ↳ trade['symbol'] = {trade['symbol']} | pnl = {trade['pnl']}")

    # 6) Loop through dict items
    for key, values in grouped.items():
        log_step(f"   ↳ key = {key} | values = {values}")

    # =====================================================================
    # 11. LISTS VS DICTS CHEAT CARD
    # =====================================================================
    log_step("\n--- 11. LISTS VS DICTS CHEAT CARD ---")
    log_step("1. Use a LIST when you care about ORDER and POSITION")
    log_step("   trades = ['AAPL', 'MSFT', 'NVDA']")
    log_step("   trades[0] -> 'AAPL'")
    log_step("   trades.append('AMZN')")
    log_step("   trades.pop(1)")
    log_step("   trades.sort()")

    log_step("")
    log_step("2. Use a DICT when you care about NAMES and LOOKUPS")
    log_step("   trade = {'symbol': 'AAPL', 'pnl': 250.00}")
    log_step("   trade['symbol'] -> 'AAPL'")
    log_step("   trade['pnl'] = 500.00")
    log_step("   trade.pop('pnl')")
    log_step("   for key, value in trade.items():")

    log_step("")
    log_step("3. Append belongs to LISTS")
    log_step("   my_list.append('new item')")
    log_step("   my_list.insert(0, 'first')")

    log_step("")
    log_step("4. Direct assignment belongs to DICTS")
    log_step("   my_dict['new_key'] = value")
    log_step("   my_dict['symbol'] = 'TSLA'")

    log_step("")
    log_step("5. Common trading patterns")
    log_step("   trades[0]['symbol']       -> dict inside list")
    log_step("   grouped['AAPL'][0]       -> list inside dict")
    log_step("   for trade in trades:      -> iterate list of dicts")
    log_step("   for k, v in grouped.items(): -> iterate dict of lists")

    log_step("")
    log_step("6. Memory rule")
    log_step("   [] = list = position-based")
    log_step("   {} = dict = key-based")
    log_step("   append() = list only")
    log_step("   my_dict['new_key'] = value = dict only")
    log_step("   pop() works on both, but list uses index/value and dict uses key")

    # =====================================================================
    # 12. MAPPING (Python 102 / 103 core)
    # =====================================================================
    log_step("\n--- 12. MAPPING (TRANSFORMING DATA) ---")
    log_step("Mapping means taking one structure and turning it into another one.")
    log_step("This is one of the biggest Python 102 / 103 ideas.")

    trades = [
        {"symbol": "AAPL", "pnl": 120.0},
        {"symbol": "MSFT", "pnl": -15.0},
        {"symbol": "NVDA", "pnl": 240.0},
        {"symbol": "AMZN", "pnl": 50.0}
    ]
    log_step(f"1. trades = {trades}")

    # list comprehension: map each trade to a single value
    pnl_values = [trade["pnl"] for trade in trades]
    log_step(f"2. pnl_values = [trade['pnl'] for trade in trades] -> {pnl_values}")

    # filter: keep only profitable trades
    winners = [trade for trade in trades if trade["pnl"] > 0]
    log_step(f"3. winners = [trade for trade in trades if trade['pnl'] > 0] -> {winners}")

    # dict comprehension: turn list of dicts into a dict keyed by symbol
    symbol_to_pnl = {trade["symbol"]: trade["pnl"] for trade in trades}
    log_step(f"4. symbol_to_pnl = {{trade['symbol']: trade['pnl'] for trade in trades}} -> {symbol_to_pnl}")

    # another common pattern: build a summary dict of counts or totals
    profitable_symbols = {trade["symbol"] for trade in trades if trade["pnl"] > 0}
    log_step(f"5. profitable_symbols = {{trade['symbol'] for trade in trades if trade['pnl'] > 0}} -> {profitable_symbols}")

    log_step("")
    log_step("7. Quick rule")
    log_step("   [x for x in items] -> new list")
    log_step("   {k: v for item in items} -> new dict")
    log_step("   if condition -> filter")
    log_step("   for trade in trades -> iterate list of dicts")
    log_step("   trade['symbol'] -> access a dict inside a list")

    # =====================================================================
    # 13. COMPLEXITY + RECURSION CHEAT CARD
    # =====================================================================
    log_step("\n--- 13. COMPLEXITY + RECURSION CHEAT CARD ---")
    log_step("1. One loop -> O(n)")
    log_step("   for x in items:")
    log_step("   -> linearly scans the collection")

    log_step("")
    log_step("2. Loop inside loop -> O(n^2)")
    log_step("   for i in items:")
    log_step("       for j in items:")
    log_step("   -> each outer step triggers a full inner pass")

    log_step("")
    log_step("3. Loop inside loop inside loop -> O(n^3)")
    log_step("   for i in items:")
    log_step("       for j in items:")
    log_step("           for k in items:")
    log_step("   -> growth blows up fast")

    log_step("")
    log_step("4. List search by value -> O(n)")
    log_step("   if target in my_list:")
    log_step("   -> Python may walk through the whole list")

    log_step("")
    log_step("5. Dict lookup by key -> O(1) average")
    log_step("   my_dict['AAPL']")
    log_step("   -> direct hash lookup, usually instant")

    log_step("")
    log_step("6. Factorial recursion is a good memory anchor")
    log_step("   def factorial(n):")
    log_step("       if n <= 1: return 1")
    log_step("       return n * factorial(n - 1)")
    log_step("   -> one recursive call each step -> O(n)")

    log_step("")
    log_step("7. Naive Fibonacci recursion is a classic exponential case")
    log_step("   fib(n) calls fib(n-1) and fib(n-2)")
    log_step("   -> tree-like branching -> O(2^n)")

    log_step("")
    log_step("8. Memory rule")
    log_step("   list scan = O(n)")
    log_step("   dict lookup = O(1)")
    log_step("   nested loops = O(n^2), O(n^3), etc.")
    log_step("   recursion = depends on branching and depth")

    log_step("\n==================================================")
    log_step("            ALL STEPS DEMONSTRATED!               ")
    log_step("==================================================")

    if output_file != "None":
        save_log_to_file(output_file,cheat_sheet_lines)

if __name__ == "__main__":
    main()