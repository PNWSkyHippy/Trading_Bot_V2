import sys

empty_line = False
while not empty_line:
    for line in sys.stdin:
        if line == "\n":
            empty_line = True
            break
        print(line.upper(), end="")
