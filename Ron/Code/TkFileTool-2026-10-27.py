import tkinter as tk
from tkinter import ttk
from quick_tk import FormPanel, QuickApp, ToolView

import stat
FILE_ATTRIBUTE_HIDDEN = getattr(stat, "FILE_ATTRIBUTE_HIDDEN", 0x2)
import argparse
import os, sys
import fnmatch
from datetime import datetime
import yaml
import subprocess
from concurrent.futures import ThreadPoolExecutor
from local_functions import colorize, Timed, bytes_to_str, str_to_bytes, clean_ansi, chkstr_isnum

"""
TODO:
Fix output file location pciker
add cat file option
debug extention filter
show hidden toggle
debug max search depth, not workigng at all aymore
add exlude gkob patern
add limit by filesize w/dropdown list of sizes
add execute a command per file found
add excecute batch (all files) sent to one command like cat filelist  | wc
debug why show tree output  format ignores -m maxdepth in gui mode
New:
add search for duplicate files with ptions to auto delete exrta, dislay listof dpes foum
add explorer view to the program soyou get small large extra large icon represntatiom
  sortable  by groups type es dates etc lke explorer
add scp of file ability, perhaps jus tied to n all around send a file to a pogram with arguments
extend dir option to inlude all tha dir offers. as were spnwing dir just add combobox of switch choices
text edit files, again perhaps just tied o send a file ot a given program ala notepad++ 
"""

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

class MyFileUtilityTool(ToolView):
    title = "File Processing Utility"

