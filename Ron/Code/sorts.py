import sys
import argparse
from local_functions import (
    chkstr_isnum,
    bubble_sort,
    insertion_sort,
)

debug = False


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
        help="If given will user insertion sort",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="If given print the list read in and then bubble sorted",
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
    verbose = (
        args.verbose if args.verbose else False
    )
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
            5,
            6,
            10,
            75,
            99,
            66,
            2,
            57,
            8,
            7,
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
            5,
            6,
            10,
            75,
            99,
            66,
            2,
            57,
            8,
            7,
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
        if verbose:
            print(
                f"Input list pre sort:\n\t{my_list}"
            )
            print(
                f"Output Bubble Sorted list\n\t{res_list}"
            )
        else:
            print(f"Bubble Sorted: {res_list}")
        if debug:
            print(
                f"Proof original list unchanged:\n\t{my_list}"
            )

    if insertion and args.list:
        res_list = insertion_sort(my_list)
        if verbose:
            print(
                f"Input list pre sort:\n\t{my_list}"
            )
            print(
                f"Output Bubble Sorted list\n\t{res_list}"
            )
        else:
            print(f"Insertion SortedL {res_list}")
        if debug:
            print(
                f"Proof original list unchanged:\n\t{my_list}"
            )


if __name__ == "__main__":
    main()
