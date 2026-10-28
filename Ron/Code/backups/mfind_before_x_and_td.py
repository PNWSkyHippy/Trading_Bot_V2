"""Search for files by name, size, date, and extension from the command line.

Provides the ``Manipulate_files`` class, which parses command-line options,
walks a directory tree (honoring ``.gitignore`` rules), and writes the sorted
results to stdout or to a file in several formats.
"""
from asyncio import subprocess
import stat
from stat import FILE_ATTRIBUTE_HIDDEN
import argparse
import os, sys
import fnmatch
from datetime import datetime
import yaml
from local_functions import colorize, Timed, bytes_to_str, str_to_bytes
from TkFileTool import MyFileUtilityTool

"""
To Code Yet
**    filter by type of file ** Done
**    filter by extension of file ** Done
**    sort by bytesize ** Done
**    forward or reverse the sort method chosen ** Done
**    show and sort by timestamp on file (Lst modification) (recent command) ** Done
**    exlude pattern -more of whats already skipped via .gitignore ** Done
    xecute command on each file found
    Xecute a command on entire list of files found IE program | wc -l that takes a list of files on stdin 
"""

import subprocess
from concurrent.futures import ThreadPoolExecutor

def run_for_file(args):
    template, name = args
    cmd = template.replace("{}", f'"{name}"')
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return name, p.returncode, p.stdout, p.stderr
    except Exception as e:
        return name, -1, "", str(e)

def exec_on_files(template, files, workers=8):
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(run_for_file, [(template, f) for f in files]))
    for name, rc, out, err in results:      # printed in original file order
        print(f"== {name} (rc={rc})")
        if out: print(out, end="")
        if err: print(err, end="")

class Manipulate_files(MyFileUtilityTool):
    """Provide the main engine behind an all-around file finding tool.

    Attributes:
        format_list (list[str]): Allowed output file formats.
        output_file (str | None): Output path, or "stdout" for the console.
        directory (str | None): Root directory of the search.
        filename (str | None): Name or glob pattern to search for.
        gitignore_rules (list[tuple[str, bool]]): Loaded ``.gitignore``
            rules as (pattern, negated) pairs.
    """
    # maps every accepted -t spelling to its canonical type name
    TYPE_ALIASES = {
        "f": "file", "file": "file",
        "d": "dir", "dir": "dir", "directory": "dir",
        "l": "symlink", "link": "symlink", "symlink": "symlink",
        "x": "executable", "exec": "executable", "executable": "executable",
        "e": "empty", "empty": "empty",
        "s": "socket", "socket": "socket",
        "p": "pipe", "pipe": "pipe", "fifo": "pipe",
        "c": "char", "char": "char", "char-device": "char",
        "b": "block", "block": "block", "block-device": "block",
    }

    @Timed
    def __init__(self):
        """Parse command-line arguments, run the search, and print results.

        Raises:
            SystemExit: If no file name is specified or the specified
                directory does not exist.
        """
        self.format_list = [ # list of allowed output file formats
            "txt", "csv", "json", "jsonl", "yaml", "yml"
        ]
        os.path.dirname(__file__)
        self.output_file = None
        self.docat = None
        self.dodir = None
        self.verbose = None
        self.format = None
        self.directory = None
        self.filename = None
        self.gitignore_file = None
        self.gitignore_base = None
        self.file_sz = 0
        self.file_sz_str = ""
        self.file_hid = 0
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
            import subprocess
            cmd_ret = subprocess.run(['powershell', '-Command', 'dir', os.path.abspath(self.directory)], capture_output= True, text=True)
            sys.stdout.write(f'{cmd_ret.stdout}')

        # Proper arguments given , search for file
        else:
            found_files = self.find_files(self.directory, self.filename)
            if found_files:
                if self.verbose or self.do_long:
                    self.write_out(f'{"Size":<12}{"Lines":<8}{"Words":<8}{"Chars":<8}{"File Path"}')
                elif self.size:
                    self.write_out(f'{"Size":<12}{"File Path"}')
                if self.sortmod and (self.sorted == "reverse"):
                    found_files.sort(key=lambda x: (x[3]))
                elif self.sortmod:
                    found_files.sort(key=lambda x: (x[3] ), reverse = True)
                elif self.sortsize and (self.sorted == "reverse"):
                    found_files.sort(key=lambda x: (x[1]), reverse=True)
                elif self.sortsize:
                    found_files.sort(key=lambda x: (x[1] ))
                elif self.sorted == "forward":
                    found_files.sort(key=lambda x: (x[0].split("\\")[-1]).casefold())
                elif self.sorted == "reverse":
                    found_files.sort(key=lambda x: (x[0].split("\\")[-1]).casefold(), reverse=True)

                for found in found_files:
                    path, bsize, size, mod_time, lines, words, chars = found
                    if self.verbose or self.do_long:
                        self.write_out(f'{size:<12}{lines:<8}{words:<8}{chars:<8}{colorize(found[0], "blue")}')
                    elif self.size:
                        self.write_out(f'{size:<12}{colorize(found[0], "blue")}')
                    else:
                        self.write_out(colorize(found[0], "blue"))