#    def __init__(self):
#        self.itself  = itself
        
    def build_ui(self):
        # Configure layout (Left Form / Right Console)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)

        # 1. Declare your inputs
        self.form = self.add_form("Settings", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.form.add_text("filename", "Search Pattern", 
        default=f"{self.app.caller.filename}", on_change=self.do_filename)
        self.form.add_file_picker(
                name="directory", label="Seach Location", mode="directory",
                default=f"{self.app.caller.directory}", on_change=self.do_directory)
        self.form.add_button(
            "Show Dir of destination", callback=self.do_showdir, variant="default")
              
        self.form.add_text("extention", "Comma list of extentions", 
        default=f"", on_change=self.do_extention)
        self.form.add_number(
            "maxdepth",
            "Max depth",
            default=self.app.caller.maxdepth,
            min_val=0,
            max_val=500,
            step=1,
            on_change=self.do_maxdepth,
        )
 #       self.form.add_text("maxdepth", "Max Depth of folders to search", 
 #       default=f"{self.app.caller.maxdepth}", on_change=self.do_maxdepth)
        self.form.add_dropdown("sort_dir", "Sort Direction", ["forward", "reverse"],
                on_change=self.do_sort_dir)
        self.form.add_dropdown("outfile_fomat", "Output File Format", 
        ["txt", "csv", "json", "jsonl", "yaml", "yml"], on_change=self.do_out_format)
        self.form.add_file_picker("file_path", "Target File", mode="open", on_change=self.do_output_file)
        self.form.add_button("Execute", callback=self.on_run, variant="primary")

        # 2. Declare your outputs
        self.console = self.add_console("File Search Results", parent=self)
        self.console.grid(row=0, column=1, sticky="nsew")

        # 3. Setup Top Menu Bar
        self.setup_menu()

    def setup_menu(self):
        # Top-level Menu: Configuration
        config_menu = self.menu("Configuration")
        config_menu.add_item(
            "On/Off Options)",
            self.open_onoff_options,
            shortcut="Ctrl+P",
        )
        config_menu.add_item(
            "Open Floating Tool Window... (Non-Modal)",
            self.open_floating_window,
            shortcut="Ctrl+Shift+P",
        )
        config_menu.add_item(
            "Help",
            self.show_help,
            shortcut="Ctrl+Shift+H",
        )
        config_menu.add_separator()
        config_menu.add_item("Exit", self.app.root.quit, shortcut="Alt+F4")

    # =========================================================================
    # OPTION 1: MODAL POPUP DIALOG (self.prompt_form)
    # Recommended for straightforward configuration steps
    # =========================================================================
 
    def show_help(self):
        epilog ="""\
                                                                    Usage: mfind.py [OPTIONS] [pattern] [path]
        
     Arguments:
        [pattern]  the search pattern (a regular expression, unless '--glob' is used; optional)
        [path]...  the root directories for the filesystem search (optional)
        
    Options:epil
        mfind.py [opt. switches] <file name> [path] current directory used if not given
        mfind.py -n <file to search for>
        mfind.py "view*.py" (wildcards * ? [abc] for partial names - quote them on Mac/Linux)
        mfind.py -o <output file name> (stdout default)
        mfind.py -c (cat file contents if found)
        mfind.py -E <extension> (filter results by file extension)
        mfind.py -f <output file format>  (txt, csv, json, jsonl, yaml, yml)
        mfind.py -d (return a dir of specified directory)
        mfind.py -v (verbose output <file name , size, date>)
        mfind.py -i (ignore case on matches)
        mfind.py -sm (sort results by file modification time) **use -s forward/reverse for direction**
        mfind.py -sz (sort results by file size) **use -s forward/reverse for direction**
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
        mfind.py -T Display search results in a visual tree hierarchy
        mfind.py -t Filter by type: file (f), directory (d/dir), symlink (l),
                               executable (x), empty (e), socket (s), pipe (p), char-device
                               (c), block-device (b`
    mfind.py -h (display this help message)
 """
        self.console.write_line(epilog)

    def open_onoff_options(self):
        def build_inputs(form: FormPanel):
            form.add_dropdown(
                name="strategy",
                label="Execution Strategy",
                options=["Momentum Breakout", "Mean Reversion", "VWAP Scalper"],
                default="Momentum Breakout",
            )
            form.add_file_picker(
                name="model_weights",
                label="Model Weights File",
                mode="open",
                filetypes=[("Model Files", "*.pth;*.onnx;*.bin"), ("All Files", "*.*")],
            )
            form.add_file_picker(
                name="log_dir", label="Diagnostics Log Directory", mode="directory"
            )
       # Opens popup dialog centered over the main window
        results = self.prompt_form(
            title="Configure On/Off Options",
            form_builder_fn=build_inputs,
            size=(480, 420),
            ok_text="Apply",
            cancel_text="Cancel",
        )

        if results:
            self.on_apply_inputs(results)

 

    def open_floating_window(self):
        popup = tk.Toplevel(self)
        popup.title("On/Off Options")
        popup.geometry("480x440")
        popup.configure(bg=self.theme.get("bg", "#181825"))

        container = ttk.Frame(popup, style="Surface.TFrame", padding=14)
        container.grid(row=0, column=0, sticky="ew")
        container.rowconfigure(0, weight=0)
        container.rowconfigure(1, weight=1)
        container.columnconfigure(0, weight=0)
        container.columnconfigure(1, weight=1)
        container.columnconfigure(2, weight=1)

        leftside = self.add_form("Calc Options", parent=container)
        leftside.grid(
             row=0,
             column=0,
             rowspan=2,
             sticky="nws",
             padx=0,
             pady=10,
         )       
    
    
     
        # Dropdown boxes
        leftside.add_checkbox(
                "igcase", "Ignore Case", default=self.app.caller.ignorecase, on_change=self.do_igcase
            )
        leftside.add_checkbox(
                "partial", "Partial Matches", default=self.app.caller.partial, on_change=self.do_partial
            )

        leftside.add_checkbox(
            "treeview", "Show Tree View of the results", default=self.app.caller.tree, on_change=self.do_treeview
        )
        leftside.add_checkbox(
            "sortsize", "Sort by filesize", default=self.app.caller.sortsize, on_change=self.do_sortsize
        )
        
        rightside = self.add_form("Calc Options", parent=container)
        rightside.grid(
               row=0,
               column=1,
               rowspan=2,
               sticky="nws",
               padx=0,
               pady=10,
           )                
    
        rightside.add_checkbox(
            "sortmod", "Sort by last mod", default=self.app.caller.sortmod, on_change=self.do_sortmod
        )

        rightside.add_checkbox(
             "do_long", "Long output", default=self.app.caller.do_long, on_change=self.do_do_long
         )

        rightside.add_checkbox(
            "verbose", "Verbose mode", default=self.app.caller.verbose, on_change=self.do_verbose
        )


        # Option checkbox
        rightside.add_checkbox(
            "auto_clean", "Auto-clean null rows on ingest", default=True
        )

        botside = self.add_form("Calc Options", parent=container)
        botside.grid(
               row=1,
               column=0,
               colspan=2,
               sticky="nws",
               padx=0,
               pady=10,
           )         

        # File p  ickers
        botside.add_file_picker(
            name="dataset_file",
            label="Input Dataset (CSV / Parquet)",
            mode="open",
            filetypes=[
                ("Data Files", "*.csv;*.parquet;*.json"),
                ("All Files", "*.*"),
            ],
        )


           # Action Buttons inside the popup
        def _on_submit():
            vals = botside.get_values()
            self.on_apply_inputs(vals)
            popup.destroy()

        botside.add_button(
            "Execute with Selected Files", callback=_on_submit, variant="primary"
        )
 

   
    def on_apply_inputs(self, values: dict):
#        self.console.write_heading("RECEIVED CONFIGURATION FROM POPUP WINDOW")
#        for k, v in values.items():
#            self.console.write_line(f"  • {k}: {v}", "info")

#        feed = values.get("data_source") or values.get("strategy") or "Custom"
#        infile = (
#            values.get("dataset_file") or values.get("model_weights") or "Not Specified"
#        )
#        filename = os.path.basename(infile) if infile else "None"

        pass      
      

    def do_maxdepth(self, inputs):
        if chkstr_isnum(inputs) in ("int", "float"):
            self.app.caller.maxdepth = int(inputs)

    def do_showdir(self, inputs=None):
        if isinstance(inputs, dict) and "directory" in inputs:
            self.app.caller.directory = inputs["directory"]
        self.app.caller.dodir = True
        try:
            result = self.app.caller.run_search(is_gui=True)
            if result is not None:
                for c in result.split("\n"):
                    self.console.write_line(c)
        finally:
            self.app.caller.dodir = None

    def do_do_long(self,inputs):
        self.app.caller.do_long = inputs

    def do_treeview(self, inputs):
        self.app.caller.tree = inputs

    def do_partial(self, inputs):
        self.app.caller.partial = inputs

    def do_verbose(self, inputs):
        self.app.caller.verbose = inputs

    def do_igcase(self, inputs):
         self.app.caller.ignorecase = inputs

    def do_out_format(self, inputs):
        self.app.caller.format = inputs

    def do_output_file(self, inputs):
        self.app.caller.outfile = inputs

    def do_sortmod(self, inputs):
        self.app.caller.sortmod = inputs
        if inputs:
            self.app.caller.sorted = True
        else:
            self.app.caller.sorted = False

    def do_filename(self, inputs):
        self.app.caller.filename = inputs

    def do_directory(self, inputs):
        self.app.caller.directory = inputs

    def do_sort_dir(self, inputs):
        self.app.caller.sorted = inputs

    def do_extention(self, inputs):
        self.app.caller.extension_rules = []
        if inputs.strip().lstrip("."):
            for e in inputs.split(","):
                self.app.caller.extension_rules.append(e)
        """     
        self.app.caller.extension_rules = [e.strip().lstrip(".").lower()
                                for arg in (inputs or []) for e in inputs.split(",")
                                if e.strip().lstrip(".")]
        """
        if self.app.caller.extension_rules != []:
            self.app.caller.filterby_ext = True
        else:
            self.app.caller.extension_rules = None
            self.app.caller.filterby_ext = False


    def do_sortsize(self, inputs):
        self.app.caller.sortsize = inputs
        if inputs:
            self.app.caller.sorted = "size"


    def on_run(self, inputs: dict):
        # 3. Drop in your backend logic!
        # inputs is automatically a clean dict: {'username': '...', 'mode': '...', 'file_path': '...'}

        result = self.app.caller.run_search(is_gui=True)
        if result != None:
            clist = result.split("\n")
            for c in clist:
                self.console.write_line(c)
        """
        self.console.write_heading("Argument List")
        for name, value in self.app.cdict.items():
            self.console.write_line(f"Var {name}: {value}")
        self.app.cdict["_run_gui"] = False
        self.console.write_line(f"_run_gui: {self.app.cdict['\"_run_gui\"']}")
        self.app.cdict["_run_gui"] = True
        self.console.write_line(f"_run_gui: {self.app.cdict['\"_run_gui\"']}")
        """


def safe_print_stdout(content):
    try:
        sys.stdout.write(content)
        sys.stdout.flush()
    except (UnicodeEncodeError, OSError):
        sys.stdout.buffer.write(content.encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()

def safe_print_stderr(content):
    try:
        sys.stderr.write(content)
        sys.stderr.flush()
    except (UnicodeEncodeError, OSError):
        sys.stderr.buffer.write(content.encode("utf-8", errors="replace"))
        sys.stderr.buffer.flush()

"""
To Code Yet

"""

def is_binary_file(filepath):
    """Check if a file appears to contain binary data."""
    try:
        if os.path.isdir(filepath):
            return False
        with open(filepath, "rb") as f:
            chunk = f.read(1024)
            return b"\x00" in chunk
    except OSError:
        return False

def run_for_file(args):
    """Run command template for an individual file result."""
    template, name = args
    if "{}" in template:
        cmd = template.replace("{}", f'"{name}"')
    else:
        cmd = f'{template} "{name}"'
    is_bin = is_binary_file(name)
    try:
        p = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL
        )
        return name, p.returncode, p.stdout or "", p.stderr or "", is_bin
    except Exception as e:
        return name, -1, "", str(e), is_bin

def exec_on_files(template, files, workers=8, output_file="stdout"):
    """Run a command template on each matching file in parallel."""
    file_paths = [f[0] if isinstance(f, (tuple, list)) else f for f in files]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(run_for_file, [(template, f) for f in file_paths]))

    output_lines = []
    had_binary = False
    had_error = False
    for name, rc, out, err, is_bin in results:
        header = f"== {name} (rc={rc})"
        output_lines.append(header)
        if out:
            output_lines.append(out.rstrip("\r\n"))
        if err:
            safe_print_stderr(err if err.endswith("\n") else err + "\n")
        if is_bin:
            had_binary = True
        if rc != 0:
            had_error = True

    content = "\n".join(output_lines) + "\n" if output_lines else ""
    if output_file == "stdout":
        safe_print_stdout(content)
    else:
        try:
            with open(output_file, "w", encoding="utf-8", errors="replace") as f:
                f.write(content)
        except OSError as e:
            safe_print_stderr(f"Error writing to {output_file}: {e}\n")

    if had_binary and had_error:
        safe_print_stderr("[mfind] Note: one or more matching files appeared to be binary. Tip: use '-E <ext>' or '-t f' to narrow search to text files.\n")
    elif had_error:
        safe_print_stderr("[mfind] Note: command returned non-zero exit code for some files. Tip: verify command syntax or file types.\n")

