import argparse
import os, sys
import fnmatch
from datetime import datetime
import yaml
from local_functions import colorize, Timed
from TkFileTool import MyFileUtilityTool

class Manipulate_files(MyFileUtilityTool):
    """_summary_ mainengine behind an all around file finding class
        methods:
            __init__(): initializes the class and sets up the necessary attributes.
            find_files(): searches for files in a given directory.
            list_dir(): lists the contents of a specified directory.
            write_out(): writes output to a file or stdout.
    """
    @Timed
    def __init__(self):
        """_summary_ parses comandline argumetnts and initiates esarch
        Raises:
            SystemExit: If no file name is specified or if the specified directory does not exist.            
        """
        self.format_list = [ # list of allowed output file formats
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
        self.gitignore_file = None
        self.gitignore_base = None
        self.gitignore_rules = []
        self.parse_arguments()
        if not self.dodir and not self.filename:
            sys.stderr.write("Error: Please specify a file name to search for using the -f option.")
            sys.stderr.flush()
            sys.exit(1)
        if self.dodir and not os.path.isdir(self.directory):
            sys.stderr.write(f"Error: The specified directory '{self.directory}' does not exist.")
            sys.stderr.flush()
            sys.exit(1)

        # Directory list asked for, list and exit
        elif self.dodir and os.path.isdir(self.directory):
            self.write_out(self.list_dir())
            sys.exit(0)
        # Proper arguments given , search for file
        else:
            found_files = self.find_files(self.directory, self.filename)
#            breakpoint()
            if found_files:
                if self.do_long:
                    self.write_out(f'{"Lines":<8}{"Words":<8}{"Chars":<8}{"File Path"}')

                if self.sorted == "forward":
                    found_files.sort(key=lambda x: (x[0][0].split("\\")[-1]).casefold())
                elif self.sorted == "reverse":
                    found_files.sort(key=lambda x: (x[0][0].split("\\")[-1]).casefold(), reverse=True)
                for found in found_files:
                    path, lines, words, chars = found
                    if self.verbose:
                        print(f"Found: {path} | Lines: {lines} | Words: {words} | Characters: {chars}")
                    if self.do_long:
                        self.write_out(f'{lines:<8}{words:<8}{chars:<8}{colorize(found[0], "blue")}')
                    else:
                        self.write_out(colorize(found[0], "blue"))

            else:
                sys.stderr.write(f"Error: No files named '{self.filename}' found in directory '{self.directory}'.")
                sys.stderr.flush()
        

    def wide_formatter(self,prog):
        return argparse.RawDescriptionHelpFormatter(
            prog,
            width=110,
            max_help_position=46,
        )

    def parse_arguments(self):
        """_summary_ parses command line arguments and sets the corresponding attributes."""
        parser = argparse.ArgumentParser(
            description="List PnL based on search criteria",
            epilog="""\
    Usage examples:
        mfind.py [opt. switches] <file name> [path] current directory used if not given
        mfind.py -f <file to search for>
        mfind.py "view*.py" (wildcards * ? [abc] for partial names - quote them on Mac/Linux)
        mfind.py -o <output file name> ((stdout default)
        mfind.py -c (cat file contents if found)
        mfind.py -f <input file format>  (txt, csv, jscon, jsonl, yaml, yml)
        mfind.py -d (return a dir of specified directory)
        mfind.py -v (verbose output <file name , size, date>)
        mfind.py -i (ignore case on matches)
        mfind.py -p (find partial matches (like *filename*))
        mfind.py -l (print file statistics <line count, word count, char count>)
        mfind.py -h Search hidden files and directories
        mfind.py -s <forward/reverse> List of files sorted forward or reverse
        mfind.py -m Set maximum search depth (default: none) -m 0 for no recursion pat starting location
        mfind.py -e Exclude entries that match the given glob pattern
        mfind.py -S Limit results based on the size of files
        mfind.py -x Execute a command for each search result
        mfind.py -X Execute a command with all search results at once
        mfind.py -t Filter by type: file (f), directory (d/dir), symlink (l),
                                   executable (x), empty (e), socket (s), pipe (p), char-device
                                   (c), block-device (b`
        mfind.py -h (display this help message)
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
            "-c",
            "--cat",
            action="store_true",
            help="Cat file contents if found",
        )

        parser.add_argument(
            "-o",
            "--outfile",
            metavar="",
            help="path and name of output file",
        )

        parser.add_argument(
            "-d",
            "--dir",
            action="store_true",
            help="\treturn a dir of specified directory",
        )

        parser.add_argument(
            "-f",
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

        parser.add_argument(
            "-p",
            "--partial",
            action="store_true",
            help="\tifind partial matches (like *filename*)",
        )

        parser.add_argument(
            "-g",
            "--gitignore",
            nargs="?",
            const=True,
            metavar="PATH",
            default=True,
            help="discover .gitignore automatically, or use PATH or its directory explicitly",
        )

        parser.add_argument(
            "-ig",
            "--ignoregit",
            action="store_true",
            help="ignore .gitignore rules and search the complete directory tree",
        )

        parser.add_argument(
            "-l",
            "--long",
            action="store_true",
            help="print file statistics <line count, word count, char count>",
        )

        parser.add_argument(
            "-H",
            "--hidden",
            action="store_true",
            help="search will include hidden files",
        )

        parser.add_argument(
            "-s",
            "--sorted",
            metavar="",
            help="\t <forward/reverse>    output list of files will be sorted given direction)",
        )


        parser.add_argument(
            "-m",
            "--maxdepth",
            metavar="",
            help="\t <depth>            Set maximum search depth (default: none)) 1 means only do current directory",
        )

        parser.add_argument(
            "-e",
            "--exclude",
            metavar="",
            help="\t <pattern>          Exclude entries that match the given glob pattern",
        )

        parser.add_argument(
            "-E",
            "--extension",
            metavar="",
            help="\t <ext>            Filter by file extension",
        )

        parser.add_argument(
            "-t",
            "--type",
            metavar="",
            help="\t<file type>       Filter by type: file (f), directory (d/dir), symlink (l)",
        )

        parser.add_argument(
            "-S",
            "--size",
            metavar="",
            help="\t<size>                Limit results based on the size of files",
        )

        parser.add_argument(
            "-x",
            "--execute",
            metavar="",
            help="\t<cmd>...              Execute a command for each search result",
        )

        parser.add_argument(
            "-X",
            "--exec-batch",
            metavar="",
            help="\t <cmd>...        Execute a command with all search results at once",
        )


        parser.add_argument("fname")                                   # 1st bare word
        parser.add_argument("path", nargs="?", default=".")          # 2nd bare word, optional

        args = parser.parse_args()
        if args.sorted:
            if args.sorted.strip().lower() in ("forward", "reverse"):
                self.sorted = args.sorted.strip().lower()
            else:
                self.sorted = False
        else:
            self.sorted = False        
        self.hidden = args.hidden if args.hidden else False
        self.maxdepth = int(args.maxdepth) if args.maxdepth else -1
        self.exclude = args.exclude if args.exclude else None
        self.extension = args.extension if args.extension else None
        self.type = args.type if args.type else None
        self.size = int(args.size) if args.size else -1
        self.execute = args.execute if args.execute else None
        self.exec_batch = args.exec_batch if args.exec_batch else None
        self.do_long = args.long if args.long else False
        self.partial = args.partial if args.partial else False
        self.ignorecase = args.ignore if args.ignore else False
        self.filename = args.name if args.name else None
        self.filename = args.fname if args.fname else self.filename
        self.output_file = args.outfile if args.outfile else "stdout"
        self.directory = args.path if args.path else "."
        self.docat = args.cat if args.cat else False
        self.dodir = args.dir if args.dir else False
        self.verbose = args.verbose if args.verbose else False
        self.format = args.format if args.format else None
        self.gitignore_file = args.gitignore
        self.ignoregit = args.ignoregit
        if self.format and self.format not in self.format_list:
            sys.stderr.write(f"Error: Invalid format '{self.format}'. Supported formats are: {', '.join(self.format_list)}.")
            sys.stderr.flush()
            sys.exit(1)

    def _load_gitignore(self, directory):
        """Load the first .gitignore found, or the explicitly supplied one."""
        ignore_file = self.gitignore_file
        if isinstance(ignore_file, str):
            ignore_file = os.path.abspath(ignore_file)
            if os.path.isdir(ignore_file):
                ignore_file = os.path.join(ignore_file, ".gitignore")
            if not os.path.isfile(ignore_file):
                sys.stderr.write(f"Warning: gitignore file '{ignore_file}' was not found.\n")
                return
        elif ignore_file is True:
            search_directory = os.path.abspath(directory)
            candidates = []

            # Check the script and working-directory ancestry. This handles
            # invoking the script from above the repository, such as
            # `python Ron\Code\mfind.py ...` from the user's home directory.
            discovery_starts = [
                os.path.abspath(os.path.dirname(__file__)),
                os.path.abspath(os.getcwd()),
            ]
            for discovery_start in discovery_starts:
                try:
                    starts_inside_search = (
                        os.path.normcase(os.path.commonpath([discovery_start, search_directory]))
                        == os.path.normcase(search_directory)
                    )
                except ValueError:
                    starts_inside_search = False
                if not starts_inside_search:
                    continue
                current = discovery_start
                while True:
                    candidates.append(os.path.join(current, ".gitignore"))
                    if current == search_directory:
                        break
                    parent = os.path.dirname(current)
                    if parent == current:
                        break
                    current = parent

            # If no repository rule was found, check the search root and its
            # parents without walking the tree first.
            current = search_directory
            while True:
                candidates.append(os.path.join(current, ".gitignore"))
                parent = os.path.dirname(current)
                if parent == current:
                    break
                current = parent

            ignore_file = next((candidate for candidate in candidates
                                if os.path.isfile(candidate)), None)
            if self.verbose and not ignore_file:
                sys.stderr.write(
                    "\nGitignore: checked these paths:\n  " +
                    "\n  ".join(candidates) + "\n"
                )
                sys.stderr.flush()
        else:
            return

        if not ignore_file:
            if self.verbose:
                sys.stderr.write("\nGitignore: no .gitignore found; searching without ignore rules\n")
                sys.stderr.flush()
            return

        self.gitignore_file = os.path.abspath(ignore_file)
        self.gitignore_base = os.path.dirname(self.gitignore_file)
        try:
            with open(self.gitignore_file, "r", encoding="utf-8") as ignore:
                for line in ignore:
                    line = line.rstrip("\r\n")
                    if not line or line.lstrip().startswith("#"):
                        continue
                    if line.startswith("\\#"):
                        line = line[1:]
                    negated = line.startswith("!")
                    if negated:
                        line = line[1:]
                    if line:
                        self.gitignore_rules.append((line, negated))
            if self.verbose:
                sys.stderr.write(
                    f"\nGitignore: loaded {len(self.gitignore_rules)} rules from {self.gitignore_file}\n"
                )
                sys.stderr.flush()
        except OSError as exc:
            sys.stderr.write(f"Warning: unable to read gitignore file '{self.gitignore_file}': {exc}\n")

    def _gitignored(self, path, is_dir=False):
        """Return whether path is excluded by the loaded gitignore rules."""
        if not self.gitignore_rules:
            return False
        relative = os.path.relpath(path, self.gitignore_base).replace(os.sep, "/")
        ignored = False
        for pattern, negated in self.gitignore_rules:
            pattern = pattern.replace("\\", "/")
            directory_pattern = pattern.endswith("/")
            pattern = pattern.rstrip("/")
            anchored = pattern.startswith("/")
            pattern = pattern.lstrip("/")
            if directory_pattern:
                # An unanchored directory rule applies to matching directory
                # names anywhere in the search tree, including above the repo.
                if "/" in pattern or anchored:
                    matches = (relative == pattern or
                               relative.startswith(pattern + "/"))
                else:
                    parts = relative.split("/")
                    basename = os.path.basename(os.path.normpath(path))
                    matches = (fnmatch.fnmatchcase(basename, pattern) or
                               any(fnmatch.fnmatchcase(part, pattern)
                                   for part in parts if part not in ("", "..")))
            elif "/" in pattern or anchored:
                matches = fnmatch.fnmatchcase(relative, pattern)
            else:
                matches = any(fnmatch.fnmatchcase(part, pattern)
                              for part in relative.split("/"))
            if matches:
                ignored = not negated
        return ignored

    def count_file_contents(self, path):
        """
        Count the number of lines, words, and characters in a file.

        Args:
            path (str): The path to the file.

        Returns:
            tuple: A tuple containing the number of lines, words, and characters.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                contents = f.read()
                lines = contents.count("\n") + 1 if contents else 0
                words = len(contents.split())
                chars = len(contents)
                return lines, words, chars
        except Exception as e:
            if self.verbose:
                sys.stderr.write(f"Error reading {path}: {e}\n")
                sys.stderr.flush()
            return 0, 0, 0


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
        if self.ignoregit:
            if self.verbose:
                sys.stderr.write("\nGitignore: bypassed; searching the complete directory tree\n")
                sys.stderr.flush()
        else:
            self._load_gitignore(directory)
        if self.partial:
            filename = f"*{filename}*"
        want = filename.lower() if self.ignorecase else filename
        wild = any(c in filename for c in "*?[")         # glob pattern like *.py or view*
        for root, dirs, files in os.walk(directory):      # os.walk already goes into every subfolder
 
            if len(root.split("\\")) >= int(self.maxdepth):
                    dirs.clear()
            if not self.ignoregit:
                ignored_dirs = [d for d in dirs
                                if self._gitignored(os.path.join(root, d), is_dir=True)]
                if self.verbose and ignored_dirs:
                    sys.stderr.write(
                        f"\nGitignore: pruning from {root}: {', '.join(ignored_dirs)}\n"
                    )
                    sys.stderr.flush()
                dirs[:] = [d for d in dirs
                           if not self._gitignored(os.path.join(root, d), is_dir=True)]
            for f in files:
                path = os.path.join(root, f)
                if not self.ignoregit and self._gitignored(path):
                    continue
                have = f.lower() if self.ignorecase else f
                if fnmatch.fnmatchcase(have, want) if wild else have == want:
                        lines, words, chars = self.count_file_contents(path)
                        found_files.append((path, lines, words, chars))    # f = name as it is on disk
            if self.verbose:
                sys.stderr.write(f"\rSearching in: {root} ...")
                sys.stderr.flush()
        return found_files 

    def list_dir(self):
        """
        List the contents of the specified directory.
        Args:
            directory (str): The directory to list.

        Returns:
            list: a list of the contents of the directory.
        """
       
        ret_str = ""
        for f in os.listdir(self.directory):
            if not f.startswith('.'):
                modified = datetime.fromtimestamp(os.path.getmtime(os.path.join(self.directory, f))).strftime("%m/%d/%Y %I:%M %p")
                ret_str += f"{modified}\t{os.path.getsize(os.path.join(self.directory, f)):>15}\t {f}\n"

        return ret_str
      
    def write_out(self, inp_str):
        """
        Write the output to the specified file or stdout.

        Args:
            inp_str (str): The string to write out.
        """
        if self.docat:
            file_list = [f for f in inp_str.splitlines() if os.path.isfile(f)]
            out_buff = ""
            for file in file_list:
                try:
                   with open(file, "r") as f:
                        temp_buff = f.read()
                except Exception as e:
                    sys.stderr.write(f"Error reading {file}: {e}")
                    sys.stderr.flush()
                else:
                    with open(file, "r") as f:
                        out_buff += f'\n\n#--- Contents of {file} ---\n'
                        out_buff += f.read()
                        exc_flag = False
        if self.format is not None:
            try:
                outfile, _ = self.output_file.split(".")
            except ValueError:
                outfile = self.output_file 
            outfile = outfile + "." + self.format
            if self.format == "txt":
                if self.docat:
                    with open(outfile, "w") as f:
                        f.write(out_buff)
                else:
                    with open(outfile, "w") as f:
                        f.write(str(inp_str))
            elif self.format == "csv":
                import csv
                if self.docat:
                    with open(outfile, "w", newline="") as f:
                        writer = csv.writer(f)
                        for line in out_buff.splitlines():
                            writer.writerow([line])
                else:
                    with open(outfile, "w", newline="") as f:
                        writer = csv.writer(f)
                        for line in inp_str.splitlines():
                            writer.writerow([line])
            elif self.format in ["json", "jsonl"]:
                import json
                if self.docat:
                    with open(outfile, "w") as f:
                        if self.format == "json":
                            json.dump(out_buff.splitlines(), f)
                        else:  # jsonl
                            for line in out_buff.splitlines():
                                f.write(json.dumps(line) + "\n")
                else:
                    with open(outfile, "w") as f:
                        if self.format == "json":
                            json.dump(inp_str.splitlines(), f)
                        else:  # jsonl
                            for line in inp_str.splitlines():
                                f.write(json.dumps(line) + "\n")
            elif self.format in ["yaml", "yml"]:
                if self.docat:
                    with open(outfile, "w") as f:
                        yaml.dump(out_buff.splitlines(), f)
                else:
                    with open(outfile, "w") as f:
                        yaml.dump(inp_str.splitlines(), f)

        if self.output_file == "stdout":
            if self.docat:
                print(out_buff)
            else:
                print(inp_str)
        else:
            if self.docat:
                with open(self.output_file, "w") as f:
                    f.write(out_buff)
            else:
                with open(self.output_file, "w") as f:
                    f.write(str(inp_str))

def main():
    timer = Manipulate_files()
    print(f'Time Elapsed: {timer.__init__.elapsed}')
if __name__ == "__main__":
    main()
