import sys
import argparse

std_input = ""
std_output = ""


# Parse stidin or passed file name
def parse_file(in_file, patt):
    text_file = []
    if in_file:  # if we were given a valid file name, use it
        with open(f"{in_file}", "r") as file:
            for line in file:
                if line == "":  # end of file and exit if found
                    break
                elif (
                    patt in line
                ):  # still here? Only store lines containing the search pattern
                    text_file.append(line)
    else:  # No file name was give, read stdin (Keyboard)
        for line in sys.stdin:
            if line == "":  # end of file and exit if found
                break
            elif (
                patt in line
            ):  # still here? Only store lines containing the search pattern
                text_file.append(line)
    return (
        text_file  # Send back the file parsed to only include lines containing pattern
    )


# write file contents to stdout (screen) or passed file name
def print_outfile(loc_file, std_outfile):
    if std_outfile:  # if we were given a valid file name, use it
        with open(f"{std_outfile}", "w") as file:
            for line in loc_file:
                if line == "":  # end of file and exit if found
                    break
                file.write(line)
    else:  # No file name was give, write to stdout (Screen)
        for line in loc_file:
            if line == "":  # end of file and exit if found
                break
            print(line, end="")
    print(f"Saved {len(loc_file)} lines to {std_outfile}")


# Parse command line for search pattern (mandatory) and optionally
# input file name and/or output file name
parser = argparse.ArgumentParser(description="Persistant Grep Filter")
parser.add_argument("pattern", help="<search pattern>")
parser.add_argument(
    "-i",
    "--infile",
    help="--infile <File Name>",
    default="",
)
parser.add_argument(
    "-o",
    "--outfile",
    help="--outfile <File Name>",
    default="",
)


args = parser.parse_args()
pattern = args.pattern  # Store the search pattern
if args.infile:
    std_input = args.infile  # Store the input file name if given
if args.outfile:
    std_output = args.outfile  # Store the output file name if given

# Grep style search of the file or stdinput based on search pattern
read_file = parse_file(std_input, pattern)

# print grepped file conents to an output file or stdout
print_outfile(read_file, std_output)
