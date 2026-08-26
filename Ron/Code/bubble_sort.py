import argparse

debug = False


def insert_sort(lst):
    pass_count = 0
    for pass_num in range(1, len(lst)):
        pos = pass_num
        while (
            pos > 0 and lst[pass_num] > lst[pos]
        ):
            lst[pos], lst[pos - 1] = (
                lst[pos - 1],
                lst[pos],
            )
            pos = pos - 1
            pass_count += 1
            print(lst)
    if debug:
        print(f"Passes made: {pass_count}")


def bubble_sort(lst):
    #    kinds = classify(lst)
    #    if kinds == (int, float):

    tmp_lst = lst.copy()
    pass_count = 0
    for pass_num in range(1, len(tmp_lst)):
        for pos in range(len(tmp_lst) - 1):
            if tmp_lst[pos] > tmp_lst[pos + 1]:
                tmp_lst[pos], tmp_lst[pos + 1] = (
                    tmp_lst[pos + 1],
                    tmp_lst[pos],
                )
            pass_count += 1

    if debug:
        print(f"Passes made: {pass_count}")
    return tmp_lst


def main():
    global debug

    def wide_formatter(prog):
        return (
            argparse.RawDescriptionHelpFormatter(
                prog,
                width=110,
                max_help_position=46,
            )
        )
        """_summary_
        """

    parser = argparse.ArgumentParser(
        description="Bubble Sort a list of coma seperated terms or default a demo",
        epilog="""\
Usage examples:
  bubble_sort.py -l <list,of,comma,separated,items>
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
    args = parser.parse_args()
    verbose = (
        args.verbose if args.verbose else False
    )
    debug = args.debug if args.debug else False

    if not args.list:
        print(insert_sort([5, 2, 4, 6, 1, 3]))
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
        my_list = [5, 2, 8, 1]
        print(
            f"my_list pre insertion sorted:\n\t{my_list}"
        )
        insert_sort(my_list)
        print(
            f"post insertion sorted list:\n\t{my_list}"
        )
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
        my_list = [3, 1, 4, 2]
        print(
            f"my_list pre bubble sort:\n\t{my_list}"
        )
        sorted_list = bubble_sort(my_list)
        print(
            f"post bubble sorted list:\n\t{sorted_list}"
        )
        print(
            f"verifying original list untouched:\n\t{my_list}"
        )
    else:
        my_list = args.list.split(",")
        assert my_list, "Error: Empty list given"
        res_list = bubble_sort(my_list)
        if verbose:
            print(
                f"Input list pre sort:\n\t{my_list}"
            )
            print(
                f"Output Bubble Sorted list\n\t{res_list}"
            )
        else:
            print(res_list)
    if debug:
        print(
            f"Proof orignal list unchanged:\n\t{my_list}"
        )


if __name__ == "__main__":
    main()
