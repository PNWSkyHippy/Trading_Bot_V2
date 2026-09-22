import sys
import re
import argparse
import os
import logging

colors = {
    # Text Modifiers
    "clear": "\033[0m",
    "bold": "\033[1m",
    "blink": "\033[5m",
    # Foreground (Text) Colors
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    # Background Block Colors
    "bg_red": "\033[41m",
    "bg_green": "\033[42m",
    "bg_yellow": "\033[43m",
    "bg_blue": "\033[44m",
    "bg_magenta": "\033[45m",
    "bg_cyan": "\033[46m",
    "bg_black": "\033[40m",
    "bg_white": "\033[47m",
}

# Flawless regex compilation targeting all ANSI controls
ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
STAT_LABEL_VALUE_RE = re.compile(
    r"([A-Za-z][\w &/%]*:)\s+(.*?)(?=(?:\s{2,}[A-Za-z][\w &/%]*:)|\s*$)"
)


class SkipErrors(logging.Filter):
    """Keep INFO/WARNING on stdout; errors go to stderr instead."""

    def filter(self, record):
        return record.levelno < logging.ERROR


def setup_logging(log_filename: str) -> logging.Logger:
    """Route debug to the log file, info/warning to stdout, error+ to stderr."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    file_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_fmt = logging.Formatter("%(message)s")

    log_dir = os.path.dirname(log_filename)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_fmt)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.addFilter(SkipErrors())
    stdout_handler.setFormatter(console_fmt)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(file_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)
    return logger


def clean_ansi(text):
    """Safely extracts all terminal control sequences out of an output file string."""
    #    text = ANSI_EQUALS_RE.sub("", str(text))
    return ANSI_ESCAPE_RE.sub("", str(text))


def colorize(
    my_str,
    text_col=None,
    bg_col=None,
    bold=False,
    blink=False,
):
    # Dynamic list to hold active ANSI numeric codes
    codes = []

    if bold:
        codes.append("1")
    if blink:
        codes.append("5")

    if text_col:
        if text_col not in colors:
            raise ValueError(f"Invalid text color: {text_col}")
        # Extract just the number from the string (e.g., '\033[31m' -> '31')
        codes.append(colors[text_col].strip("\033[m"))

    if bg_col:
        if bg_col not in colors:
            raise ValueError(f"Invalid background color: {bg_col}")
        codes.append(colors[bg_col].strip("\033[m"))

    # If no styles are passed, return the plain string
    if not codes:
        return str(my_str)

    # Merge codes with semicolons (e.g., \033[1;5;31;40m)
    prefix = f"\033[{';'.join(codes)}m"
    return f"{prefix}{my_str}{colors['clear']}"


def parse_time(mtime: str) -> tuple[int, int]:
    if not isinstance(mtime, str):
        raise TypeError("Time must be a string in HH:MM format")

    parts = mtime.strip().split(":")

    if len(parts) != 2:
        raise ValueError("Time must be in HH:MM format")

    hour_text, minute_text = parts

    if not hour_text or not minute_text:
        raise ValueError("Both hour and minute are required")

    if not hour_text.isdigit() or not minute_text.isdigit():
        raise ValueError("Hour and minute must be numbers")

    hour = int(hour_text)
    minute = int(minute_text)

    if not 0 <= hour <= 23:
        raise ValueError("Hour must be between 0 and 23")

    if not 0 <= minute <= 59:
        raise ValueError("Minute must be between 0 and 59")

    return hour, minute


def parse_date(mday: str) -> tuple[int, int]:
    if not isinstance(mday, str):
        raise TypeError("Date must be a string in YYYY-MM-DD format")

    parts = mday.strip().split("-")

    if len(parts) != 3:
        raise ValueError("Date must be in YYYY-MM-DD format")

    year_text, month_text, day_text = parts

    if not year_text or not month_text or not day_text:
        raise ValueError("Year and Monh and Day are required")

    if not year_text.isdigit() or not month_text.isdigit() or not day_text.isdigit():
        raise ValueError("Year, Month, and Day must be numbers")

    year = int(year_text)
    month = int(month_text)
    day = int(day_text)

    if not 1980 <= year <= 4000:
        raise ValueError("Year must be between 1980 and 4000")

    if not 1 <= month <= 12:
        raise ValueError("Month must be between 1 and 12")

    if not 1 <= day <= 31:
        raise ValueError("Day must be between 1 and 31")

    return year, month, day


def date_check(mdate):
    try:
        mdate, mtime = mdate.split("T")
    except ValueError:
        return False

    try:
        parse_time(mtime)
        parse_date(mdate)
    except (TypeError, ValueError):
        return False

    return True


def chkstr_isnum(value: str) -> str:
    """
    Distinguishes if a string represents an integer or a float.
    Returns 'float', 'int', or 'str'.
    """
    try:
        # First, ensure it is a valid numeric structure
        f = float(value)

        # Check if a decimal point exists in the string to confirm it's a float
        # This correctly marks "9.0" as float and "9" as int
        if str(value).find("."):
            return "float"

        # Handle scientific notation (e.g., "1e3"), which results in a float
        #        elif "e" in value.lower():
        #            return "float"

        else:
            return "int"

    except ValueError:
        return "str"


def can_to_float(value: str) -> bool:
    """Returns True if the string can be parsed into a float."""
    try:
        float(value)
        return True
    except ValueError:
        return False


def can_to_int(value: str) -> bool:
    """Returns True if the string can be parsed into an integer."""
    try:
        int(value)
        return True
    except ValueError:
        return False


def classify(args):
    """
    kinds = classify(sys.argv[1:])
    kinds == {int}          # all ints
    kinds == {float}        # all floats
    kinds == {int, float}   # mix of ints/floats
    kinds == {str}          # all strings
    str in kinds and (int in kinds or float in kinds)  # mixed strings + numbers
    """
    kinds = set()
    for x in args:
        try:
            int(x)
            kinds.add(int)
        except ValueError:
            try:
                float(x)
                kinds.add(float)
            except ValueError:
                kinds.add(str)
    return kinds


debug = False


def insertion_sort(arr):
    """Takes a list and sorts a copy of it susing insertion sort
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
            pass_count += 1

        # Insert our current term into the correct spot
        tmp_list[pos + 1] = key
        if debug:
            print(f"inner loop {pass_count}: {tmp_list}")
    if debug:
        print(f"after inner loop {pass_count}: {tmp_list}")
        print(f"Passes made: {pass_count}")
    return tmp_list


