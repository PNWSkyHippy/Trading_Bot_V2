#!/usr/bin/env python3
import sys
import os
import time
import subprocess
from anthropic import Anthropic
from openai import OpenAI

if len(sys.argv) < 3:
    print("Error: Missing parameters. Usage: python3 agent_runner.py [claude|codex] [file.py]")
    sys.exit(1)

AGENT_NAME = sys.argv[1]
TARGET_FILE = sys.argv[2]
PEER = "codex" if AGENT_NAME == "claude" else "claude"

anthropic_client = Anthropic() if AGENT_NAME == "claude" else None
openai_client = OpenAI() if AGENT_NAME == "codex" else None

def read_file(path):
    with open(path, 'r') as f:
        return f.read()

def run_cmd(cmd_list):
    # SECURE: Pass arguments as a list with shell=False to eliminate command injection completely
    return subprocess.check_output(cmd_list, shell=False).decode('utf-8').strip()

SESSION = run_cmd(["tmux", "display-message", "-p", "#S"])
CODE_BODY = read_file(TARGET_FILE)

# =====================================================================
# STAGE 1: Parallel Optimization Review
# =====================================================================
print(f"[{AGENT_NAME.upper()}] Commencing structural optimization on {TARGET_FILE}...")

stage_1_prompt = f"""Review this trading strategy script:
{CODE_BODY}
Provide a deep performance optimization layout. Maximize calculation speed and fix structural bottlenecks.
OUTPUT RULES:
- Start your code patch exactly with the line: === MY PROPOSAL ===
- End your code patch exactly with the line: === END PROPOSAL ===
- Skip all conversational preamble and background explanations. Output ONLY the code and the markers."""

if AGENT_NAME == "claude":
    response = anthropic_client.messages.create(
        model="claude-sonnet-5-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": stage_1_prompt}]
    ).content.text
else:
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": stage_1_prompt}]
    ).choices.message.content

print(response)
print(f"=== END OF STAGE 1 FOR {AGENT_NAME.upper()} ===")

subprocess.run(["tmux", "set-option", "-t", SESSION, f"@{AGENT_NAME}_ready", "1"], shell=False)

while run_cmd(["tmux", "show-option", "-qv", "-t", SESSION, "@pipeline_state"]) != "STAGE_2":
    time.sleep(1.5)

# =====================================================================
# STAGE 2: Cross-Analysis Scrape
# =====================================================================
print(f"[{AGENT_NAME.upper()}] Stage 2 Unlocked. Scraping {PEER}'s terminal output...")

peer_raw_terminal = run_cmd(["tmux-bridge", "read", PEER, "200"])
try:
    peer_proposal = peer_raw_terminal.split("=== MY PROPOSAL ===")[-1].split("=== END PROPOSAL ===")[0]
except:
    peer_proposal = peer_raw_terminal

stage_2_prompt = f"""Review the opposite agent's strategy code proposal layout:
{peer_proposal}
Cross-analyze their changes against the original code context. Write a direct critique mapping out their flaws, missing edge cases, or logic gaps."""

if AGENT_NAME == "claude":
    critique = anthropic_client.messages.create(
        model="claude-sonnet-5-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": stage_2_prompt}]
    ).content.text
else:
    critique = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": stage_2_prompt}]
    ).choices.message.content

print(f"=== CROSS-CRITIQUE FOR {AGENT_NAME.upper()} ===")
print(critique)
print("=== END CRITIQUE ===")

subprocess.run(["tmux", "set-option", "-t", SESSION, f"@{AGENT_NAME}_ready", "1"], shell=False)

while run_cmd(["tmux", "show-option", "-qv", "-t", SESSION, "@pipeline_state"]) != "OPEN_DEBAT":
    time.sleep(1.5)

# =====================================================================
# STAGE 3: Open Autopilot Debate Loop
# =====================================================================
print(f"[{AGENT_NAME.upper()}] Entering open debate floor...")
chat_history = [{"role": "user", "content": f"Here is the strategy file: {CODE_BODY}. Here is your proposal: {response}. Here is your critique of the peer: {critique}. Negotiate with {PEER} to construct a single unified optimized code patch."}]

turn = 0
last_seen = ""

if AGENT_NAME == "claude":
    opening_argument = "Let's combine our fixes. I noticed your structure has layout advantages but misses array allocation limits. Let's merge my safety constraints into your execution path."
    subprocess.run(["tmux-bridge", "message", PEER, f"[From: claude] {opening_argument}"], shell=False)
    chat_history.append({"role": "assistant", "content": opening_argument})

while turn < 12:
    if run_cmd(["tmux", "show-option", "-qv", "-t", SESSION, "@pipeline_state"]) == "COMPLETE":
        print(f"[{AGENT_NAME.upper()}] Consensus reached. Shutting down loop.")
        sys.exit(0)

    peer_lines = run_cmd(["tmux-bridge", "read", PEER, "15"])
    latest_msg = [line for line in peer_lines.split('\n') if f"[From: {PEER}]" in line]
    
    if latest_msg and latest_msg[-1] != last_seen:
        last_seen = latest_msg[-1]
        raw_text = last_seen.split(f"[From: {PEER}]")[-1].strip()
        turn += 1
        
        chat_history.append({"role": "user", "content": raw_text})
        
        if AGENT_NAME == "claude":
            reply = anthropic_client.messages.create(model="claude-sonnet-5-5", max_tokens=4000, messages=chat_history).content.text
        else:
            reply = openai_client.chat.completions.create(model="gpt-4o", messages=chat_history).choices.message.content
            
        chat_history.append({"role": "assistant", "content": reply})
        
        # SECURE: Safe list passing avoids quote breakouts
        subprocess.run(["tmux-bridge", "message", PEER, f"[From: {AGENT_NAME}] {reply}"], shell=False)
        
        if "=== FINAL UNIFIED PATCH ===" in reply:
            subprocess.run(["tmux", "set-option", "-t", SESSION, "@pipeline_state", "COMPLETE"], shell=False)
            sys.exit(0)
            
    time.sleep(2)
