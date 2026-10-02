lengths_list = [
    "Meters",
    "Feet",
    "Yards",
    "Miles",
    "Inches",
    "Centimeters",
    "Millimeters",
    "KiloMeters",
    "Naut Miles",
    "Mils",
]

areas_list = [
    "acres",
    "area",
    "hectares",
    "square centimeters",
    "square feet",
    "square inches",
    "square meters",
]

volume_list = [
    "gallons us",
    "gallons ltr",
    "liters",
    "milliliters",
    "cubic meters",
    "cubic centimeters",
    "cubic inches",
    "cubic feet",
    "cubic yards",
]

mass_list = [
    "tons",
    "tons uk",
    "tons us",
    "pounds",
    "ounces",
    "kilograms",
    "grams",
]

data_list = [
    "bits",
    "bytes",
    "kilobytes",
    "kibibytes",
    "megabytes",
    "mebibytes",
    "gigabytes",
    "gibibytes",
    "terabytes",
    "tebibytes",
]

speed_list = [
    "Meters/sec",
    "Meters/min",
    "Meters/hour",
    "Kilometers/sec",
    "Kilometers/min",
    "Kilometers/hour",
    "Inches/sec",
    "Inches/min",
    "Inches/hour",
    "Feet/sec",
    "Feet/min",
    "Feet/hour",
    "Miles/sec",
    "Miles/min",
    "Miles/hour",
    "knots",
]

time_list = [
    "Seconds",
    "Minutes",
    "Hours",
    "Days",
    "Weeks",
    "Months",
    "Years",
]


def calc_areas(from_u, to_u, raw_val):
    _SQUARE_METERS_PER_UNIT = {
        "acres": 4046.8564224,
        "area": 1,
        "hectares": 10000,
        "square centimeters": 0.0001,
        "square feet": 0.09290304,
        "square inches": 0.00064516,
        "square meters": 1,
    }
    try:
        return raw_val * _SQUARE_METERS_PER_UNIT[from_u] / _SQUARE_METERS_PER_UNIT[to_u]
    except KeyError:
        return None


def calc_lengths(from_u, to_u, raw_val):
    _METERS_PER_UNIT = {
        "Meters": 1,
        "Feet": 0.3048,
        "Yards": 0.9144,
        "Miles": 1609.344,
        "Inches": 0.0254,
        "Centimeters": 0.01,
        "Millimeters": 0.001,
        "KiloMeters": 1000,
        "Naut Miles": 1852,
        "Mils": 0.0000254,
    }
    try:
        return raw_val * _METERS_PER_UNIT[from_u] / _METERS_PER_UNIT[to_u]
    except KeyError:
        return None


def calc_volume(from_u, to_u, raw_val):
    _CUBIC_METERS_PER_UNIT = {
        "gallons us": 0.00378541,
        "gallons ltr": 0.00454609,
        "liters": 0.001,
        "milliliters": 0.000001,
        "cubic meters": 1,
        "cubic centimeters": 0.000001,
        "cubic inches": 0.0000163871,
        "cubic feet": 0.0283168,
        "cubic yards": 0.764555,
    }
    try:
        return raw_val * _CUBIC_METERS_PER_UNIT[from_u] / _CUBIC_METERS_PER_UNIT[to_u]
    except KeyError:
        return None


def calc_mass(from_u, to_u, raw_val):
    _KILOGRAMS_PER_UNIT = {
        "tons": 907.18474,
        "tons uk": 1016.0469088,
        "tons us": 907.18474,
        "pounds": 0.45359237,
        "ounces": 0.0283495231,
        "kilograms": 1,
        "grams": 0.001,
    }
    try:
        return raw_val * _KILOGRAMS_PER_UNIT[from_u] / _KILOGRAMS_PER_UNIT[to_u]
    except KeyError:
        return None


def calc_data(from_u, to_u, raw_val):
    _BYTES_PER_UNIT = {
        "bits": 0.125,
        "bytes": 1,
        "kilobytes": 1024,
        "kibibytes": 1024,
        "megabytes": 1048576,
        "mebibytes": 1048576,
        "gigabytes": 1073741824,
        "gibibytes": 1073741824,
        "terabytes": 1099511627776,
        "tebibytes": 1099511627776,
    }
    try:
        return raw_val * _BYTES_PER_UNIT[from_u] / _BYTES_PER_UNIT[to_u]
    except KeyError:
        return None