def exec_batch_on_files(template, files, output_file="stdout"):
    """Run a command once passing all matching files as arguments and via stdin."""
    file_paths = [f[0] if isinstance(f, (tuple, list)) else f for f in files]
    if not file_paths:
        return

    quoted_files = " ".join(f'"{f}"' for f in file_paths)
    if "{}" in template:
        cmd = template.replace("{}", quoted_files)
    else:
        cmd = f"{template} {quoted_files}"

    had_binary = any(is_binary_file(f) for f in file_paths)
    try:
        p = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            input="\n".join(file_paths) + "\n",
        )
        if output_file == "stdout":
            if p.stdout:
                safe_print_stdout(p.stdout)
        else:
            with open(output_file, "w", encoding="utf-8", errors="replace") as f:
                if p.stdout:
                    f.write(p.stdout)

        if p.stderr:
            safe_print_stderr(p.stderr)

        if p.returncode != 0:
            safe_print_stderr(f"[mfind] Note: batch command exited with code {p.returncode}. (Tip: verify command syntax or file types)\n")
            if had_binary:
                safe_print_stderr("[mfind] Note: batch list included binary files. Tip: use '-E <ext>' or '-t f' to search only text files.\n")
    except Exception as e:
        safe_print_stderr(f"[mfind] Error executing batch command: {e}\n")

