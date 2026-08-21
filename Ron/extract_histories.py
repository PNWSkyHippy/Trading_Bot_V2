import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime

HOME_DIR = Path.home()
OUTPUT_DIR = HOME_DIR / "Desktop" / "AI_Chat_Exports"

# Expanded structural fallbacks for Codex and Claude
CODEX_PATHS = [
    HOME_DIR / ".codex" / "logs_1.sqlite",
    HOME_DIR / ".codex" / "state_5.sqlite",
    HOME_DIR / ".codex" / "logs_2.sqlite"
]
CLAUDE_PROJECTS_DIR = HOME_DIR / ".claude"

def setup_output_folder():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Export folder active: {OUTPUT_DIR}\n")

def extract_codex_history():
    print("🤖 Checking Codex Storage...")
    found_any = False
    for db_path in CODEX_PATHS:
        if db_path.exists():
            found_any = True
            print(f"   Found Codex Database: {db_path.name}")
            try:
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                cursor = conn.cursor()
                
                # Dynamic table structure discovery to bypass app update changes
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [t[0] for t in cursor.fetchall()]
                
                target_table = "messages" if "messages" in tables else ("threads" if "threads" in tables else None)
                if not target_table:
                    print(f"   ⚠️ Unknown table schema in {db_path.name}. Found tables: {tables}")
                    continue
                
                cursor.execute(f"SELECT * FROM {target_table} LIMIT 5000;")
                rows = cursor.fetchall()
                
                if rows:
                    filename = OUTPUT_DIR / f"extracted_{db_path.stem}_raw.txt"
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(f"# Raw DB Dump: {db_path.name}\n\n")
                        for r in rows:
                            f.write(f"{str(r)}\n\n---\n")
                    print(f"   ✅ Saved fallback data to {filename.name}")
            except Exception as e:
                print(f"   ❌ Error reading {db_path.name}: {e}")
            finally:
                if 'conn' in locals(): conn.close()
    if not found_any:
        print("   ℹ️ No local Codex databases detected (Expected since it is uninstalled).")

def extract_claude_history():
    print("\n📦 Scanning Claude Directory deeply...")
    if not CLAUDE_PROJECTS_DIR.exists():
        print(f"   ❌ Claude folder not found at {CLAUDE_PROJECTS_DIR}")
        return

    extracted_count = 0
    # Walk through absolutely everything inside the .claude directory
    for root, _, files in os.walk(CLAUDE_PROJECTS_DIR):
        for file in files:
            if file.endswith(('.jsonl', '.json', '.log')):
                file_path = Path(root) / file
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    
                    valid_text_blocks = []
                    for line in lines:
                        cleaned = line.strip()
                        if not cleaned: continue
                        
                        # Try parsing as JSON to find raw text, user queries, or model outputs
                        try:
                            data = json.loads(cleaned)
                            if isinstance(data, dict):
                                # Flatten and capture string values over 10 characters long
                                for k, v in data.items():
                                    if isinstance(v, str) and len(v) > 10 and not v.startswith('{'):
                                        valid_text_blocks.append(f"[{k.upper()}]: {v}")
                        except json.JSONDecodeError:
                            # If it's a standard log file, pull the raw string line
                            if len(cleaned) > 20 and not cleaned.startswith(('{', '[')):
                                valid_text_blocks.append(cleaned)
                    
                    if valid_text_blocks:
                        out_file = OUTPUT_DIR / f"claude_extracted_{file_path.stem}_{extracted_count}.md"
                        with open(out_file, "w", encoding="utf-8") as out_f:
                            out_f.write(f"# Data Source: {file_path.name}\n\n")
                            out_f.write("\n\n---\n\n".join(valid_text_blocks))
                        extracted_count += 1
                except Exception as e:
                    pass

    print(f"   ✅ Processed Claude artifacts. Created {extracted_count} text extracts.")

if __name__ == "__main__":
    setup_output_folder()
    extract_codex_history()
    extract_claude_history()
    print("\n🎉 Done! Check your Desktop folder now.")
