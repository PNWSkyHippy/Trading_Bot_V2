import sys
import argparse
from local_functions import (
    chkstr_isnum,
#    bubble_sort,
#    insertion_sort,
)

debug = True

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

def insertion_sort(arr):
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
            tmp_list[pos+1] = tmp_list[pos]
            pos -= 1
 #           print(tmp_list)
        # Insert our current term into the correct spot
        tmp_list[pos+1] =key

        pass_count += 1        
        if debug:
            print(f'Insertion: inner loop {pass_count}: {tmp_list}')
    if debug:
        print(f'Insertion: after inner loop {pass_count}: {tmp_list}')
    return(tmp_list)
    
    
def bubble_sort(lst):
    tmp_lst = lst.copy()
    pass_count = 0
    for pass_num in range(1,len(tmp_lst)):
        for pos in range(len(tmp_lst) - 1):
            if tmp_lst[pos] > tmp_lst[pos + 1]:
                tmp_lst[pos], tmp_lst[pos+1] = tmp_lst[pos+1], tmp_lst[pos]
            if debug:
                print(f'Bubble: inside inner loop {pass_count}: {tmp_lst}')
        pass_count += 1
        if debug:
            print(f'Bubble: outside loop {pass_count}: {tmp_lst}')
    return tmp_lst


def main():
    has_numbers = False
    has_strings = False

    def wide_formatter(prog):
        return (
            argparse.RawDescriptionHelpFormatter(
                prog,
                width=110,
                max_help_position=46,
            )
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
    insertion = (
        args.insert if args.insert else False
    )
    demo_enabled = (
        args.demo if args.demo else False
    )
    if args.list:
        my_list = args.list.split(",")
        assert my_list, "Error: Empty list given"

        for idx, my_args in enumerate(my_list):
            if chkstr_isnum(my_args) == "float":
                my_list[idx] = float(my_args)
                has_numbers = True
            elif chkstr_isnum(my_args) == "int":
                my_list[idx] = int(my_args)
                has_numbers - True
            else:
                has_strings = True
        assert not (
            has_strings and has_numbers
        ), "Error: Can't sort strings and numbers together"

    if (
        insertion and not args.list
    ) or demo_enabled:
    
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
        print(
            f"my_list pre insertion sorted:\n{my_list}"
        )
        sorted_list = insertion_sort(my_list)
        print(
            f"post insertion sorted list:\n{sorted_list}"
        )
        print(
            f"verifying original list untouched:\n{my_list}"
        )

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
        print(
            f"my_list pre bubble sort:\n{my_list}"
        )
        sorted_list = bubble_sort(my_list)
        print(
            f"post bubble sorted list:\n{sorted_list}"
        )
        print(
            f"verifying original list untouched:\n{my_list}"
        )

    if bubble and args.list:
        res_list = bubble_sort(my_list)
        if debug:
            print(
                f"Input list pre sort:\n\t{my_list}"
            )
            print(
                f"Output Bubble Sorted list\n\t{res_list}"
            )
            print(
                f"Proof original list unchanged:\n\t{my_list}"
            )
        else:
            print(f"Bubble Sorted: {res_list}")

    if insertion and args.list:
        res_list = insertion_sort(my_list)
        if debug:
            print(
                f"Input list pre sort:\n\t{my_list}"
            )
            print(
                f"Output Insertion Sorted list\n\t{res_list}"
            )
            print(
                f"Proof original list unchanged:\n\t{my_list}"
            )
        else:
            print(f"Insertion SortedL {res_list}")


if __name__ == "__main__":
    main()