class Manipulate_files:
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
        self.execute = None
        self.exec_batch = None
        self.doexec = False
        self.doexec_batch = False
        self.tree = False
        self.use_ascii = False
        self.found_files = []

        # Majoy bypas decision if -gui given hand off to GUI
        self.parse_arguments()
        if  self.run_gui:
            app = QuickApp(title="File Utility Tool", size=(900, 600), use_ctk=True, resizable=True,theme="Dark Obsidian", caller=self)
            app.set_single_tool(MyFileUtilityTool)
            app.run()
        # Else process the user give inputs from cmd and output 
        else:
            self.run_search(is_gui=False)
 
    def run_search(self, is_gui):
        if not self.dodir and not self.filename:
            if is_gui:
                return "Error: Please specify a search pattern (e.g. -n <name> or positional pattern)."
            else:
                sys.stderr.write("Error: Please specify a search pattern (e.g. -n <name> or positional pattern).\n")
                sys.stderr.flush()
                sys.exit(1)
        if self.dodir and not os.path.isdir(self.directory):
            if is_gui:
                return f"Error: The specified directory '{self.directory}' does not exist."
            else:
                sys.stderr.write(f"Error: The specified directory '{self.directory}' does not exist.\n")
                sys.stderr.flush()
                sys.exit(1)
        # Directory list asked for, list and exit
        elif self.dodir and os.path.isdir(self.directory):
            output = self.list_dir()
            if is_gui:
                return clean_ansi(output)
            else:
                safe_print_stdout(output)
                return

        # Proper arguments given , search for file
        else:
            found_files = self.find_files(self.directory, self.filename)
            self.found_files = found_files
            if found_files:
                if self.sortmod and (self.sorted == "reverse"):
                    found_files.sort(key=lambda x: (x[3]))
                elif self.sortmod:
                    found_files.sort(key=lambda x: (x[3] ), reverse = True)
                elif self.sortsize and (self.sorted == "reverse"):
                    found_files.sort(key=lambda x: (x[1]), reverse=True)
                elif self.sortsize:
                    found_files.sort(key=lambda x: (x[1] ))
                elif self.sorted == "forward":
                    found_files.sort(key=lambda x: os.path.basename(x[0]).casefold())
                elif self.sorted == "reverse":
                    found_files.sort(key=lambda x: os.path.basename(x[0]).casefold(), reverse=True)

                if self.doexec:
                    exec_on_files(self.execute, found_files, output_file=self.output_file)
                elif self.doexec_batch:
                    exec_batch_on_files(self.exec_batch, found_files, output_file=self.output_file)
                elif self.tree:
                    tree_res = self.write_tree_out(found_files)
                    if is_gui:
                        return clean_ansi(tree_res) if tree_res else ""
                    return tree_res
                else:
                    output_rows = []
                    if self.verbose or self.do_long:
                        output_rows.append(f'{"Size":<12}{"Lines":<8}{"Words":<8}{"Chars":<8}{"File Path"}')
                    elif self.size:
                        output_rows.append(f'{"Size":<12}{"File Path"}')

                    for found in found_files:
                        path, bsize, size, mod_time,file_hid, lines, words, chars = found
                        if (self.verbose or self.do_long) and not file_hid:
                            output_rows.append(f'{size:<12}{lines:<8}{words:<8}{chars:<8}{colorize(found[0], "blue")}')
                        elif (self.verbose or self.do_long) and file_hid:
                            output_rows.append(f'{size:<12}{lines:<8}{words:<8}{chars:<8}{colorize(found[0], "red")}')                                
                        elif self.size and file_hid:
                            output_rows.append(f'{size:<12}{colorize(found[0], "red")}')
                        elif self.size and not file_hid:
                             output_rows.append(f'{size:<12}{colorize(found[0], "blue")}')                            
                        elif not file_hid:
                            output_rows.append(colorize(found[0], "blue"))
                        else:                        
                            output_rows.append(colorize(found[0], "red"))     
                    retval = (clean_ansi(self.write_out("\n".join(output_rows), raw_files=[f[0] for f in found_files])))
                    return(retval)

            else:
                entity_type = "directories" if self.type == "dir" else "files"
                if is_gui:
                    return f"Error: No {entity_type} named '{self.filename}' found in directory '{self.directory}'." 
                else:
                    sys.stderr.write(f"Error: No {entity_type} named '{self.filename}' found in directory '{self.directory}'.\n")
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
        [pattern]  the search pattern (a regular expression, unless '--glob' is 
            used; optional)
        [path]...  the root directories for the filesystem search (optional)

    Options:epil
        mfind.py [opt. switches] <file name> [path] current directory used if not 
            given
        mfind.py -n <file to search for>
        mfind.py "view*.py" (wildcards * ? [abc] for partial names - quote them on 
            Mac/Linux)
        mfind.py -o <output file name> (stdout default)
        mfind.py -c (cat file contents if found)
        mfind.py -E <extension> (filter results by file extension)
        mfind.py -f <output file format>  (txt, csv, json, jsonl, yaml, yml)
        mfind.py -d (return a dir of specified directory)
        mfind.py -v (verbose output <file name , size, date>)
        mfind.py -i (ignore case on matches)
        mfind.py -sm (sort results by file modification time) **use -s forward/reverse 
            for direction**
        mfind.py -sz (sort results by file size) **use -s forward/reverse for direction**
        mfind.py -p (find partial matches (like *filename*))
        mfind.py -l (print file statistics <line count, word count, char count>)
        mfind.py -H Search hidden files and directories
        mfind.py -s <forward/reverse> List of files sorted forward or reverse
        mfind.py -m Set maximum search depth (default: none) -m 0 for no recursion 
            pat starting location
        mfind.py -e Exclude entries that match the given glob pattern
        mfind.py -S Limit results based on the size of files using the format 
                <+-><NUM><UNIT>. 
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
                  ** 2 -S arguments, one specifying a +<val> and the other a 
                        -<val> are allowed
                  ** However specifying 2, -S + or 2 -S - raise an ambiguous error  
                  ** specifying both is saying - if size > this AND < that, 
                        show it
        mfind.py -x Execute a command for each search result
        mfind.py -X Execute a command with all search results at once
        mfind.py -T Display search results in a visual tree hierarchy
        mfind.py -t Filter by type: file (f), directory (d/dir), symlink (l),
                        executable (x), empty (e), socket (s), pipe (p), char-device
                        (c), block-device (b)
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
            "-gui",
            "--gui",
            action="store_true",
            help="run in gui mode",
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
            help="\tOutput file format (txt, csv, json, jsonl, yaml, yml)",
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
            help="\tfind partial matches (like *filename*)",
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
            "-T",
            "--tree",
            action="store_true",
            help="Display search results in a visual tree hierarchy",
        )

        parser.add_argument(
            "--ascii",
            action="store_true",
            help=r"Use plain ASCII characters (|--, \--) for tree rendering",
        )

        parser.add_argument(
            "-x",
            "--execute",
            metavar="cmd",
            help="Execute a command for each search result",
        )

        parser.add_argument(
            "-X",
            "--exec-batch",
            metavar="cmd",
            help="Execute a command with all search results at once",
        )

        parser.add_argument("fname", nargs="?")                        # 1st bare word, optional with -E or -t
        parser.add_argument("path", nargs="?")                         # 2nd bare word, optional

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
        # With -E or -t the name pattern is optional: "mfind.py -E txt,json [folder]" or "mfind.py -t d [folder]" lists every match
        if (args.extension or args.type) and not args.name:
            if args.fname is not None and args.path is None and os.path.isdir(args.fname):
                args.path, args.fname = args.fname, None    # lone bare word is the folder
            if args.fname is None:
                args.fname = "*"
        elif args.fname is None and not args.name:
            parser.error("the following arguments are required: fname (or use -E or -t)")
        self.run_gui = args.gui if args.gui else False
        self.sortmod = args.sortmod if args.sortmod else False
        if self.sortmod:
            self.sorted = "mod"
        self.sortsize = args.sortsize if args.sortsize else False
        if self.sortsize:
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
            self.extension_rules = None
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
    
        self.tree = args.tree if args.tree else False
        self.use_ascii = args.ascii if args.ascii else False
        self.execute = args.execute if args.execute else None
        self.exec_batch = args.exec_batch if args.exec_batch else None
        self.doexec = bool(self.execute)
        self.doexec_batch = bool(self.exec_batch)
        if self.doexec and self.doexec_batch:
            parser.error("cannot combine -x/--execute and -X/--exec-batch")
        self.do_long = args.long if args.long else False
        self.partial = args.partial if args.partial else False
        self.ignorecase = args.ignore if args.ignore else False
        self.filename = args.name if args.name else None
        self.filename = args.fname if args.fname else self.filename
        self.output_file = args.outfile if args.outfile else "stdout"
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
            with open(path, "r", encoding="utf-8", errors="replace") as f:
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
            str: The extension without leading dot, or empty string if none.
        """
        ext = os.path.splitext(filename)[1]
        return ext.lstrip(".").lower() if ext else ""

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

    def _is_hidden_entry(self, path, name=None, statinfo=None):
        """Return whether an entry is hidden (starts with a dot or has hidden attribute)."""
        basename = name if name is not None else os.path.basename(path)
        if basename.startswith("."):
            return True
        if os.name == "nt":
            if statinfo is not None and hasattr(statinfo, "st_file_attributes"):
                return bool(statinfo.st_file_attributes & FILE_ATTRIBUTE_HIDDEN)
            try:
                attrs = os.stat(path).st_file_attributes
                return bool(attrs & FILE_ATTRIBUTE_HIDDEN)
            except (OSError, AttributeError):
                pass
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

            if not self.hidden:
                dirs[:] = [d for d in dirs if not self._is_hidden_entry(os.path.join(root, d), d)]
 
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
                mod_time = datetime.fromtimestamp(statinfo.st_mtime)
#                mod_time = statinfo.st_mtime
                file_sz = float(f'{file_sz}')
                file_sz_str = bytes_to_str(file_sz)
                self.file_hid = self._is_hidden_entry(path, f, statinfo)

                if not self.matches_type(path, file_mode):
                    continue
                if self.filterby_ext:
                    matched = False
#                    breakpoint()
                    if self.extension_rules is not None:                   
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
                if not self.ignoregit and self._gitignored(path, is_dir=stat.S_ISDIR(file_mode)):
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
                        found_files.append((path,file_sz,file_sz_str,  mod_time, self.file_hid, lines, words, chars))    # f = name as it is on disk
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
      
    def write_out(self, inp_str, raw_files=None):
        """Write output to the chosen file, format, or stdout.

        When ``cat`` mode is on, file paths are read and their contents
        are appended.

        Args:
            inp_str (str): The text or lines to write out.
            raw_files (list[str] | None): Clean list of matching file paths (uncolored).
        """
        if self.docat:
            file_list = raw_files if raw_files is not None else [f for f in inp_str.splitlines() if os.path.isfile(f)]
            out_buff = ""
            for file in file_list:
                try:
                    with open(file, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    out_buff += f'\n\n#--- Contents of {file} ---\n' + content
                except Exception as e:
                    safe_print_stderr(f"Error reading {file}: {e}\n")
            payload = out_buff
        else:
            payload = inp_str

        # Structured export formats
        if self.format is not None:
            import re
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_payload = ansi_escape.sub('', payload)
            lines = clean_payload.splitlines()
            if self.format in ("json", "jsonl"):
                import json
                formatted = json.dumps(lines, indent=2) if self.format == "json" else "\n".join(json.dumps(l) for l in lines)
            elif self.format in ("yaml", "yml"):
                import yaml
                formatted = yaml.dump(lines)
            elif self.format == "csv":
                import csv, io
                buf = io.StringIO()
                writer = csv.writer(buf)
                for l in lines:
                    writer.writerow([l])
                formatted = buf.getvalue()
            else:  # txt
                formatted = payload

            if self.run_gui:
             
                return (inp_str)
            elif self.output_file == "stdout":
                safe_print_stdout(formatted + "\n")
                return
            else:
                base_out = os.path.splitext(self.output_file)[0]
                target_file = f"{base_out}.{self.format}"
                try:
                    with open(target_file, "w", encoding="utf-8", errors="replace") as f:
                        f.write(formatted)
                except OSError as e:
                    safe_print_stderr(f"Error writing to {target_file}: {e}\n")
                return

        # Plain output
        if self.run_gui:
            return payload #       if payload and not payload.endswith("\n"
        elif (self.output_file == "stdout"):
            safe_print_stdout(payload + "\n" if payload and not payload.endswith("\n") else payload)
        else:
            try:
                with open(self.output_file, "w", encoding="utf-8", errors="replace") as f:
                    f.write(payload + "\n" if payload and not payload.endswith("\n") else payload)
            except OSError as e:
                safe_print_stderr(f"Error writing to {self.output_file}: {e}\n")

    def write_tree_out(self, found_files):
        """Render search results as a visual directory tree hierarchy."""
        tree = {}
        base_dir = os.path.abspath(self.directory)
        for item in found_files:
            path = item[0]
            abs_p = os.path.abspath(path)
            try:
                rel = os.path.relpath(abs_p, base_dir)
            except ValueError:
                rel = path
            parts = rel.split(os.sep)

            curr = tree
            for part in parts[:-1]:
                if part not in curr:
                    curr[part] = {"__meta__": None, "__children__": {}}
                curr = curr[part]["__children__"]

            leaf = parts[-1]
            if leaf not in curr:
                curr[leaf] = {"__meta__": item, "__children__": {}}
            else:
                curr[leaf]["__meta__"] = item
        if self.run_gui:
            root_label = self.directory
        else:
            root_label = colorize(self.directory, "blue") if self.output_file == "stdout" else self.directory
        lines = [root_label]

        def _render_node(node_dict, prefix=""):
            sorted_keys = sorted(
                node_dict.keys(),
                key=lambda s: (not bool(node_dict[s]["__children__"]), s.casefold())
            )
            for i, name in enumerate(sorted_keys):
                is_last = (i == len(sorted_keys) - 1)
                if self.use_ascii:
                    connector = "\\-- " if is_last else "|-- "
                    sub_indent = "    " if is_last else "|   "
                else:
                    connector = "└── " if is_last else "├── "
                    sub_indent = "    " if is_last else "│   "

                meta = node_dict[name]["__meta__"]
                meta_str = ""
                if (self.verbose or self.do_long) and meta is not None:
                    _, _, size_str, _, _, lines_cnt, words_cnt, _ = meta
                    if os.path.isfile(meta[0]):
                        meta_str = f" [{size_str.strip()}, {lines_cnt} lines, {words_cnt} words]"
                    else:
                        meta_str = f" [{size_str.strip()}]"
                elif self.size and meta is not None:
                    _, _, size_str, _, _, _, _, _ = meta
                    meta_str = f" [{size_str.strip()}]"

                is_dir_entry = bool(node_dict[name]["__children__"]) or (meta and os.path.isdir(meta[0]))
                display_name = colorize(name, "blue") if is_dir_entry and self.output_file == "stdout" else name
                lines.append(f"{prefix}{connector}{display_name}{meta_str}")

                children = node_dict[name]["__children__"]
                if children:
                    _render_node(children, prefix + sub_indent)

        _render_node(tree)
        return self.write_out("\n".join(lines))

    def get_summary(self, elapsed=None):
        """Build a descriptive summary of the search criteria and results."""
        total = len(self.found_files)
        parts = []

        if total == 0:
            count_str = "0 results found"
        elif total == 1:
            is_d = os.path.isdir(self.found_files[0][0]) or (self.type in ("d", "dir"))
            count_str = f"1 {'directory' if is_d else 'file'} found"
        else:
            num_dirs = sum(1 for f in self.found_files if os.path.isdir(f[0]) or (self.type in ("d", "dir")))
            num_files = total - num_dirs
            if num_dirs == 0:
                count_str = f"{total} files found"
            elif num_files == 0:
                count_str = f"{total} directories found"
            else:
                count_str = f"{total} results ({num_files} files, {num_dirs} dirs)"
        parts.append(count_str)

        norm_dir = os.path.normpath(self.directory)
        parts.append(f"in '{norm_dir}'")

        if elapsed is not None:
            time_str = f"{elapsed:.2f}s" if isinstance(elapsed, (int, float)) else str(elapsed)
            parts.append(f"({time_str})")

        criteria = []
        if self.filename and self.filename != "*":
            criteria.append(f"pattern: '{self.filename}'")
        if self.type:
            type_names = {
                "f": "regular files", "file": "regular files",
                "d": "directories", "dir": "directories",
                "l": "symlinks", "symlink": "symlinks",
                "x": "executables", "executable": "executables",
                "e": "empty entries", "empty": "empty entries"
            }
            criteria.append(f"filtered by {type_names.get(self.type.lower(), self.type)}")
        if self.filterby_ext:
            criteria.append(f"ext: {','.join(self.extension_rules)}")
        if self.maxdepth > 0:
            criteria.append(f"maxdepth: {self.maxdepth}")
        if self.size_lower is not None or self.size_upper is not None or self.size_exact is not None:
            size_conds = []
            if self.size_lower is not None: size_conds.append(f">={bytes_to_str(self.size_lower)}")
            if self.size_upper is not None: size_conds.append(f"<={bytes_to_str(self.size_upper)}")
            if self.size_exact is not None: size_conds.append(f"=={bytes_to_str(self.size_exact)}")
            criteria.append(f"size: {', '.join(size_conds)}")
        if self.sortmod:
            criteria.append("sorted by mod time" + (" (reverse)" if self.sorted == "reverse" else ""))
        elif self.sortsize:
            criteria.append("sorted by file size" + (" (reverse)" if self.sorted == "reverse" else ""))
        elif self.sorted:
            criteria.append(f"sorted {self.sorted}")
        if self.hidden:
            criteria.append("including hidden")
        if self.ignoregit:
            criteria.append("bypassing .gitignore")
        if self.tree:
            criteria.append("tree view")

        summary = " ".join(parts)
        if criteria:
            summary += f" | {', '.join(criteria)}"
        return summary

def main():
    """Run the file search and print the elapsed time and summary."""
    app = Manipulate_files()
    elapsed = getattr(app.__init__, "elapsed", None)
    summary = app.get_summary(elapsed)
    if app.doexec or app.doexec_batch or app.output_file != "stdout":
        safe_print_stderr(summary + "\n")
    else:
        safe_print_stdout(summary + "\n")

if __name__ == "__main__":
    main()
