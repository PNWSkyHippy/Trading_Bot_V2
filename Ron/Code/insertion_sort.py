def insertion_sort(arr):
    """Takes a list and sorts a copy of it susing insertion sort
    returns the sported list, leaving original intact
    """
    # Make a copy of the list
    tmp_list = arr.copy()
    # Loop through the list, 2nd item to last
    for pass_cnt in range(1, len(tmp_list)):
        # Store current item we want to sort into position
        key = tmp_list[pass_cnt]
        # setup to look left
        pos = pass_cnt - 1
        #  shift larger elements to the right
        while pos >= 0 and tmp_list[pos] > key:
            tmp_list[pos + 1] = tmp_list[pos]
            pos -= 1
        # Insert our current term into the correct spot
        tmp_list[pos + 1] = key
    return tmp_list


def main():
    my_list = [5, 2, 4, 6, 1, 3]
    print(
        f"Sorte List:\n{insertion_sort(my_list)}"
    )
    print(f"Original list intact:\n{my_list}")


if __name__ == "__main__":
    main()
