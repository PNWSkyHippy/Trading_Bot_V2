import argparse
import importlib
import pydoc
import sys

parser = argparse.ArgumentParser(description="Search names inside a Python module")
parser.add_argument("-l", "--list", action="store_true", help="list all standard library modules")
parser.add_argument("module_name", nargs= "?",  help="module to inspect, like sys, pathlib, argparse")
parser.add_argument("search", nargs="?", default="", help="optional search word")

    
args = parser.parse_args()

def list_modules():
    for name in sorted(sys.stdlib_module_names):
        print(name)
    return


def resolve_dotted_name(dotted_name):
    """Import the longest valid module prefix, then walk remaining attributes."""
    parts = dotted_name.split(".")
    last_error = None

    for split_at in range(len(parts), 0, -1):
        module_name = ".".join(parts[:split_at])
        attr_parts = parts[split_at:]
        try:
            obj = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            last_error = exc
            continue

        for attr in attr_parts:
            try:
                obj = getattr(obj, attr)
            except AttributeError:
                print(f"Object found through {module_name}, but missing attribute: {attr}")
                raise SystemExit(1)
        return obj

    print(f"Module or object not found: {dotted_name}")
    if last_error:
        print(last_error)
    raise SystemExit(1)


def inspect_module(module_name):
    module = resolve_dotted_name(module_name)

    if "." in module_name and not args.search:
        print(pydoc.plain(pydoc.render_doc(module, title="Help on %s")))
        return

    matches = [name for name in dir(module) if args.search.lower() in name.lower()]

    if not matches:
        print("No matches found.")
    else:
        for name in matches:
            obj = getattr(module, name)
            print(f"{name:30} {type(obj).__name__}")

if args.list :
  list_modules()
elif args.module_name:
  inspect_module(args.module_name)
else:
    parser.error("give a module_name or use -l/--list")
      
