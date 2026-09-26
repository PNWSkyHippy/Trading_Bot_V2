# Using and maintaining your Trade Analyzer

The program is `Ron/Code/tktrades_list.py`. It uses your existing report loop,
filter comparisons, P&L calculations, grouping, and formatted summaries.
The QuickTk shell supplies the controls and report tables.

## Start it

From `C:\Users\Linda\Trading_Bot_V2` in PowerShell:

```powershell
.\venv312\Scripts\Activate.ps1

# Open the GUI. No filters or other arguments are required.
python .\Ron\Code\tktrades_list.py --gui

# Start the GUI with two filters already filled in.
python .\Ron\Code\tktrades_list.py --gui -k strategy_name,symbol -1 emt -2 ESU6

# Run a terminal report and exit, without opening Tk windows.
python .\Ron\Code\tktrades_list.py -k strategy_name -1 ALL

# Use another trades database in either mode.
python .\Ron\Code\tktrades_list.py --gui --db "C:\Reports\my_trades.db"

# Read the VPS database for one report, without downloading it.
python .\Ron\Code\tktrades_list.py --gui --ssh-host vps.example.com --ssh-user linda --ssh-db /srv/trading/data/trading_bot.db

# Original terminal text-file and CSV output options.
python .\Ron\Code\tktrades_list.py -k strategy_name -1 ALL -o report.txt
python .\Ron\Code\tktrades_list.py -k strategy_name -1 ALL -csv -o report.csv
```

The default database is the project's `data/trading_bot.db`, located relative
to the script, so changing your working directory does not change that default.
Connections are read-only. This tool reads trades; it does not change them.

## Read the VPS database

The GUI has SSH fields on the database tab. Leave **SSH host** blank for the
normal local database. To use the VPS, enter the host name from your SSH
configuration, your SSH user, and the absolute path to the SQLite file on the
VPS. The optional SSH port defaults to `22`. Your existing passwordless SSH
configuration and key are used by the normal Windows `ssh` program.

The same tab now has a **Table** selector. It is filled from the database's
SQLite schema. Selecting `trades` keeps the trade-specific P&L report. Selecting
any other table uses the generic report: every column becomes available as a
search key, value list, sort field, and output column. Generic reports show the
filtered rows without inventing trade totals for data that is not a trade ledger.

SQLite files are not TCP services, so forwarding a port alone cannot make a
remote file look like a local SQLite connection. The program therefore uses
one short-lived SSH session to run a read-only Python query on the VPS. The
session returns the table schema and trade rows as JSON, the report reads them
from an in-memory SQLite connection, and the SSH process exits when that read
is complete. The database file is never written to your computer. Values used
to populate the five dropdowns use the same one-read process.

This requires `ssh.exe` on your PATH and `python3` plus the standard `sqlite3`
module on the VPS. It does not require `paramiko`, `sshtunnel`, or any Python
package installation on your Windows machine. A failed SSH login, missing
remote file, or missing remote Python is shown as a normal report error while
the GUI stays open. The report is read again on the next Run button press.
Your separate `trades_list.py` file has not been edited.

## Build a report graphically

1. On **Database, dates and output**, choose the database if necessary. Press
   **Load database fields / refresh values** after typing a new path or when
   you want to refresh the available choices.
2. On **Search keys (maximum 5)**, open the main selector and check your fields.
   Existing selections retain their row order; new fields go into the next row.
   The numbered rows show exactly which field belongs to each value list.
3. Each row's value dropdown fills from that field in the loaded trade
   dictionaries. For example, `strategy_name` fills with strategy names, and
   `symbol` fills with symbols. Choose several values, or choose `ALL`.
4. The editable line underneath each value dropdown accepts the original
   comma-separated text and comparisons, such as `>=100` or `!=0`. It is the
   value that will be used when you run. Selecting items in the dropdown updates
   that line. Blank values mean `ALL`; a blank search key disables that row.
5. Optionally choose a sort field for each row, dates, output columns, and the
   switches below the tabs. Then press **Run report**.

The per-row key boxes also let you change or clear an individual field directly.
Changing a row's field resets its values to `ALL` and fills its new choices.
Choices include both open and closed trades; **Open trades** determines which
records the report actually uses. Reports reread the database on every run.

Without **AND filters**, each active search key opens its own window, up to five
windows per run. All selected groups for a key go into that key's window.
With **AND filters**, one combined report contains only trades that pass every
selected filter, just as `-A` does in the terminal.

Each report window has:

- **Sortable trades**: click headings to sort; use Filter to narrow the visible
  rows. These actions affect only that window's table.
- **Original report and summaries**: the original formatted report with its
  group totals. It retains the original run order and totals when the table is
  sorted or searched. Terminal reports still use the original ANSI colors;
  this text tab removes ANSI escape codes.
- **Export visible CSV**: saves the currently visible table in its current order.
- **Save original text**: saves the original report and group summaries.

You can change the controls and run again while old windows stay open. Old
windows keep their own data, sorting, and exports. Reset changes the controls
for the next report and keeps your current database selection.

## Dates, fields, switches, and files

Dates use `YYYY-MM-DDTHH:MM`. The calendar fills the start at `00:00` or the end
at `23:59`; edit the entry to choose a different time. Leave an entry blank for
no limit at that end. The existing engine checks entry time against the start
and exit time against the end. It is not an interval-overlap query.

The output-field chooser supports multiple columns. Blank means your original
default columns. Typing `ALL` uses all database columns. `-k ALL` expands to the
original five default keys: strategy, symbol, exit reason, quantity, and broker
order ID. Each CLI key still needs a value-list option unless the date-only
defaults apply.

