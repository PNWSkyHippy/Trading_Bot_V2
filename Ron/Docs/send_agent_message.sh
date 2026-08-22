#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "Usage: bash Ron/Docs/send_agent_message.sh <claude|codex> <message>" >&2
    exit 1
fi
if [[ -z "${TMUX:-}" || -z "${TMUX_PANE:-}" ]]; then
    echo "ERROR: send_agent_message.sh must run from an agent's tmux pane." >&2
    exit 1
fi

TARGET="$1"
shift
MESSAGE="$*"
case "$TARGET" in
    claude|codex) ;;
    *) echo "ERROR: Stage 3 peer target must be claude or codex." >&2; exit 1 ;;
esac

SENDER="$(tmux display-message -p -t "$TMUX_PANE" '#{@name}')"
if [[ -z "$SENDER" ]]; then
    SENDER="$TMUX_PANE"
fi

# Long bracketed pastes can leave Codex's terminal composer busy for minutes and
# block the sending agent's shell. Persist the full content and send a compact
# pointer instead; both agents share this repository and can read the file.
MAX_INLINE_CHARS="${PIPELINE_MAX_INLINE_PEER_CHARS:-900}"
if (( ${#MESSAGE} > MAX_INLINE_CHARS )); then
    SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
    REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
    PEER_DIR="$REPO_ROOT/reports/agent_pipeline/peer_messages"
    mkdir -p "$PEER_DIR"
    MESSAGE_FILE="$PEER_DIR/$(date +'%Y%m%d-%H%M%S')_${SENDER//[^a-zA-Z0-9_.-]/_}_to_${TARGET}.md"
    printf '%s\n' "$MESSAGE" > "$MESSAGE_FILE"
    MESSAGE="Long peer message saved to $MESSAGE_FILE. Read that file now, then respond through send_agent_message.sh."
fi

# tmux-bridge enforces read-before-type and read-before-keys. Its `message`
# command does not press Enter and adds a "load the smux skill" header that can
# distract an agent into auditing the transport. Use the primitive operations
# directly and provide an unambiguous authorized Stage 3 peer header.
PAYLOAD="[AUTHORIZED STAGE 3 PEER MESSAGE from:$SENDER] $MESSAGE"
tmux-bridge read "$TARGET" 1 >/dev/null
tmux-bridge type "$TARGET" "$PAYLOAD"
sleep "${PIPELINE_PROMPT_SETTLE_SECONDS:-2}"
SUBMIT_COUNT=1
if [[ "$TARGET" == "codex" ]]; then
    SUBMIT_COUNT="${PIPELINE_CODEX_SUBMIT_COUNT:-3}"
fi
for ((submit_attempt = 1; submit_attempt <= SUBMIT_COUNT; submit_attempt++)); do
    tmux-bridge read "$TARGET" 1 >/dev/null
    tmux-bridge keys "$TARGET" Enter
    sleep 2
done
tmux-bridge read "$TARGET" 3 >/dev/null
