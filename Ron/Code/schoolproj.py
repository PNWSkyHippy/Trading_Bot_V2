import copy

purchases = [
    {"customer": "Charlie", "amount": 12.5},
    {"customer": "Alice", "amount": 25.0},
    {"customer": "Bob", "amount": 10.0},
    {"customer": "Alice", "amount": 40.0},
    {"customer": "Bob", "amount": "5.0"},
]


def compute_totals(loc_list):
    """Takes list of dictionaries of customer/amount pairs
    Createes a list of dicts comtaining 1 entry per customer
    paired with the total of all amounts for that customer
    """
    loc_dict_list = (
        []
    )  # New list of dictionaries for results
    tmp_dict = {}  # Temp scratch dictionary
    assert (
        len(loc_list) >= 1
    ), f"Error: Length of loc_list was empty"
    # Loop though each dictioary in the list
    for lists in loc_list:
        found = False
        chk_type = type(lists["amount"])
        assert chk_type in (
            float,
            int,
        ), f'Error: amount {lists["amount"]} is not a number'
        # Create a dictionary entry for "customer"/"amount"
        tmp_dict["customer"] = lists["customer"]
        tmp_dict["total"] = lists["amount"]

        # Check if this customer is in new list of dicts
        for key in loc_dict_list:
            if (
                lists["customer"]
                == key["customer"]
            ):
                found = True
        # If not found add a new entry for customer
        # using deep copy as were going to reuse tmp_dict
        if not found:
            loc_dict_list.append(
                copy.deepcopy(tmp_dict)
            )
        # Else was found so locate the dict in new list
        # And add the amount to the running total
        else:
            for ldicts in loc_dict_list:
                if (
                    ldicts["customer"]
                    == lists["customer"]
                ):
                    ldicts["total"] += lists[
                        "amount"
                    ]
    return loc_dict_list


def sort_totals(loc_dict):
    """Given a list of dictionaries, sorts the list
    entries by the dicionary key ["total"] high to low
    """
    loc_dict.sort(
        key=lambda x: x["total"], reverse=True
    )
    return loc_dict


def print_summary(loc_dict):
    """Formats and prints the summary results"""
    for ldict in loc_dict:
        print(
            f'{ldict["customer"]} -> {ldict["total"]}'
        )
    return


def main():
    my_dict = compute_totals(purchases)
    sorted_totals = sort_totals(my_dict)
    print_summary(sorted_totals)


if __name__ == "__main__":
    main()

    """Goal: print
Text

Alice -> 65.0
Bob -> 15.0
Charlie -> 12.5
sorted by total (largest first).

Use 3+ functions plus main(), for example:
compute_totals(purchases) → dict
sort_totals(totals_dict) → sorted list of pairs
print_summary(sorted_totals) → does the printing
main() → wires it all together
Now jump into the editor, write the full program, hit Run to make sure it works, then Run & Submit and send me the cod

    """
