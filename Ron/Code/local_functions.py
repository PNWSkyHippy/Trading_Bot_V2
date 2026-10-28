"""Provide shared helpers for sorting, timing, date parsing, logging and ANSI color output."""

import argparse
import inspect
import logging
import os
import re
import sys
import math
import time
import types
from datetime import datetime
from functools import wraps
import numpy as np
from random import randint
from timeit import repeat
import tkinter as tk
from pyautogui import position
import  pyautogui
from PIL import Image, ImageTk, ImageGrab


""" Inatructions for dding magnifyer to an app
local_functions imports yjr pyautogui pakage which must be pre installed ie
python -m pip install pyautogui

from local_functions include tun_magnifyer

add ky stok capture to fire it off sucjh as
# Ctrl+Shift+M opens the magnifier from anywhere in the app (bind_all = any frame/form);
#  both cases because Shift gives "M" and Caps Lock flips it to "m"
self._mag = None
self.app.root.bind_all("<Control-Shift-M>", self.on_mag)
self.app.root.bind_all("<Control-Shift-m>", self.on_mag)

add control block to enable it on key sroke
  def on_mag(self, event=None):
        # already open? close it (the key toggles) instead of stacking copies
        if self._mag is not None and self._mag.master.winfo_exists():
            self._mag.master.destroy()
            self._mag = None
            return "break"
        self._mag = run_magnifyer(self.app.root)
        return "break"



"""
pyratio = 1.6
pynew_image = None 