#                if self.doexec:
#                    exec_on_files(self.exec_list, found_files)

            else:
                sys.stderr.write(f"Error: No files named '{self.filename}' found in directory '{self.directory}'.")
                sys.stderr.flush()

    def wide_formatter(self,prog):
        """Build a wide argparse help formatter.

        Args:
            prog (str): The program name shown in the help output.

        Returns:
            argparse.RawDescriptionHelpFormatter: A formatter that keeps the
                epilog layout and uses a 110-column width.
        """
        return argparse.RawDescriptionHelpFormatter(
            prog,
            width=110,
            max_help_position=46,
        )

    def parse_arguments(self):
        """Parse command-line arguments and set the matching attributes.

        Raises:
            SystemExit: If an argument is invalid, such as a value for ``-s``
                other than forward/reverse, a malformed or conflicting ``-S``
                size filter, or an unsupported output format.
        """
        parser = argparse.ArgumentParser(
            description="Search for files on various criteria",
            epilog="""\
    Usage: mfind.py [OPTIONS] [pattern] [path]

    Arguments:
        [pattern]  the search pattern (a regular expression, unless '--glob' is used; optional)
        [path]...  the root directories for the filesystem search (optional)

    Options:
        mfind.py [opt. switches] <file name> [path] current directory used if not given
        mfind.py -n <file to search for>
        mfind.py "view*.py" (wildcards * ? [abc] for partial names - quote them on Mac/Linux)
        mfind.py -o <output file name> ((stdout default)
        mfind.py -c (cat file contents if found)
        mfind.py -E <extension> (filter results by file extension)
        mfind.py -f <input file format>  (txt, csv, jscon, jsonl, yaml, yml)
        mfind.py -d (return a dir of specified directory)
        mfind.py -v (verbose output <file name , size, date>)
        mfind.py -i (ignore case on matches)
        mfind.py -sm (sort results by fle modification time) **use -s forward/reverse for direction**
        mfind.py -sz (sort results by fle size) **use -s forward/reverse for direction**
        mfind.py -p (find partial matches (like *filename*))
        mfind.py -l (print file statistics <line count, word count, char count>)
        mfind.py -H Search hidden files and directories
        mfind.py -s <forward/reverse> List of files sorted forward or reverse
        mfind.py -m Set maximum search depth (default: none) -m 0 for no recursion pat starting location
        mfind.py -e Exclude entries that match the given glob pattern
        mfind.py -S Limit results based on the size of files using the format <+-><NUM><UNIT>. 
                  '+': file size must be greater than or equal to this
                  '-': file size must be less than or equal to this

                  If neither '+' nor '-' is specified, file size must be exactly equal to this.
                  Use one + and one - together for a range: -S +10KB -S -20KB
                     'NUM':  The numeric size (e.g. 500)
                     'UNIT': The units for NUM. They are not case-sensitive.
                  Allowed unit values:
                      'Bs':   bytes
                      'KB':   kilobytes (base ten, 10^3 = 1000 bytes)
                      'MB':   megabytes
                      'GB':   gigabytes
                      'TB':   terabytes
                      'PB':   petabytes   
                      'KiB':  kilobytes (1024 bytes)
                      'MiB':  megabytes
                      'GiB':  gigabytes
                      'TiB':  terabytes
                      'PiB':  petabytes    
                  ** 2 -S arguments, one specifying a +<val> and the other a -<val> are allowed
                  ** However specifying 2, -S + or 2 -S - raise an ambiguous error  
                  ** specifying both is saying - if size > this AND < that, show it
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
            "-sz",
            "--sortsize",
            action="store_true",
            help="sort results by file size",
        )

        parser.add_argument(
            "-sm",
            "--sortmod",
            action="store_true",
            help="sort results by file modification time",
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
            action="append",
            help="\t <pattern>          Exclude entries that match the given glob pattern (repeatable)",
        )

        parser.add_argument(
            "-E",
            "--extension",
            metavar="",
            action="append",
            help="\t <ext>            Filter by extension: comma list and/or repeatable (-E txt,json -E .jpg)",
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
            action="append",
            help="-S [+/-]bytes[PB|TB|GB|MB|KB|BS|PiB|TiB|MiB|KiB|BiS]"
            ,
        )
        parser.add_argument(
            "-x", "--execute",
            nargs=argparse.REMAINDER
        )


        parser.add_argument(
            "-X",
            "--exec-batch",
            metavar="",
            help="\t <cmd>...        Execute a command with all search results at once",
        )


        parser.add_argument("fname", nargs="?")                        # 1st bare word, optional with -E
        parser.add_argument("path", nargs="?", default=None)         # 2nd bare word, optional

        # Glue the -S value onto the switch so argparse doesn't treat "-600MB" as a new option
        argv = sys.argv[1:]
        i = 0
        while i < len(argv) - 1:
            if argv[i] == "--":
                break
            if argv[i] in ("-S", "--size"):
                argv[i:i + 2] = [f"--size={argv[i + 1]}"]
            i += 1
        args = parser.parse_args(argv)
        # With -E the name pattern is optional: "mfind.py -E txt,json [folder]" lists every match
        if args.extension and not args.name:
            if args.fname is not None and args.path is None and os.path.isdir(args.fname):
                args.path, args.fname = args.fname, None    # lone bare word is the folder
            if args.fname is None:
                args.fname = "*"
        elif args.fname is None and not args.name:
            parser.error("the following arguments are required: fname (or use -E)")
        self.sortmod = args.sortmod if args.sortmod else False
        if args.sortsize:
            self.sorted = "mod"
        self.sortsize = args.sortsize if args.sortsize else False
        if args.sortsize:
            self.sorted = "size"
        if args.sorted:
            direction = args.sorted.strip().lower()[:1]
            if direction == "f":
                self.sorted = "forward"
            elif direction == "r":
                self.sorted = "reverse"
            else:
                parser.error(f"invalid value '{args.sorted}' for -s (use forward or reverse)")
        elif not self.sortsize:
            self.sorted = False        
        self.hidden = args.hidden if args.hidden else False
        self.maxdepth = int(args.maxdepth) if args.maxdepth else -1
        self.exclude = args.exclude if args.exclude else None
        # -e patterns reuse the .gitignore matcher, so "build/", "*.log" and "docs/*.md" all work
        self.exclude_rules = [(pat.strip(), False) for pat in (args.exclude or []) if pat.strip()]
        self.extension_rules = [e.strip().lstrip(".").lower()
                                for arg in (args.extension or []) for e in arg.split(",")
                                if e.strip().lstrip(".")]
        if self.extension_rules != []:
            self.filterby_ext = True
        else:
            self.filterby_ext = False
        self.type = None
        if args.type:
            self.type = self.TYPE_ALIASES.get(args.type.strip().lower())
            if self.type is None:
                parser.error(f"invalid type '{args.type}' for -t (use f, d, l, x, e, s, p, c, or b)")
        # directories only show up in os.walk's dirs list, so -t needs to look there too
        self.type_wants_dirs = self.type in ("dir", "symlink", "empty")
        # -S can be given twice: one +<size> (lower limit) and one -<size> (upper limit)
        self.size_lower = None      # file must be >= this
        self.size_upper = None      # file must be <= this
        self.size_exact = None      # file must be == this
        for siz in (args.size or []):
            sign = siz[0] if siz[0] in ("+", "-") else ""
            nbytes = str_to_bytes(siz[1:] if sign else siz)
            if nbytes is None:
                parser.error(f"invalid size '{siz}' for -S (e.g. +15KB, -600MB, 2MiB, 100BS)")
            if self.size_exact is not None or (not sign and (self.size_lower is not None or self.size_upper is not None)):
                parser.error(f"-S {siz}: an exact size can't be combined with another -S")
            if sign == "+":
                if self.size_lower is not None:
                    parser.error(f"-S {siz}: -S +<size> already used. Duplicates are ambiguous.")
                self.size_lower = nbytes
            elif sign == "-":
                if self.size_upper is not None:
                    parser.error(f"-S {siz}: -S -<size> already used. Duplicates are ambiguous.")
                self.size_upper = nbytes
            else:
                self.size_exact = nbytes
        if self.size_lower is not None and self.size_upper is not None and self.size_lower > self.size_upper:
            parser.error("-S lower limit (+) is bigger than upper limit (-), nothing can match")
        self.size = bool(args.size)  # True when any size filter is active (shows the Size column)
    
#        self.execute = args.execute if args.execute else None
#        self.exec_batch = args.exec_batch if args.exec_batch else None
        self.do_long = args.long if args.long else False
        self.partial = args.partial if args.partial else False
        self.ignorecase = args.ignore if args.ignore else False
        self.filename = args.name if args.name else None
        self.filename = args.fname if args.fname else self.filename
        self.output_file = args.outfile if args.outfile else "stdout"
#        self.exec_list = args.execcute if args.excecute else []
#        self.doexec = True if self.exec_list != [] else False 
        self.docat = args.cat if args.cat else False
        self.dodir = args.dir if args.dir else False
        if self.dodir:
            self.directory = self.filename
        else:
              self.directory = args.path if args.path else "."  
        self.verbose = args.verbose if args.verbose else False
        self.format = args.format if args.format else None
        self.gitignore_file = args.gitignore
        self.ignoregit = args.ignoregit
        if self.format and self.format not in self.format_list:
            sys.stderr.write(f"Error: Invalid format '{self.format}'. Supported formats are: {', '.join(self.format_list)}.")
            sys.stderr.flush()
            sys.exit(1)

    def _load_gitignore(self, directory):
        """Load the first .gitignore found, or the explicitly supplied one.

        Populates ``gitignore_rules``, ``gitignore_file``, and
        ``gitignore_base``. Prints a warning to stderr and returns without
        loading rules if the file is missing or unreadable.

        Args:
            directory (str): The search root, used to discover a .gitignore
                when none was given explicitly.
        """
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
        """Return whether a path is excluded by the loaded gitignore rules.

        Args:
            path (str): The file or directory path to test.
            is_dir (bool): Whether ``path`` is a directory. Defaults to False.

        Returns:
            bool: True if the last matching rule ignores the path, False if
                no rules are loaded or the path is not ignored.
        """
        if not self.gitignore_rules:
            return False
        return self._match_rules(path, self.gitignore_rules, self.gitignore_base)

    def _excluded(self, path):
        """Return whether a path matches a pattern given with -e.

        Uses the same glob rules as .gitignore, relative to the search root.

        Args:
            path (str): The file or directory path to test.

        Returns:
            bool: True if any -e pattern matches the path.
        """
        if not self.exclude_rules:
            return False
        return self._match_rules(path, self.exclude_rules, self.directory)

    def _match_rules(self, path, rules, base):
        """Apply gitignore-style rules to a path; the last matching rule wins.

        Args:
            path (str): The file or directory path to test.
            rules (list[tuple[str, bool]]): (pattern, negated) pairs.
            base (str): The directory the patterns are relative to.

        Returns:
            bool: True if the path ends up ignored by the rules.
        """
        relative = os.path.relpath(path, base).replace(os.sep, "/")
        ignored = False
        for pattern, negated in rules:
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
        """Count the lines, words, and characters in a file.

        Args:
            path (str): The path to the file.

        Returns:
            tuple[int, int, int]: The line, word, and character counts, or
                (0, 0, 0) if the file cannot be read.
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

    def get_extension(self, filename):
        """Return the extension of a file name.

        Args:
            filename (str): The file name to inspect.

        Returns:
            str | "None": The text after the last dot, or empty string if the name
                contains no dot.
        """
        tmp_str = filename.split(".")
        if len(tmp_str) > 1:
            return tmp_str[len(tmp_str)-1]
        else:
            return "None"

    def matches_type(self, path, mode):
        """Return whether a path matches the type chosen with -t.

        Args:
            path (str): The path to test.
            mode (int): The ``st_mode`` of the path, taken without following
                symlinks.

        Returns:
            bool: True if no -t filter is active or the path is of the
                requested type.
        """
        if self.type is None:
            return True
        if self.type == "file":
            return stat.S_ISREG(mode)
        if self.type == "dir":
            return stat.S_ISDIR(mode)
        if self.type == "symlink":
            return stat.S_ISLNK(mode)
        if self.type == "socket":
            return stat.S_ISSOCK(mode)
        if self.type == "pipe":
            return stat.S_ISFIFO(mode)
        if self.type == "char":
            return stat.S_ISCHR(mode)
        if self.type == "block":
            return stat.S_ISBLK(mode)
        if self.type == "executable":
            if not stat.S_ISREG(mode):
                return False
            if os.name == "nt":
                # Windows has no execute bit; go by the PATHEXT extensions
                pathext = os.environ.get("PATHEXT", ".EXE;.BAT;.CMD;.COM").lower().split(";")
                return os.path.splitext(path)[1].lower() in pathext
            return os.access(path, os.X_OK)
        if self.type == "empty":
            if stat.S_ISREG(mode):
                return os.path.getsize(path) == 0
            if stat.S_ISDIR(mode):
                try:
                    return not os.listdir(path)
                except OSError:
                    return False
            return False
        return False

    def find_files(self, directory, filename):
        """Recursively search a directory for files matching a name or glob.

        Applies the depth, gitignore, hidden, extension, and size filters
        configured from the command line.

        Args:
            directory (str): The directory to search in.
            filename (str): The file name or glob pattern to search for.

        Returns:
            list[tuple]: One tuple per match, containing (path, size in
                bytes, size string, modification time, line count, word
                count, character count).
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
 
            listed_dirs = list(dirs)    # -t d/l/e still match these even when we stop descending
            if self.maxdepth > 0:
                # level 1 is the starting directory itself, measured from where the search began
                rel = os.path.relpath(root, directory)
                level = 1 if rel == "." else rel.count(os.sep) + 2
                if level >= self.maxdepth:
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
            if self.exclude_rules:
                dirs[:] = [d for d in dirs if not self._excluded(os.path.join(root, d))]
            for f in (files + listed_dirs if self.type_wants_dirs else files):
                path = os.path.join(root, f)
                file_sz = -1
                try:
                    statinfo = os.stat(path)
                    # lstat so a symlink reports as a link, not as its target
                    file_mode = os.lstat(path).st_mode
                except OSError:
                    if self.type == "symlink":
                        # a broken link can't be stat'ed but is still a link
                        try:
                            statinfo = os.lstat(path)
                            file_mode = statinfo.st_mode
                        except OSError:
                            continue
                    else:
                        sys.stderr.write("Error reading file stats")
                        sys.stderr.flush()
                        continue
                file_sz = statinfo.st_size
                mod_time = statinfo.st_mtime
                file_sz = float(f'{file_sz}')
                file_sz_str = bytes_to_str(file_sz)
                if hasattr(statinfo, "st_file_attributes"):
                    # Windows
                    self.file_hid = bool(statinfo.st_file_attributes & FILE_ATTRIBUTE_HIDDEN)
                else:
                    self.file_hid = (os.path.basename(path).starswith("."))

                if not self.matches_type(path, file_mode):
                    continue
                if self.filterby_ext:
                    matched = False
                    for extension in self.extension_rules:
                        if self.filterby_ext and (self.get_extension(f).lower() == extension.lower()):
                            matched = True
                    if not matched:
                        continue
                if self.size_lower is not None and file_sz < self.size_lower:
                    continue
                if self.size_upper is not None and file_sz > self.size_upper:
                    continue
                if self.size_exact is not None and file_sz != self.size_exact:
                    continue
                if not self.hidden and self.file_hid:   
                    continue   
                if not self.ignoregit and self._gitignored(path):
                    continue
                if self._excluded(path):
                    continue
                have = f.lower() if self.ignorecase else f
                if fnmatch.fnmatchcase(have, want) if wild else have == want:
                        if stat.S_ISREG(file_mode):
                            lines, words, chars = self.count_file_contents(path)
                        else:
                            # never open dirs, pipes, or devices (a pipe read can block)
                            lines = words = chars = 0
                        found_files.append((path,file_sz,file_sz_str, mod_time, lines, words, chars))    # f = name as it is on disk
            if self.verbose:
                sys.stderr.write(f"\rSearching in: {root} ...\n")
                sys.stderr.flush()
        return found_files 

    def list_dir(self):
        """List the non-hidden contents of ``self.directory``.

        Returns:
            str: One line per entry, with its modification time, size in
                bytes, and name.
        """
       
        ret_str = ""
        for f in os.listdir(self.directory):
            if not f.startswith('.'):
                modified = datetime.fromtimestamp(os.path.getmtime(os.path.join(self.directory, f))).strftime("%m/%d/%Y %I:%M %p")
                ret_str += f"{modified}\t{os.path.getsize(os.path.join(self.directory, f)):>15}\t {f}\n"

        return ret_str
      
    def write_out(self, inp_str):
        """Write output to the chosen file, format, or stdout.

        When ``cat`` mode is on, file paths found in ``inp_str`` are replaced
        by their contents.

        Args:
            inp_str (str): The text to write out.
        """
        if self.docat:
            file_list = [f for f in inp_str.splitlines() if os.path.isfile(f)]
            out_buff = ""
            for file in file_list:
                try:
                   with open(file, "r") as f:
                        f.read()
                except Exception as e:
                    sys.stderr.write(f"Error reading {file}: {e}")
                    sys.stderr.flush()
                else:
                    with open(file, "r") as f:
                        out_buff += f'\n\n#--- Contents of {file} ---\n'
                        out_buff += f.read()
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
    """Run the file search and print the elapsed time."""
    timer = Manipulate_files()
    print(f'Time Elapsed: {timer.__init__.elapsed}')
if __name__ == "__main__":
    main()
