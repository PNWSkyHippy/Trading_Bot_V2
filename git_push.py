"""
git_push.py
Quick git add, commit, push in one command.
Usage:
    python git_push.py                    # commits with timestamp message
    python git_push.py "your message"     # commits with custom message
"""
import subprocess
import sys
from datetime import datetime

message = sys.argv[1] if len(sys.argv) > 1 else f"Updates {datetime.now().strftime('%Y-%m-%d %H:%M')}"

commands = [
    ["git", "add", "."],
    ["git", "commit", "-m", message],
    ["git", "push"],
]

for cmd in commands:
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        print(f"Error on: {' '.join(cmd)}")
        sys.exit(1)

print("Done — all changes pushed.")