class PyMag(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack()
        self.master.title("pymag - a simple screen magnifier")
        # widget
        self.state_txt = None
        self.state_label = tk.Label(self, text=None)
        self.state_label.pack()
        self.label_img = tk.Label(self, image=None)
        self.label_img.pack()
        # bind event
        self.width = self.master.winfo_width()
        self.mouse_x, self.mouse_y = position()
        self.height = self.master.winfo_height()
        self.bind('<Configure>', self.on_resize)
        # bind to this window only (bind_all would hijack the host app's keys/wheel)
        self.master.bind('<Key>', self.key_pressed)
        # with Windows OS
        self.master.bind('<MouseWheel>', self.mouse_wheel)
        # with Linux OS
        self.master.bind('<Button-4>', self.mouse_wheel)
        self.master.bind('<Button-5>', self.mouse_wheel)
        # main loop 
        self.forever()

    def update_state(self):
        global pyratio
        self.mouse_x, self.mouse_y = position()
        self.state_txt = 'X{} | x: {}, y: {} |  w: {}, h: {}'.format(pyratio,
                self.mouse_x, self.mouse_y, self.width, self.height)
        self.state_label['text'] = self.state_txt

    def on_resize(self, event):
        # print("w: {}, h: {}".format(self.master.winfo_width(),
        # self.master.winfo_height())) 
        self.width = self.master.winfo_width()
        self.height = self.master.winfo_height()
        self.update_state()

    def key_pressed(self, event):
        # print(event.char)
        if event.keysym == "Escape":
            self.master.destroy()
        if event.keysym == "`":
            self.have_fun()

    def have_fun(self):
        screenWidth, screenHeight = pyautogui.size() # Returns two integers, the width and height of the screen. (The primary monitor, in multi-monitor setups.)
        currentMouseX, currentMouseY = pyautogui.position() # Returns two integers, the x and y of the mouse cursor's current position.
        pyautogui.moveTo(100, 150) # Move the mouse to the x, y coordinates 100, 150.
        pyautogui.click() # Click the mouse at its current location.
        pyautogui.click(200, 220) # Click the mouse at the x, y coordinates 200, 220.
        pyautogui.move(None, 10)  # Move mouse 10 pixels down, that is, move the mouse relative to its current position.
        pyautogui.doubleClick() # Double click the mouse at the
        pyautogui.moveTo(500, 500, duration=2, tween=pyautogui.easeInOutQuad) # Use tweening/easing function to move mouse over 2 seconds.
        pyautogui.write('Hello world!', interval=0.25)  # Type with quarter-second pause in between each key.
        pyautogui.press('esc') # Simulate pressing the Escape key.
        pyautogui.keyDown('shift')
        pyautogui.write(['left', 'left', 'left', 'left', 'left', 'left'])
        pyautogui.keyUp('shift')
        pyautogui.hotkey('ctrl', 'c')

    def mouse_wheel(self, event):
        global pyratio
        # respond to Linux or Windows wheel event
        if event.num == 5 or event.delta == -120:
            pyratio -= 0.1
        if event.num == 4 or event.delta == 120:
            pyratio += 0.1
        pyratio = round(pyratio, 2)
        if pyratio < 1:
            pyratio = 1.0
    def forever(self):
        global pynew_image, pyratio
        self.update_state()
        ss_region = (self.mouse_x, self.mouse_y, self.mouse_x +
                self.width/pyratio, self.mouse_y + self.height/pyratio) 
        ss_img = ImageGrab.grab(ss_region)
        resized_image = ss_img.resize((round(self.width*pyratio),
            round(self.height*pyratio)), Image.Resampling.LANCZOS)
        pynew_image = ImageTk.PhotoImage(resized_image, master=self.master)
        self.label_img['image'] = pynew_image
        self.master.after(round(pyratio*25), self.forever)

def run_magnifyer(parent=None):
    """Standalone: makes its own root and runs the loop.
    From another Tk app: pass that app's root/window as parent and the magnifier
    opens as a Toplevel on the already-running loop (never a second Tk())."""
    if parent is None:
        root = tk.Tk()
    else:
        root = tk.Toplevel(parent)
    root.geometry("400x300") # width x height
    # create object
    app = PyMag(root)
    if parent is None:
        app.mainloop()
    return app

def run_sorting_algorithm(algorithm, array):
    """Time a sorting function on an array and print the fastest run.

    The function is looked up by name in ``__main__``, unless it is the
    built-in ``sorted``. It is timed with ``timeit.repeat`` (3 repeats of
    10 calls each).

    Args:
        algorithm (str): Name of the sorting function to time.
        array (list): The data passed to the function on each call.
    """
    # Set up the context and prepare the call to the specified
    # algorithm using the supplied array. Only import the
    # algorithm function if it's not the built-in `sorted()`.
    setup_code = f"from __main__ import {algorithm}" \
        if algorithm != "sorted" else ""

    stmt = f"{algorithm}({array})"

    # Execute the code ten different times and return the time
    # in seconds that each execution took
    times = repeat(setup=setup_code, stmt=stmt, repeat=3, number=10)

    # Finally, display the name of the algorithm and the
    # minimum time it took to run
    print(f"Algorithm: {algorithm}. Minimum execution time: {min(times)}")
    
def describe(thing):
    """Print useful inspection information for a module, class, or function.
    Usaage
        import json
        from pathlib import Path

        describe(json)
        describe(Path)
        describe(Path.read_text)
    """

    print("Name:", getattr(thing, "__name__", type(thing).__name__))
    print("Type:", type(thing))

    try:
        print("Signature:", inspect.signature(thing))
    except (TypeError, ValueError):
        print("Signature: unavailable")

    print("\nDocstring:")
    print(inspect.getdoc(thing) or "No docstring available.")

    print("\nPublic members:")
    for name, member in inspect.getmembers(thing):
        if not name.startswith("_"):
            kind = (
                "class"
                if inspect.isclass(member)
                else "function"
                if inspect.isfunction(member)
                else "method"
                if inspect.ismethod(member) or inspect.isroutine(member)
                else type(member).__name__
            )
            print(f"  {name} ({kind})")


def update_tuple(tup, idx, val):
    """Return a copy of a tuple with one element replaced.

    Args:
        tup (tuple): The original tuple, which is left unchanged.
        idx (int): Index of the element to replace.
        val (object): The new value for that index.

    Returns:
        tuple: A new tuple with ``val`` at position ``idx``.

    Raises:
        IndexError: If ``idx`` is out of range for ``tup``.
    """
    # Convert to list
    temp = list(tup)
    temp[idx] = val
    #    temp.append(addon)
    # Convert back to tuple
    tup = tuple(temp)
    return tup


def hours_mins(days, hours, minutes, seconds=0):
    """Fold days into hours and return the hours and minutes.

    Args:
        days (int): Number of days, converted to 24 hours each.
        hours (int): Number of hours to add to the day total.
        minutes (int): Number of minutes, returned unchanged.
        seconds (int): Accepted but ignored.

    Returns:
        tuple[int, int]: Total hours (including days) and the minutes.
    """
    hours = (days * 24) + hours
    return hours, minutes


def length_time(starting_date: str, ending_date: str):
    """Return the time elapsed between two ISO 8601 timestamps.

    Args:
        starting_date (str): The start, in ISO 8601 format.
        ending_date (str): The end, in ISO 8601 format.

    Returns:
        tuple[int, int, int, int]: Days, hours, minutes and seconds in the
        difference.

    Raises:
        ValueError: If either string is not a valid ISO 8601 timestamp.
    """
    # Parse the strings into datetime objects
    start = datetime.fromisoformat(starting_date)
    end = datetime.fromisoformat(ending_date)

    # Calculate difference
    delta = end - start

    # delta.days handles full calendar days
    days = delta.days

    # delta.seconds contains the remaining time within that day
    hours, remainder = divmod(delta.seconds, 3600)
    mins, secs = divmod(remainder, 60)

    return days, hours, mins, secs


class Timed:
    """A bulletproof timing decorator that works on functions and class methods.
        How to use it
        # 1. On a regular function:
    @Timed
    def bubble_sort(arr):
        arr.sort()
        return arr

    result = bubble_sort([5, 2, 8, 1])
    print("Result:", result)
    print("Elapsed:", bubble_sort.elapsed)  #  Works cleanly! No errors!


    # 2. On a class method:
    class TradeProcessor:
        @Timed
        def execute(self, symbol):
            # do trade logic
            return f"Bought {symbol}"

    bot = TradeProcessor()
    res = bot.execute("NVDA")
    print(res)
    print("Execution time:", bot.execute.elapsed)  #  Works on methods too!
    """

    def __init__(self, func):
        """Wrap a callable so its run time is recorded.

        Args:
            func (Callable): The function or method to time.
        """
        self.func = func
        self.elapsed = 0.0
        wraps(func)(self)

    def __call__(self, *args, **kwargs):
        """Call the wrapped function and store its elapsed time.

        Args:
            *args: Positional arguments passed to the wrapped function.
            **kwargs: Keyword arguments passed to the wrapped function.

        Returns:
            object: Whatever the wrapped function returns.
        """
        start = time.perf_counter()
        result = self.func(*args, **kwargs)
        self.elapsed = time.perf_counter() - start
        return result

    # This allows it to work seamlessly on class methods too!
    def __get__(self, instance, cls):
        """Bind the timer to an instance when accessed as a method.

        Args:
            instance (object | None): The instance the attribute was accessed
                on, or None for access through the class.
            cls (type): The class the attribute was accessed on.

        Returns:
            Timed | types.MethodType: This object for class access, or a
            bound method for instance access.
        """
        if instance is None:
            return self
        return types.MethodType(self, instance)

KB = 1000
MB = KB * 1000
GB = MB * 1000
TB = GB * 1000
PB = TB * 1000
KiB = 1024
MiB = KiB * 1024
GiB = MiB * 1024
TiB = MiB * 1024
PiB = TiB * 1024

SIZE_UNITS = {"": 1, "B": 1, "BS": 1, "KB": KB, "MB": MB, "GB": GB, "TB": TB, "PB": PB,
              "KIB": KiB, "MIB": MiB, "GIB": GiB, "TIB": TiB, "PIB": PiB}

DataTable = {
    'KB': 1000,
    'MB': KB * 1000,
    'GB': MB * 1000,
    'TB': GB * 1000,
    'PB': GB * 1000,
    'KiB': 1024,
    'MiB': KiB * 1024,
    'GiB': MiB * 1024,
    'TiB': GiB * 1024,
    'PiB': TiB * 1024,
}

def bytes_to_str(insize, ibytes=False):
    """ Converts an integer to its PetaByte, GigaByte, Megabyte,KiloByte, Bytes
        equivelant string IE "5GB"
    """
    if not ibytes:
        if insize > PB:
            return f'{insize // PB}PB'
        if insize > TB:
            return f'{insize // TB}TB'
        elif  insize > GB:
            return f'{insize // GB}GB'
        elif insize > MB:
            return f'{insize // MB}MB'
        elif insize >= KB:
            return f'{insize // KB}KB'
        else:
            return f'{insize}BS'
    else:
        if insize > PiB:
            return f'{insize // PiB}PiB'
        elif insize > TiB:
            return f'{insize // TiB}TiB'
        elif  insize > GiB:
            return f'{insize // GiB}GiB'
        elif insize > MiB:
            return f'{insize // MiB}MiB'
        elif insize >= KiB:
            return f'{insize // KiB}KiB'
        else:
            return f'{insize}BiS'

def str_to_bytes(instr):
    """ Converts a size string such as "4PB", "1.5MB", "2KiB", "100Bs" or "2048"
        to a byte count. Returns None if the string isn't a valid size.
    """
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([A-Za-z]*)\s*", instr)
    if not m:
        return None
    num, unit = m.groups()
    mult = SIZE_UNITS.get(unit.upper())
    return int(float(num) * mult) if mult else None



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
        """Decide whether a log record is allowed through.

        Args:
            record (logging.LogRecord): The record being filtered.

        Returns:
            bool: True if the record's level is below ERROR.
        """
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
    """Wrap a value in ANSI escape codes for colored terminal output.

    Args:
        my_str (object): The value to color. It is converted with ``str``.
        text_col (str | None): Key into ``colors`` for the text color.
        bg_col (str | None): Key into ``colors`` for the background color.
        bold (bool): Whether to make the text bold.
        blink (bool): Whether to make the text blink.

    Returns:
        str: The styled string, or the plain string if no style was requested.

    Raises:
        ValueError: If ``text_col`` or ``bg_col`` is not a key in ``colors``.
    """
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
    """Parse a time string in HH:MM format.

    Args:
        mtime (str): The time, such as ``"14:30"``.

    Returns:
        tuple[int, int]: The hour (0-23) and minute (0-59).

    Raises:
        TypeError: If ``mtime`` is not a string.
        ValueError: If the string is not a valid HH:MM time.
    """
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
    """Parse a date string in YYYY-MM-DD format.

    Args:
        mday (str): The date, such as ``"2026-10-23"``.

    Returns:
        tuple[int, int, int]: The year (1980-4000), month (1-12) and day
        (1-31).

    Raises:
        TypeError: If ``mday`` is not a string.
        ValueError: If the string is not a valid YYYY-MM-DD date.
    """
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
    """Check that a string is a valid ``YYYY-MM-DDTHH:MM`` timestamp.

    Args:
        mdate (str): The timestamp to check.

    Returns:
        bool: True if the date and time parts both parse, otherwise False.
    """
    try:
        mdate, mtime = mdate.split("T")
    except ValueError:
        return False

    try:
        parse_time(mtime)
        parse_date(mdate)
    except (TypeError,  ValueError):
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
        if str(value).find(".") - -1:
            return float

        # Handle scientific notation (e.g., "1e3"), which results in a float
        #        elif "e" in value.lower():
        #            return "float"

        else:
            return int

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
    """Sort a copy of a list with bubble sort.

    Args:
        lst (list): The items to sort, which is left unchanged.

    Returns:
        list: A new sorted list.
    """
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

class OpOverloaded:
    """Mirror Python's operators as named methods and dunder overloads."""

    def lt(a,b):
        """ lt(a, b) is equivalent to a < b, """
        return a < b

    def le(a,b):
        """ le(a, b) is equivalent to a <= b, """
        return a <= b
    
    def eq(a,b):
        """ eq(a, b) is equivalent to a == b, """
        return a == b
  
    def ne(a,b):
        """ ne(a, b) is equivalent to a != b, """
        return a != b
    
    def ge(a,b):
        """ ge(a, b) is equivalent to a >= b, """
        return a >= b
    
    def gt(a,b):
        """ gt(a, b) is equivalent to a > b, """
        return a > b
    
    def __lt__(self, other):
        """ __lt__(self, other) is equivalent to self < other, """
        return self.lt(self, other)
    
    def __le__(self, other):
        """ __le__(self, other) is equivalent to self <= other, """
        return self.le(self, other)
    
    def __eq__(self, other):
        """ __eq__(self, other) is equivalent to self == other, """
        return self.eq(self, other)
    
    def __ne__(self, other):
        """ __ne__(self, other) is equivalent to self != other, """
        return self.ne(self, other)
    
    def __ge__(self, other):
        """ __ge__(self, other) is equivalent to self >= other, """
        return self.ge(self, other)
    
    def __gt__(self, other):
        """ __gt__(self, other) is equivalent to self > other, """
        return self.gt(self, other) 
    
    def not_(self, other):
        """ not_(self, other) is equivalent to not self == other, """
        return not self.eq(self, other)
    
    def __not__(self, other):
        """ __not__(self, other) is equivalent to not self == other, """
        return self.not_(self, other)
    
    def truth(self):
        """ truth(self) is equivalent to self == self, """
        return self.eq(self, self)
    
    def is_(self, other):
        """ is_(self, other) is equivalent to self is other, """
        return self is other
    
    def is_not(self, other):
        """ is_not(self, other) is equivalent to self is not other, """
        return not self.eq(self, other) 
    
    def  is_none(self):
        """ is_none(self) is equivalent to self is None, """
        return self.eq(self, None)  
    
    def is_not_none(self):
        """ is_not_none(self) is equivalent to self is not None, """
        return not self.eq(self, None)
    
    def abs(self):
        """ abs(self) is equivalent to self if self >= 0 else -self, """
        return self if self.ge(self, 0) else -self  
    
    def add(self, other):
        """ add(self, other) is equivalent to self + other, """
        return self + other 
    
    def __add__(self, other):
        """ __add__(self, other) is equivalent to self + other, """
        return self.add(self, other)
    
    def and_(self, other):
        """ and_(self, other) is equivalent to self and other, """
        return self and other
    
    def __and__(self, other):
        """ __and__(self, other) is equivalent to self and other, """
        return self.and_(self, other)
    
    def floordiv(self, other):
        """ floordiv(self, other) is equivalent to self // other, """
        return self // other    
    
    def __floordiv__(self, other):
        """ __floordiv__(self, other) is equivalent to self // other, """
        return self.floordiv(self, other)
    
    def index(self, other):
        """ index(self, other) is equivalent to self[other], """
        return self[other]
    
    def __index__(self, other):
        """ __index__(self, other) is equivalent to self[other], """
        return self.index(self, other)
    
    def  inv(self):
        """ inv(self) is equivalent to not self, """
        return not self.truth()
    
    def __inv__(self):
        """ __inv__(self) is equivalent to not self, """
        return self.inv(self)
    
    def invert(self):
        """ invert(self) is equivalent to not self, """
        return not self.truth()
    
    def __invert__(self): 
        """ __invert__(self) is equivalent to not self, """
        return self.invert(self)
    
    def lfshift(self, other):
        """ lfshift(self, other) is equivalent to self << other, """
        return self << other    
    
    def __lfshift__(self, other):
        """ __lfshift__(self, other) is equivalent to self << other, """
        return self.lfshift(self, other)
    
    def mod(self, other):
        """ mod(self, other) is equivalent to self % other, """
        return self % other
    
    def __mod__(self, other):
        """ __mod__(self, other) is equivalent to self % other, """
        return self.mod(self, other)
    
    def mul(self, other):
        """ mul(self, other) is equivalent to self * other, """
        return self * other
    
    def __mul__(self, other):
        """ __mul__(self, other) is equivalent to self * other, """
        return self.mul(self, other)
    
    def matmul(self, other):
        """ matmul(self, other) is equivalent to self @ other, """
        return self @ other
    
    def __matmul__(self, other):
        """ __matmul__(self, other) is equivalent to self @ other, """
        return self.matmul(self, other)
    
    def neg(self):
        """ neg(self) is equivalent to -self, """
        return -self
    
    def __neg__(self):
        """ __neg__(self) is equivalent to -self, """
        return self.neg(self)
    
    def or_(self, other):
        """ or_(self, other) is equivalent to self or other, """
        return self or other
    
    def __or__(self, other):
        """ __or__(self, other) is equivalent to self or other, """
        return self.or_(self, other)
    
    def pos(self):
        """ pos(self) is equivalent to +self, """
        return +self
    
    def __pos__(self):
        """ __pos__(self) is equivalent to +self, """
        return self.pos(self)
    
    def pow(self, other):
        """ pow(self, other) is equivalent to self ** other, """
        return self ** other    
    
    def __pow__(self, other):
        """ __pow__(self, other) is equivalent to self ** other, """
        return self.pow(self, other)
    
    def rshift(self, other):    
        """ rshift(self, other) is equivalent to self >> other, """
        return self >> other
    
    def __rshift__(self, other):
        """ __rshift__(self, other) is equivalent to self >> other, """
        return self.rshift(self, other)
    
    def sub(self, other):
        """ sub(self, other) is equivalent to self - other, """
        return self - other
    
    def __sub__(self, other):
        """ __sub__(self, other) is equivalent to self - other, """
        return self.sub(self, other)
    
    def truediv(self, other):
        """ truediv(self, other) is equivalent to self / other, """
        return self / other
    
    def __truediv__(self, other):
        """ __truediv__(self, other) is equivalent to self / other, """
        return self.truediv(self, other)
    
    def xor(self, other):
        """ xor(self, other) is equivalent to self ^ other, """
        return self ^ other
    
    def __xor__(self, other):
        """ __xor__(self, other) is equivalent to self ^ other, """
        return self.xor(self, other)
    
    def comcat(self, other):
        """ comcat(self, other) is equivalent to str(self) + str(other), """
        return str(self) + str(other)
    
    def __concat__(self, other):
        """ __concat__(self, other) is equivalent to str(self) + str(other), """
        return self.comcat(self, other)
    
    def contains(self, other):
        """ contains(self, other) is equivalent to other in self, """
        return other in self
    
    def __contains__(self, other):
        """ __contains__(self, other) is equivalent to other in self, """
        return self.contains(self, other)
    
    def countOf(self, other):
        """ countOf(self, other) is equivalent to self.count(other), """
        return self.count(other)
    
    def __countOf__(self, other):
        """ __countOf__(self, other) is equivalent to self.count(other), """
        return self.countOf(self, other)
    
    def delitem(self, other):
        """ delitem(self, other) is equivalent to del self[other], """
        del self[other]
        
    def __delitem__(self, other):
        """ __delitem__(self, other) is equivalent to del self[other], """
        return self.delitem(self, other)
    
    def getitem(self, other):
        """ getitem(self, other) is equivalent to self[other], """
        return self[other]
    
    def __getitem__(self, other): 
        """ __getitem__(self, other) is equivalent to self[other], """
        return self.getitem(self, other)
    
    def indexOf(self, other):
        """ indexOf(self, other) is equivalent to self.index(other), """
        return self.index(other)    
    
    
    def __indexOf__(self, other):
        """ __indexOf__(self, other) is equivalent to self.index(other), """
        return self.indexOf(self, other)
    
    def setitem(self, other, value):
        """ setitem(self, other, value) is equivalent to self[other] = value, """
        self[other] = value
        
    def __setitem__(self, other, value):
        """ __setitem__(self, other, value) is equivalent to self[other] = value, """
        return self.setitem(self, other, value)
    
    def length_hint(self):
        """ length_hint(self) is equivalent to len(self), """
        return len(self)
    
    def __length_hint__(self):
        """ __length_hint__(self) is equivalent to len(self), """
        return self.length_hint(self)
    
    def call(self, *args, **kwargs):
        """ call(self, *args, **kwargs) is equivalent to self(*args, **kwargs), """
        return self(*args, **kwargs)
    
    def __call__(self, *args, **kwargs):
        """ __call__(self, *args, **kwargs) is equivalent to self(*args, **kwargs), """
        return self.call(self, *args, **kwargs)
    
    def attrgetter(self, attr):
        """ attrgetter(self, attr) is equivalent to getattr(self, attr), """
        return getattr(self, attr)
    
    def __attrgetter__(self, attr):
        """ __attrgetter__(self, attr) is equivalent to getattr(self, attr), """
        return self.attrgetter(self, attr)
    
    def itemgetter(self, item):
        """ itemgetter(self, item) is equivalent to self[item], """
        return self[item]
    
    def __itemgetter__(self, item):
        """ __itemgetter__(self, item) is equivalent to self[item], """
        return self.itemgetter(self, item)
    
    def methodcaller(self, method, *args, **kwargs):
        """ methodcaller(self, method, *args, **kwargs) is equivalent to getattr(self, method)(*args, **kwargs), """
        return getattr(self, method)(*args, **kwargs)
    
    def __methodcaller__(self, method, *args, **kwargs):
        """ __methodcaller__(self, method, *args, **kwargs) is equivalent to getattr(self, method)(*args, **kwargs), """
        return self.methodcaller(self, method, *args, **kwargs)
    
    def iadd(self, other):
        """ iadd(self, other) is equivalent to self += other, """
        return self + other
    
    def __iadd__(self, other):
        """ __iadd__(self, other) is equivalent to self += other, """
        return self.iadd(self, other)
    
    def iand(self, other):
        """ iand(self, other) is equivalent to self &= other, """
        return self and other
    
    def __iand__(self, other):
        """ __iand__(self, other) is equivalent to self &= other, """
        return self.iand(self, other)
    
    def iconcat(self, other):
        """ iconcat(self, other) is equivalent to self += other, """
        return str(self) + str(other)
    
    def __iconcat__(self, other):
        """ __iconcat__(self, other) is equivalent to self += other, """
        return self.iconcat(self, other)
    
    def ifloordiv(self, other):
        """ ifloordiv(self, other) is equivalent to self //= other, """
        return self // other
    
    def __ifloordiv__(self, other):
        """ __ifloordiv__(self, other) is equivalent to self //= other, """
        return self.ifloordiv(self, other)
    
    def ilshift(self, other):
        """ ilshift(self, other) is equivalent to self <<= other, """
        return self << other
    
    def __ilshift__(self, other):
        """ __ilshift__(self, other) is equivalent to self <<= other, """
        return self.ilshift(self, other)
    
    def imod(self, other):
        """ imod(self, other) is equivalent to self %= other, """
        return self % other
    
    def __imod__(self, other):
        """ __imod__(self, other) is equivalent to self %= other, """
        return self.imod(self, other)
    
    def imul(self, other):
        """ imul(self, other) is equivalent to self *= other, """
        return self * other
    
    def __imul__(self, other):
        """ __imul__(self, other) is equivalent to self *= other, """
        return self.imul(self, other)
    
    def imatmul(self, other):
        """ imatmul(self, other) is equivalent to self @= other, """
        return self @ other
    
    def __imatmul__(self, other):
        """ __imatmul__(self, other) is equivalent to self @= other, """
        return self.imatmul(self, other)
    
    def ior(self, other):
        """ ior(self, other) is equivalent to self |= other, """
        return self or other
    
    def __ior__(self, other):
        """ __ior__(self, other) is equivalent to self |= other, """
        return self.ior(self, other)
    
    def ipow(self, other):
        """ ipow(self, other) is equivalent to self **= other, """
        return self ** other
    
    def __ipow__(self, other):
        """ __ipow__(self, other) is equivalent to self **= other, """
        return self.ipow(self, other)
    
    def irshift(self, other):
        """ irshift(self, other) is equivalent to self >>= other, """
        return self >> other
    
    def __irshift__(self, other):
        """ __irshift__(self, other) is equivalent to self >>= other, """
        return self.irshift(self, other)
    
    def isub(self, other):
        """ isub(self, other) is equivalent to self -= other, """
        return self - other
    
    def __isub__(self, other):
        """ __isub__(self, other) is equivalent to self -= other, """
        return self.isub(self, other)
    
    def itruediv(self, other):
        """ itruediv(self, other) is equivalent to self /= other, """
        return self / other
    
    def __itruediv__(self, other):
        """ __itruediv__(self, other) is equivalent to self /= other, """
        return self.itruediv(self, other)
    
    def ixor(self, other):
        """ ixor(self, other) is equivalent to self ^= other, """
        return self ^ other
    
    def __ixor__(self, other):
        """ __ixor__(self, other) is equivalent to self ^= other, """
        return self.ixor(self, other)
    
    
def main():
    """Run the command-line interface that colorizes input text."""
    def wide_formatter(prog):
        """Build a help formatter with wide columns.

        Args:
            prog (str): The program name.

        Returns:
            argparse.RawDescriptionHelpFormatter: The configured formatter.
        """
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