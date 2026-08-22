#!/bin/bash
tmux-bridge read codex 1 > /dev/null
tmux-bridge type codex "$1"
tmux-bridge read codex 1 > /dev/null
tmux-bridge keys codex Enter
