#!/usr/bin/env python3
import sys
import os
import time
import subprocess
from anthropic import Anthropic
from openai import OpenAI

# 1. Grab file targets and initialize API clients
if len(sys.argv) < 3:
    print("Error: Missing parameters. Usage: python3 agent_runner.py [claude|codex] [file.py]")
    sys.exit(1)

AGENT_NAME = sys.argv[1]
TARGET_FILE = sys.argv[2]
PEER = "codex" if AGENT_NAME == "claude" else "claude"

# Dynamically route API traffic based on identity
anthropic_client = Anthropic() if AGENT_NAME == "claude" else None
openai_client = OpenAI() if AGENT_NAME == "codex" else None

def read_file(path):
    with open(path, 'r') as f:
        return f.read()

def run_cmd(cmd):
    return subprocess.check_output(cmd, shell=True).decode('utf-8').strip()

# Fetch active session context dynamically
SESSION = run_cmd("tmux display-message -p '#S'")
CODE_BODY = read_file(TARGET_FILE)

# =====================================================================
# STAGE 1: Parallel Independent Analysis
# =====================================================================
print(f"[{AGENT_NAME.upper()}] Commencing structural optimization on {TARGET_FILE}...")

stage_1_prompt = f"""You are an autonomous code optimization engine. Review this trading strategy script:
{CODE_BODY}
Provide a deep performance optimization layout. Maximize calculation speed and fix structural bottlenecks.
No change must negatively affect the trading strategy itelf. As well as the cosmetic errors looked for above
line by line run and debug in memory the alogorithms , test bad data is it handled, missing data, internet outages,
check any file importing the module that the data isnt getting corrputed or tainted. biggest priority is making
this a profitble wining strategy
OUTPUT RULES:
- Start your code patch exactly with the line: === MY PROPOSAL ===
- End your code patch exactly with the line: === END PROPOSAL ===
Do not output conversational filler."""

if AGENT_NAME == "claude":
    response = anthropic_client.messages.create(
        model="claude-sonnet-5-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": stage_1_prompt}]
    ).content[0].text
else:
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": stage_1_prompt}]
    ).choices[0].message.content

# Print the proposal directly onto this agent's terminal panel
print(response)
print(f"=== END OF STAGE 1 FOR {AGENT_NAME.upper()} ===")

# Flip readiness flag in tmux memory
subprocess.run(f"tmux set-option -t {SESSION} @{AGENT_NAME}_ready 1", shell=True)

# Hold at the gate until the orchestrator moves the state to STAGE_2
while run_cmd(f"tmux show-option -qv -t {SESSION} @pipeline_state") != "STAGE_2":
    time.sleep(1.5)

# =====================================================================
# STAGE 2: Cross-Analysis Scrape
# =====================================================================
print(f"[{AGENT_NAME.upper()}] Stage 2 Unlocked. Scraping {PEER}'s terminal output...")

# Pluck the peer's proposal straight out of their panel memory history
peer_raw_terminal = run_cmd(f"tmux-bridge read {PEER} 200")
peer_proposal = peer_raw_terminal.split("=== MY PROPOSAL ===")[-1].split("=== END PROPOSAL ===")[0]

stage_2_prompt = f"""Review the opposite agent's strategy code proposal layout:
{peer_proposal}
Cross-analyze their changes against the original code context. Write a direct critique mapping out their flaws, missing edge cases, or logic gaps."""

if AGENT_NAME == "claude":
    critique = anthropic_client.messages.create(
        model="claude-sonnet-5-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": stage_2_prompt}]
    ).content[0].text
else:
    critique = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": stage_2_prompt}]
    ).choices[0].message.content

print(f"=== CROSS-CRITIQUE FOR {AGENT_NAME.upper()} ===")
print(critique)
print("=== END CRITIQUE ===")

subprocess.run(f"tmux set-option -t {SESSION} @{AGENT_NAME}_ready 1", shell=True)

while run_cmd(f"tmux show-option -qv -t {SESSION} @pipeline_state") != "OPEN_DEBAT":
    time.sleep(1.5)

# =====================================================================
# STAGE 3: Open Autopilot Debate Loop
# =====================================================================
print(f"[{AGENT_NAME.upper()}] Entering open debate floor...")
chat_history = [{"role": "user", "content": f"Here is the strategy file: {CODE_BODY}. Here is your proposal: {response}. Here is your critique of the peer: {critique}. Negotiate with {PEER} to construct a single unified optimized code patch."}]

turn = 0
last_seen = ""

if AGENT_NAME == "claude":
    # Proactively kick off the chat
    opening_argument = "Let's combine our fixes. I noticed your structure has layout advantages but misses array allocation limits. Let's merge my safety constraints into your execution path."
    subprocess.run(f'tmux-bridge message {PEER} "[From: claude] {opening_argument}"', shell=True)
    chat_history.append({"role": "assistant", "content": opening_argument})

while turn < 12:
    if run_cmd(f"tmux show-option -qv -t {SESSION} @pipeline_state") == "COMPLETE":
        print(f"[{AGENT_NAME.upper()}] Consensus reached. Shutting down loop.")
        sys.exit(0)

    peer_lines = run_cmd(f"tmux-bridge read {PEER} 15")
    latest_msg = [line for line in peer_lines.split('\n') if f"[From: {PEER}]" in line]
    
    if latest_msg and latest_msg[-1] != last_seen:
        last_seen = latest_msg[-1]
        raw_text = last_seen.split(f"[From: {PEER}]")[-1].strip()
        turn += 1
        
        chat_history.append({"role": "user", "content": raw_text})
        
        # Call API to generate response
        if AGENT_NAME == "claude":
            reply = anthropic_client.messages.create(model="claude-sonnet-5-5", max_tokens=1500, messages=chat_history).content[0].text
        else:
            reply = openai_client.chat.completions.create(model="gpt-4o", messages=chat_history).choices[0].message.content
            
        chat_history.append({"role": "assistant", "content": reply})
        
        # Ship it right back over the bridge
        subprocess.run(f'tmux-bridge message {PEER} "[From: {AGENT_NAME}] {reply}"', shell=True)
        
        # Check if consensus keyword is triggered by this response
        if "=== FINAL UNIFIED PATCH ===" in reply:
            subprocess.run(f"tmux set-option -t {SESSION} @pipeline_state COMPLETE", shell=True)
            sys.exit(0)
            
    time.sleep(2)
