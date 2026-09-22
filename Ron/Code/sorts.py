import argparse
from local_functions import Timed, chkstr_isnum

recurse_count = 0
debug = False


def partition(arr, low, high):
    # Choose the rightmost element as the pivot
    pivot = arr[high]

    # Index of the smaller element (tracks where the next small item should go)
    i = low - 1

    for j in range(low, high):
        # If the current element is smaller than or equal to the pivot
        if arr[j] <= pivot:
            i += 1
            # Swap elements
            arr[i], arr[j] = arr[j], arr[i]

    # Swap the pivot element with the greater element specified at i + 1
    arr[i + 1], arr[high] = arr[high], arr[i + 1]

    # Return the position where the partition was made
    return i + 1


@Timed
def quick_sort(arr, low, high):
    global recurse_count
    global debug
    recurse_count += 1
    local_loop = recurse_count
    if debug:
        print(f"In Recurse loop {recurse_count}")

    #    tmp_list = arr.copy()
    if low < high:
        # Find pivot element such that elements smaller than pivot are on the left
        # and elements greater than pivot are on the right
        pi = partition(arr, low, high)

        # Recursive call on the left of pivot
        quick_sort(arr, low, pi - 1)

        # Recursive call on the right of pivot
        quick_sort(arr, pi + 1, high)
    if debug:
        print(f" End Loop {local_loop}, list: {arr}")
    return arr


@Timed
def binary_search(nums, target):
    low = 0
    high = len(nums) - 1
    while low <= high:
        mid = (low + high) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1


@Timed
def insertion_sort(arr):
    global debug
    """ Takes a list and sorts a copy of it using insertion sort
        returns the sported list, leaving original intact
    """
    # Make a copy of the list
    pass_count = 0
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
        #           print(tmp_list)
        # Insert our current term into the correct spot
        tmp_list[pos + 1] = key

        pass_count += 1
        if debug:
            print(f"Insertion: inner loop {pass_count}: {tmp_list}")
    if debug:
        print(f"Insertion: after inner loop {pass_count}: {tmp_list}")
    return tmp_list


@Timed
def bubble_sort(lst):
    global debug
    tmp_lst = lst.copy()
    pass_count = 0
    for pass_num in range(1, len(tmp_lst)):
        for pos in range(len(tmp_lst) - 1):
            if tmp_lst[pos] > tmp_lst[pos + 1]:
                tmp_lst[pos], tmp_lst[pos + 1] = tmp_lst[pos + 1], tmp_lst[pos]
            if debug:
                print(f"Bubble: inside inner loop {pass_count}: {tmp_lst}")
        pass_count += 1
        if debug:
            print(f"Bubble: outside loop {pass_count}: {tmp_lst}")
    return tmp_lst


def main():
    global debug
    has_numbers = False
    has_strings = False

    def wide_formatter(prog):
        return argparse.RawDescriptionHelpFormatter(
            prog,
            width=110,
            max_help_position=46,
        )

    parser = argparse.ArgumentParser(
        description="Sort a list of coma separated terms or default a demo",
        epilog="""\
Usage examples:
  bubble_sort.py [-b and/or -i] -l <list,of,comma,separated,items>
  -b use bubble sort
  -i use insertion sort
""",
        formatter_class=wide_formatter,
    )

    parser.add_argument(
        "-l",
        "--list",
        metavar="",
        help="\tlist,of,comma,separated,items",
    )
    parser.add_argument(
        "-b",
        "--bubble",
        action="store_true",
        help="If given wll use bubble sort",
    )
    parser.add_argument(
        "-q",
        "--quick",
        action="store_true",
        help="If given wll use quick sort",
    )
    parser.add_argument(
        "-i",
        "--insert",
        action="store_true",
        help="If given will use insertion sort",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="If given prints debug statements",
    )
    parser.add_argument(
        "-de",
        "--demo",
        action="store_true",
        help="If given prints a demo",
    )

    args = parser.parse_args()
    debug = args.debug if args.debug else False
    bubble = args.bubble if args.bubble else False
    insertion = args.insert if args.insert else False
    demo_enabled = args.demo if args.demo else False
    quick = args.quick if args.quick else False

    if args.list:
        my_list = args.list.split(",")
        assert my_list, "Error: Empty list given"

        for idx, my_args in enumerate(my_list):
            if chkstr_isnum(my_args) == "int":
                my_list[idx] = int(my_args)
                has_numbers = True
            elif chkstr_isnum(my_args) == "float":
                my_list[idx] = float(my_args)
                has_numbers - True
            else:
                has_strings = True
        assert not (has_strings and has_numbers), (
            "Error: Can't sort strings and numbers together"
        )

    if (insertion and not args.list) or demo_enabled:
        my_list = [2, 3, 4, 7, 9, 5, 10, 11, 6]
        print(f"my_list pre insertion sorted:\n{my_list}")
        sorted_list = insertion_sort(my_list)
        print(f"post insertion sorted list:\n{sorted_list}")
        print(f"verifying original list untouched:\n{my_list}")
        print("Elapsed:", insertion_sort.elapsed)
    if (bubble and not args.list) or demo_enabled:
        my_list = [
            2,
            3,
            4,
            7,
            9,
            5,
            10,
            11,
        ]
        print(f"my_list pre bubble sort:\n{my_list}")
        sorted_list = bubble_sort(my_list)
        print(f"post bubble sorted list:\n{sorted_list}")
        print(f"verifying original list untouched:\n{my_list}")
        print("Elapsed:", bubble_sort.elapsed)
    if (quick and not args.list) or demo_enabled:
        my_list = [2, 3, 99, 1, 55, 6, 77, 11]
        print(f"my_list pre quick sort:\n{my_list}")
        sorted_list = quick_sort(my_list, 0, len(my_list) - 1)
        print(f"post quick sorted list:\n{sorted_list}")
        print(f"verifying original list was sorted in place:\n{my_list}")
        print("Elapsed:", quick_sort.elapsed)
    if bubble and args.list:
        res_list = bubble_sort(my_list, 0, len(my_list) - 1)
        if debug:
            print(f"Input list pre sort:\n\t{my_list}")
            print(f"Output Bubble Sorted list\n\t{res_list}")
            print(f"Proof original list unchanged:\n\t{my_list}")
        else:
            print(f"Bubble Sorted: {res_list}")

    if insertion and args.list:
        res_list = insertion_sort(my_list)
        if debug:
            print(f"Input list pre sort:\n\t{my_list}")
            print(f"Output Insertion Sorted list\n\t{res_list}")
            print(f"Proof original list unchanged:\n\t{my_list}")
        else:
            print(f"Insertion Sorted: {res_list}")

    if quick and args.list:
        res_list = quick_sort(my_list, 0, len(my_list) - 1)
        if debug:
            print(f"Input list pre sort:\n\t{my_list}")
            print(f"Output quick Sorted list\n\t{res_list}")
            print(f"Proof original list was sorted in place\n\t{my_list}")
        else:
            print(f"quick Sorted: {res_list}")
    # Example usage:


if __name__ == "__main__":
    main()
