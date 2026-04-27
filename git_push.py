"""
git_push.py
Quick git add, commit, push in one command.
Usage:
    python git_push.py                    # commits with timestamp message
    python git_push.py "your message"     # commits with custom message
    python git_push.py --dry-run          # show what would be committed, don't push
"""
import subprocess
import sys
from datetime import datetime

dry_run = "--dry-run" in sys.argv
args    = [a for a in sys.argv[1:] if a != "--dry-run"]
message = args[0] if args else f"Updates {datetime.now().strftime('%Y-%m-%d %H:%M')}"

def run(cmd, capture=True):
    result = subprocess.run(cmd, capture_output=capture, text=True)
    return result

# Always stage everything first
run(["git", "add", "."])

# Show what's staged
status = run(["git", "status", "--short"])
if not status.stdout.strip():
    print("Nothing to commit — working tree clean.")
    sys.exit(0)

print("Changes to be committed:")
print(status.stdout)

# Show a compact diff summary (files + lines changed)
diff = run(["git", "diff", "--cached", "--stat"])
if diff.stdout:
    print(diff.stdout)

if dry_run:
    print("[Dry run] — nothing pushed.")
    sys.exit(0)

# Commit and push
for cmd in [
    ["git", "commit", "-m", message],
    ["git", "push"],
]:
    print(f"Running: {' '.join(cmd)}")
    result = run(cmd)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        # Auto-recover from non-fast-forward (remote has commits we don't have)
        if "non-fast-forward" in result.stderr or "rejected" in result.stderr:
            print("Remote has new commits — pulling and rebasing...")
            pull = run(["git", "pull", "--rebase"])
            if pull.stdout: print(pull.stdout)
            if pull.stderr: print(pull.stderr)
            if pull.returncode != 0:
                print("Rebase failed — resolve conflicts manually.")
                sys.exit(1)
            # Retry push
            retry = run(["git", "push"])
            if retry.stdout: print(retry.stdout)
            if retry.stderr: print(retry.stderr)
            if retry.returncode != 0:
                print("Push still failed after rebase — check manually.")
                sys.exit(1)
            print(f"Done — pulled, rebased, and pushed: '{message}'")
            sys.exit(0)
        print(f"Error on: {' '.join(cmd)}")
        sys.exit(1)

print(f"Done — pushed with message: '{message}'")