def bubble_sort(lst):

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
            print(f"inside inner loop {pass_count}: {tmp_lst}")
    if debug:
        print(f"after all loops {pass_count}: {tmp_lst}")
        print(f"Passes made: {pass_count}")
    return tmp_lst


def main():
    def wide_formatter(prog):
        return argparse.RawDescriptionHelpFormatter(
            prog,
            width=110,
            max_help_position=46,
        )

    parser = argparse.ArgumentParser(
        description="Colorize the input stream into a collorized output stream for terminal display.",
        epilog="""\
Usage examples:
    tcolorize.py -c red -b bg_black -B -k "Hello, World!"
    tcolirze.py -l list the available color opttions
    tcolorize.py --i <file name to read from>
    tcolorize.py -h
 """,
        formatter_class=wide_formatter,
    )

    parser.add_argument(
        "-i",
        "--infile",
        metavar="",
        help="path/toifile/to/parse and colorize based on the provided key",
    )
    parser.add_argument(
        "-c",
        "--color",
        metavar="",
        help="a color name from the list of available colors",
    )
    parser.add_argument(
        "-k",
        "--bkcolor",
        metavar="",
        help="a background color name from the list of available colors",
    )

    parser.add_argument(
        "-b",
        "--Bold",
        action="store_true",
        help="If given, the output will be bold",
    )
    parser.add_argument(
        "-B",
        "--blink",
        action="store_true",
        help="If given, the output will blink",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="If given, the output will list available colors",
    )
    args = parser.parse_args()

    if args.list:
        print("Available text colors:")
        for color in [
            "red",
            "green",
            "yellow",
            "blue",
            "magenta",
            "cyan",
        ]:
            print(f"  {color}")
        print("\nAvailable background colors:")
        for color in [
            "bg_red",
            "bg_green",
            "bg_yellow",
            "bg_blue",
            "bg_magenta",
            "bg_cyan",
            "bg_black",
            "bg_white",
        ]:
            print(f"  {color}")
        sys.exit()

    if args.color:
        if args.color not in colors:
            print(f"Invalid text color: {args.color}")
            sys.exit(1)
        else:
            text_color = args.color
    else:
        text_color = None
    if args.bkcolor:
        if args.bkcolor not in colors:
            print(f"Invalid background color: {args.bkcolor}")
            sys.exit(1)
        else:
            bg_color = args.bkcolor
    else:
        bg_color = None

    if args.Bold:
        bold = True
    else:
        bold = False

    if args.blink:
        blink = True
    else:
        blink = False

    if args.infile:
        try:
            with open(args.infile, "r") as f:
                content = f.read()
                print(
                    colorize(
                        content,
                        text_col=text_color,
                        bg_col=bg_color,
                        bold=bold,
                        blink=blink,
                    )
                )
        except FileNotFoundError:
            print(f"File not found: {args.infile}")
            sys.exit(1)
    else:
        for line in sys.stdin:
            if line == "\n":  # end of file and exit if found
                break
            else:  # still here? Only store lines containing the search pattern
                print(
                    colorize(
                        line,
                        text_col=text_color,
                        bg_col=bg_color,
                        bold=bold,
                        blink=blink,
                    ),
                    end="",
                )
    sys.exit()


if __name__ == "__main__":
    main()
