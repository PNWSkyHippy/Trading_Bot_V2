import sys

if len(sys.argv) < 2:
    print("Error: Missing arguments!")
    print(f"Usage: python {sys.argv[0]} [pattern]")
    sys.exit(1)


std_input = sys.argv[1]


for line in sys.stdin:
    if line == "\n":
        break
    elif line == "":
        break
    if std_input in line:
        print(line, end="")
