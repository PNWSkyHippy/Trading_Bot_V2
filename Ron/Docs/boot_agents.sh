#!/usr/bin/env bash
set -euo pipefail

# Build the four-pane workspace used by run_pipeline.sh. This script must be
# launched from an existing tmux pane under WSL/Ubuntu.
if [[ -z "${TMUX:-}" ]]; then
    echo "ERROR: start tmux first, then run: bash Ron/Docs/boot_agents.sh" >&2
    exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

for command_name in tmux tmux-bridge claude codex; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "ERROR: required command not found in WSL PATH: $command_name" >&2
        exit 1
    fi
done

# Capture real pane IDs as they are created. Pane IDs are not guaranteed to be
# %0-%3 when another tmux server/session has existed previously.
CLAUDE_PANE="$(tmux display-message -p '#{pane_id}')"
CODEX_PANE="$(tmux split-window -h -c "$REPO_ROOT" -P -F '#{pane_id}')"
tmux select-pane -t "$CLAUDE_PANE"
CURSOR_PANE="$(tmux split-window -v -c "$REPO_ROOT" -P -F '#{pane_id}')"
tmux select-pane -t "$CODEX_PANE"
RON_PANE="$(tmux split-window -v -c "$REPO_ROOT" -P -F '#{pane_id}')"
tmux select-layout tiled >/dev/null

tmux-bridge name "$CLAUDE_PANE" claude
tmux-bridge name "$CODEX_PANE" codex
tmux-bridge name "$CURSOR_PANE" cursor
tmux-bridge name "RON_PANE" ron

# Let each new login shell finish initialization before typing commands into it.
sleep 2

start_command() {
    local target="$1"
    shift
    local command_text="$*"
    tmux-bridge read "$target" 1 >/dev/null
    tmux-bridge type "$target" "$command_text"
    tmux-bridge read "$target" 1 >/dev/null
    tmux-bridge keys "$target" Enter
}

# These are the interactive CLI agents used by every pipeline stage. The
# pipeline talks to these processes directly; it does not start Python API
# substitutes and therefore needs neither openai nor anthropic in WSL Python.
start_command claude "claude"
start_command codex "codex"
start_command cursor "cursor"


tmux set-option @pipeline_state "IDLE"
tmux set-option @claude_ready "0"
tmux set-option @codex_ready "0"
tmux set-option @cursor_ready "0"

# Cursor was launched in the background, so this pane is back at a normal WSL
# shell prompt. Leave focus here. Focusing Claude caused the user's next
# `bash run_pipeline.sh ...` command to be submitted to Claude as chat text.
tmux select-pane -t "$CURSOR_PANE"
echo "Agents launched. Focus moved to the Cursor/driver shell pane."
echo "Allow Claude and Codex to finish loading, then run here:"
echo "  bash Ron/Docs/run_pipeline.sh strategies/bollinger_breakout.py"
