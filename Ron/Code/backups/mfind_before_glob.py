import argparse
import os, sys
from datetime import datetime
import yaml
from local_functions import colorize

class Manipulate_files:

    def __init__(self):
        self.format_list = [
            "txt", "csv", "json", "jsonl", "yaml", "yml"
        ]
        cur_dir = os.path.dirname(__file__)
        self.output_file = None
        self.docat = None
        self.dodir = None
        self.verbose = None
        self.format = None
        self.directory = None
        self.filename = None
        self.parse_arguments()
        if not self.dodir and not self.filename:
            sys.stderr.write("Error: Please specify a file name to search for using the -f option.")
            sys.stderr.flush()
            sys.exit(1)
        if self.dodir and not os.path.isdir(self.directory):
            sys.stderr.write(f"Error: The specified directory '{self.directory}' does not exist.")
            sys.stderr.flush()
            sys.exit(1)
        elif self.dodir and os.path.isdir(self.directory):
            self.write_out(self.list_dir())
        else:
            found_files = self.find_files(self.directory, self.filename)
            if found_files:
                self.write_out("\n".join(found_files))
            else:
                sys.stderr.write(f"Error: No files named '{self.filename}' found in directory '{self.directory}'.")
                sys.stderr.flush()
                sys.exit(1)

    def wide_formatter(self,prog):
        return argparse.RawDescriptionHelpFormatter(
            prog,
            width=110,
            max_help_position=46,
        )

    def parse_arguments(self):
        parser = argparse.ArgumentParser(
            description="List PnL based on search criteria",
            epilog="""\
    Usage examples:
        mfind.py [opt. switches] <file name> [path] current directory used if not given
        mfind.py -f <file to search for>
        mfind.py -o <output file name> ((stdout default)
        mfind.py -c (cat file contents if found)
        mfind.py -m <input file format>  (txt, csv, jscon, jsonl, yaml, yml)
        mfind.py -d (return a dir of specified directory)
        mfind.py -v (verbose output <file name , size, date>)
        mfind.py -i (ignore case on matches)
        mfind,py -h (display this help message)
    """,
           formatter_class=self.wide_formatter,
        )

        parser.add_argument(
                "-n",
              "--name",
              metavar="",
              help="\tname of file to search for",
       )

        parser.add_argument(
            "-o",
            "--outfile",
            metavar="",
            help="\tpath and name of output file",
        )

        parser.add_argument(
            "-c",
            "--cat",
            action="store_true",
            help="Cat file contents if found",
        )

        parser.add_argument(
            "-d",
            "--dir",
            action="store_true",
            help="\treturn a dir of specified directory",
        )
        parser.add_argument(
            "-m",
            "--format",
            metavar="",
            help="\tinput file format (txt, csv, json, jsonl, yaml, yml)",
        )

        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="\tverbose output <file name , size, date>",
        )

        parser.add_argument(
            "-i",
            "--ignore",
            action="store_true",
            help="\tignore case on matches",
        )

        parser.add_argument("fname")                                   # 1st bare word
        parser.add_argument("path", nargs="?", default=".")          # 2nd bare word, optional

        args = parser.parse_args()

        self.ignorecase = args.ignore if args.ignore else False
        self.filename = args.name if args.name else None
        self.filename = args.fname if args.fname else self.filename
        self.output_file = args.outfile if args.outfile else "stdout"
        self.directory = args.path if args.path else "."
        self.docat = args.cat if args.cat else False
        self.dodir = args.dir if args.dir else False
        self.verbose = args.verbose if args.verbose else False
        self.format = args.format if args.format else None
        if self.format and self.format not in self.format_list:
            sys.stderr.write(f"Error: Invalid format '{self.format}'. Supported formats are: {', '.join(self.format_list)}.")
            sys.stderr.flush()
            sys.exit(1)

    def find_files(self, directory, filename):
        """
        Recursively search for files with the specified filename in the given directory.

        Args:
            directory (str): The directory to search in.
            filename (str): The name of the file to search for.

        Returns:
            list: A list of paths to the found files.
        """
        found_files = []
        for root, dirs, files in os.walk(directory):
            if self.ignorecase:
                if filename.lower() in [f.lower() for f in files]:    
                    found_files.append(os.path.join(root, filename))
            else:
                if filename in files:    
                    found_files.append(os.path.join(root, filename))
            for name in dirs:
                self.find_files(os.path.join(root, name), filename)
        return found_files

    def list_dir(self):
        """
        List the contents of the specified directory.

        Returns:
            list: A list of the contents of the directory.
        """
        if self.verbose:
            ret_str = ""
            for f in os.listdir(self.directory):
                if not f.startswith('.'):
                    modified = datetime.fromtimestamp(os.path.getmtime(os.path.join(self.directory, f))).strftime("%m/%d/%Y %I:%M %p")
                    ret_str += f"{modified}\t{os.path.getsize(os.path.join(self.directory, f)):>15}\t {f}\n"

            return ret_str
        else:
            ret_str= ""
            path = self.directory if self.directory else os.getcwd()
            with os.scandir(path) as it:
                for entry in it:
                    if not entry.name.startswith('.') and entry.is_file():
                        ret_str += entry.name + "\n"

            return ret_str

    def write_out(self, inp_str):
        """
        Write the output to the specified file or stdout.

        Args:
            inp_str (str): The string to write out.
        """
        if self.format is not None:
            outfile, _ = self.output_file.split(".")
            outfile = outfile + "." + self.format
            if self.format == "txt":
                with open(outfile, "w") as f:
                    f.write(str(inp_str))
            elif self.format == "csv":
                import csv
                with open(outfile, "w", newline="") as f:
                    writer = csv.writer(f)
                    for line in inp_str.splitlines():
                        writer.writerow([line])
            elif self.format in ["json", "jsonl"]:
                import json
                with open(outfile, "w") as f:
                    if self.format == "json":
                        json.dump(inp_str.splitlines(), f)
                    else:  # jsonl
                        for line in inp_str.splitlines():
                            f.write(json.dumps(line) + "\n")
            elif self.format in ["yaml", "yml"]:
                with open(outfile, "w") as f:
                    yaml.dump(inp_str.splitlines(), f)

        if self.output_file == "stdout":
            if self.docat:
                with open(inp_str, "r") as f:
                    print(f.read())
            else:
                print(f'{colorize(inp_str, "red")}')
        else:
            if self.docat:
                with open(self.filename, "r") as f:
                    content = f.read()
                with open(self.output_file, "w") as f:
                    f.write(content)
            else:
                with open(self.output_file, "w") as f:
                    f.write(str(inp_str))

def main():
    Manipulate_files()

if __name__ == "__main__":
    main()