def calc_speed(from_u, to_u, raw_val):
    _METERS_PER_SECOND_PER_UNIT = {
        "Meters/sec": 1,
        "Meters/min": 1 / 60,
        "Meters/hour": 1 / 3600,
        "Kilometers/sec": 1000,
        "Kilometers/min": 1000 / 60,
        "Kilometers/hour": 1000 / 3600,
        "Inches/sec": 0.0254,
        "Inches/min": 0.0254 / 60,
        "Inches/hour": 0.0254 / 3600,
        "Feet/sec": 0.3048,
        "Feet/min": 0.3048 / 60,
        "Feet/hour": 0.3048 / 3600,
        "Miles/sec": 1609.344,
        "Miles/min": 1609.344 / 60,
        "Miles/hour": 1609.344 / 3600,
        "knots": 1852 / 3600,
    }
    try:
        return (
            raw_val
            * _METERS_PER_SECOND_PER_UNIT[from_u]
            / _METERS_PER_SECOND_PER_UNIT[to_u]
        )
    except KeyError:
        return None


def calc_time(from_u, to_u, raw_val):
    _SECONDS_PER_UNIT = {
        "Seconds": 1,
        "Minutes": 60,
        "Hours": 3600,
        "Days": 86400,
        "Weeks": 604800,
        "Months": 2629800,  # Average month in seconds (30.44 days)
        "Years": 31557600,  # Average year in seconds (365.25 days)
    }
    try:
        return raw_val * _SECONDS_PER_UNIT[from_u] / _SECONDS_PER_UNIT[to_u]
    except KeyError:
        return None

btn_layout = [
    ["()", "0", ".", "="],
    ["1", "2", "3", "*"],
    ["4", "5", "6", "-"],
    ["7", "8", "9", "+"],
    ["C", "Bk", "%", "/"],
]


scientific_symbols1 = [
    ##
    "⇄",  # More keys IE Inverse options
    "Rad",
    "\u221a",  # Sq Root
    "\u007cx\u007c",  # Abs Val X
    ##
    "sin",
    "cos",
    "tan",
    "\u03c0",  # Pi
    ##
    "ln",
    "log",
    "1/x",
    "e",
    "e\u02e3",  # e to x
    "x\u00b2",  # x to 2
    "x\u02b8",  # x to y
    "+/-",
]

scientific_buttons1 = [
    ("⇄", "Rad", "\u221a", "\u007cx\u007c"),
    ("sin", "cos", "tan", "\u03c0"),
    ("ln", "log", "1/x", "e"),
    ("e\u02e3", "x\u00b2", "x\u02b8", "+/-"),
]

scientific_symbols2 = [
    ####### Alternate KeySet
    "⇄",  # Prev / Next Key Batch
    "Rad",
    "\u221b",  # sq Rt to 3
    "2\u02e3",  # 2 to x
    ##
    "sin\u207b\u00b9",
    "cos\u207b\u00b9",
    "tan\u207b\u00b9",
    "x\u00b3",  # X to 3
    ##
    "sinh",
    "cosh",
    "tanh",
    "x!",
    ##
    "sinh\u207b\u00b9",  # Sinh to -1
    "cosh\u207b\u00b9",  # cosh to -1
    "tanh\u207b\u00b9",  # Tanh to -1
    "+/-",
]

scientific_buttons2 = [
    ("⇄", "Rad", "\u221b", "2\u02e3"),  # 2 to x
    ("sin\u207b\u00b9", "cos\u207b\u00b9", "tan\u207b\u00b9", "x\u00b3"),  # X to 3
    ("sinh", "cosh", "tanh", "x!"),
    ("sinh\u207b\u00b9", "cosh\u207b\u00b9", "tanh\u207b\u00b9", "+/-"),
]


def main():
    sc1 = scientific_symbols1
    sc2 = scientific_symbols2

    # Copy and run this to see how they render
    print("Square root: \u221ax")  # Output: √x
    print("Absolute value: \u007cx\u007c")  # Output: |x|
    print("e to the x: e\u02e3")  # Output: eˣ
    print("x to the y: x\u02b8")  # Output: xʸ

    print("###########################################################################")
    for row in range(0, 16, 4):
        print(f"({sc1[row]}) ({sc1[row + 1]}) ({sc1[row + 2]}) ({sc1[row + 3]})")
    print("\n")

    for row in range(0, 16, 4):
        print(f"({sc2[row]}) ({sc2[row + 1]}) ({sc2[row + 2]}) ({sc2[row + 3]})")


if __name__ == "__main__":
    main()
