#!/usr/bin/env bash
# Refresh the published Graphify map from a disposable Git worktree.
#
# The live checkout may contain the production database and intentional
# VPS-local edits.  This script must never reset, merge, stash, or clean that
# checkout; only MAP_WORKTREE is safe to reset to origin/main.
set -Eeuo pipefail

LIVE_REPO="/opt/trading_bot_v2"
# This belongs to the service account rather than /opt: /opt itself is not
# writable by ronh, while this remains wholly separate from LIVE_REPO.
MAP_WORKTREE="/home/ronh/trading_bot_v2_map_sync"
GRAPH_LINK="/opt/trading_bot_v2_graph_analysis"
LOCK_FILE="/tmp/trading_bot_v2_map_sync.lock"

log() {
    printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"
}

fail() {
    log "ERROR: $*"
    exit 1
}

require_graph_files() {
    local graph_dir="$1/graphify-out"
    [[ -s "$graph_dir/graph.json" ]] || fail "graphify-out/graph.json is missing or empty in $1"
    [[ -s "$graph_dir/GRAPH_REPORT.md" ]] || fail "graphify-out/GRAPH_REPORT.md is missing or empty in $1"
    [[ -s "$graph_dir/manifest.json" ]] || fail "graphify-out/manifest.json is missing or empty in $1"
}

log "Starting published Graphify map synchronization."
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    log "Another synchronization is already running; exiting normally."
    exit 0
fi

[[ -d "$LIVE_REPO/.git" ]] || fail "live Git checkout is missing: $LIVE_REPO"
[[ -d "$(dirname "$MAP_WORKTREE")" ]] || fail "map-worktree parent directory is missing"

# Fetch is safe with a dirty live checkout.  Do not merge into it.
git -C "$LIVE_REPO" fetch --prune origin main

if [[ -e "$MAP_WORKTREE/.git" ]]; then
    [[ "$(git -C "$MAP_WORKTREE" rev-parse --is-inside-work-tree 2>/dev/null || true)" == "true" ]] || \
        fail "existing map path is not a Git worktree: $MAP_WORKTREE"
    [[ "$(git -C "$MAP_WORKTREE" rev-parse --git-common-dir)" == "$LIVE_REPO/.git" ]] || \
        fail "refusing to reset a worktree not attached to $LIVE_REPO"

    # MAP_WORKTREE is dedicated to published graph artifacts.  Resetting this
    # verified worktree cannot affect the live checkout or VPS-local edits.
    git -C "$MAP_WORKTREE" checkout --detach origin/main
    git -C "$MAP_WORKTREE" reset --hard origin/main
elif [[ -e "$MAP_WORKTREE" ]]; then
    fail "map worktree path exists but is not a Git worktree: $MAP_WORKTREE"
else
    git -C "$LIVE_REPO" worktree add --detach "$MAP_WORKTREE" origin/main
fi

require_graph_files "$MAP_WORKTREE"

expected_link="$MAP_WORKTREE/graphify-out"
resolved_link="$(readlink -f "$GRAPH_LINK" 2>/dev/null || true)"
if [[ "$resolved_link" != "$expected_link" ]]; then
    if [[ -e "$GRAPH_LINK" && ! -L "$GRAPH_LINK" ]]; then
        fail "analysis path exists and is not a symbolic link: $GRAPH_LINK"
    fi
    ln -sfnT "$expected_link" "$GRAPH_LINK"
    resolved_link="$(readlink -f "$GRAPH_LINK")"
fi
[[ "$resolved_link" == "$MAP_WORKTREE/graphify-out" ]] || \
    fail "analysis link points to an unexpected location: $resolved_link"

log "Map worktree commit: $(git -C "$MAP_WORKTREE" rev-parse HEAD)"
log "Graph size: $(stat -c '%s' "$MAP_WORKTREE/graphify-out/graph.json") bytes"
log "Analysis path: $GRAPH_LINK -> $resolved_link"
log "Published Graphify map synchronization completed successfully."
