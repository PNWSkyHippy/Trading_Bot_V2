def budget_tracker():
    arg_list = ["", "", ""]
    fixed_list = []
    tot_cost = 0.0
    for i in range(0, 3):
        arg_list[i] = input(
            f"Enter the name and cost of item [{i+1}]: "
        )
        # Break the list into tuples split by the space
        fixed_list = str(arg_list[i]).split(" ")
        # keep a running total of the costs
        tot_cost += float(fixed_list[1])
        # format the number with $ prepended and 2 digit float, put it back in list
        arg_list[i] = (
            f"{fixed_list[0]} - "
            f"${float(fixed_list[1]):.2f}"
        )
    # sort the list based on the number portion afer the dollar sign
    arg_list.sort(
        key=lambda item: float(
            item.split("$")[1]
        ),
        reverse=True,
    )
    print(f"Sorted list {arg_list}")

    # return the total cost
    return round(tot_cost, 2)


print(f"Total Cost is: {budget_tracker():.2f}")
