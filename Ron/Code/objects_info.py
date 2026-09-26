import sys

from local_functions import describe
from tktrades_list import TradeAnalyzerTool

# Print Python's generated documentation for the module
# help(requests)
#
# List names available from the module
# print(dir(requests))

# Show public functions and classes
# for name, thing in inspect.getmembers(requests):
#    if not name.startswith("_"):
#        if inspect.isfunction(thing) or inspect.isclass(thing):
#            print(name, "->", thing)

# print(inspect.signature(Path.read_text))
# print(inspect.getdoc(Path.read_text))


# Constructor / class-call signature
# print("Constructor:", inspect.signature(Path))

# Class docstring
# print("Docs:", inspect.getdoc(Path))

# Methods defined or inherited by the class
# for method_name, method in inspect.getmembers(Path, predicate=inspect.isroutine):
#    if not method_name.startswith("_"):
#        try:
#            signature = inspect.signature(method)
#        except (TypeError, ValueError):
#            signature = "(signature unavailable)"

#        doc = inspect.getdoc(method) or "No docstring"
#       first_line = doc.splitlines()[0]

#        print(f"{method_name}{signature}")
#        print(f"  {first_line}")

describe(TradeAnalyzerTool)
# print(inspect.getdoc(lf.Timed) or "No docstring available.")
if sys.argv[1]:
    print(f"Printing {sys.argv[1]}")
    describe(sys.argv[1])
# print(describe.__docstring__)