All the original boolean options are available as checkboxes and in **View**:
open trades, reverse sort, extended IDs, AND filters, CSV output, and field names
only. **Show field names** also provides the `-N` information directly. If only
some GUI rows have a sort field, other active rows use their own search key as
their initial sort field. You can always sort a result window by any heading.

In the GUI, an optional output filename supplies the folder and base name.
Each report adds its key and a timestamp, so repeated runs create separate
files. With CSV checked and no filename, automatic exports go into the current
working directory. Without CSV checked, a provided filename produces text.
Window export buttons ask for a folder and generate unique names automatically.
Files use exclusive creation, so an existing file cannot be overwritten even
if a generated name collides. Automatic CSV contains the report's original
column values, including full IDs; **Export visible CSV** reflects the displayed
table, including shortened IDs when extended IDs are turned off.

The CLI retains its original append-to-file behavior for `-o`. `-csv` without
`-o` now supplies a timestamped filename. GUI CSV uses real table cells and
standard CSV quoting; the CLI retains its original formatted CSV output.

## Where to change things in the code

The class remains `TradeAnalyzerTool`, matching your existing QuickTk shell.

| Method or attribute | What it is for |
| --- | --- |
| `build_ui()` | Controls, labels, tabs, layout, and View switches. Start here for visual changes. |
| `self.option_vars`, `self.key_vars`, `self.value_vars`, `self.sort_vars` | Tk variables: what the controls currently display. |
| `populate_filter_choices()` | Gives each value dropdown the choices for its selected field. |
| `self.available_trades` | Loaded trade dictionaries used to build choices in memory. |
| `read_controls()` | Copies the current controls into `self.args`. |
| `self.args` | The option holder used by both modes, with the same names as argparse. |
| `main_loop()` | Your report engine. Reads `self.args`, fills shared working settings such as `self.is_sorted` and `self.key_list`, and runs the existing processing. |
| `proc_dict()` | Original filtering, totals, and formatted trade lines. It also captures accepted GUI rows at the same point. |
| `begin_report()` | Starts one GUI result bucket for a key, or one for the combined AND report. |
| `print_outfile()` | Sends formatted text to terminal/file in CLI mode, or captures it for a GUI report. |
| `open_report_window()` | Builds a report's independent table, text tab, and export buttons. |
| `write_report_file()` | Writes a new GUI CSV/text file with a unique name. |
| `main()` at the bottom | Parses once, then chooses terminal mode or creates QuickApp. |

There is no giant `main_values` return dictionary. Shared report settings live
on `self`; temporary counters and function arguments remain local. `main_loop`
resets its result list before each run. A window keeps its earlier result bucket,
so replacing `self.reports` on the next run cannot change old windows.

The CLI creates an instance for reporting without initializing its Tk frame.
It never needs a Tk root window. The GUI initializes the frame normally through
QuickApp. Both paths use the same class methods.

The old `sys.exit` validation remains in the report code. The GUI catches those
exits and displays the error, keeping the application open for corrections.
Report calculations run on Tk's main thread for simplicity; very large reports
may pause the controls while they are being built.

The former sample-data panel now serves as a field/value browser. A useful
future addition there would be a small recent-report list with key names,
filters, and timestamps, letting you bring an existing report window forward.

## Check future edits

`Ron/Code/test_tktrades_gui.py` uses a temporary database. It checks original
report formatting and file output, repeat runs, AND filtering, open/empty data,
field/value dropdowns, five-window runs, sorting, export, and error recovery.
Its comparison with the separate legacy file supplies that file's currently
missing `build_hdr_list` helper in memory, only inside the test.

```powershell
.\venv312\Scripts\Activate.ps1
$tradesTestTemp = Join-Path $env:TEMP ('tktrades-tests-' + [guid]::NewGuid().ToString('N'))
python -m pytest .\Ron\Code\test_tktrades_gui.py -q --basetemp $tradesTestTemp
```

The fresh temporary folder avoids an existing Windows permission problem with
the default `pytest-of-Linda` temporary directory.

### Report totals, colors and VPS defaults

The Sortable trades tab includes a resizable totals section below the table.
It repeats each group's original Total Trades, Total P&L, average win/loss,
win/loss percentages, high/low symbols and fees. These are the report's full
group totals; searching the visible table does not recalculate them.

The sortable table uses a small Tk Text-backed table in `trade_report_table.py`
so each decimal value can keep the CLI color: positive/zero green, negative red.
IDs, dates, symbols and other text stay neutral; column headings are purple.
Click headings to sort, use Filter to search, and select/copy text normally.
CSV export uses raw values rather than the six-decimal display formatting.
The totals and Original report and summaries tab use text tags to preserve the original individual foreground/background colors
and bold text. ANSI escape codes are kept in the report snapshot and translated
for display; saved text and CSV files remain plain text.
CSV exports include the visible trade rows followed by a blank row and a separate
totals section with Group, Metric and Value columns. These totals describe all
report rows, even when the table search hides some trades. Text exports include
the original formatted report and its totals blocks.

The GUI initially fills SSH host `187.127.248.52`, user `ronh`, and remote path
`/opt/trading_bot_v2/data/trading_bot.db`. Clear SSH host for local mode. Explicit
SSH options override these values, and supplying a different local `--db` path
keeps local mode unless an SSH host is supplied. Command-line-only runs retain
their local database default.

Run report executes database reads and report calculations in a background thread.
An animated progress bar indicates activity while SSH is running; it is not a
percentage estimate. Run report is disabled until completion, and errors restore
the button. Each run snapshots its inputs. Tk windows are created on the main
thread after the worker returns.
