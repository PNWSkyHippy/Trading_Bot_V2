import os
from pathlib import Path

OUTPUT_DIR = Path.home() / "Desktop" / "AI_Chat_Exports"
MERGED_FILE = OUTPUT_DIR / "ALL_CLAUDE_HISTORY_MERGED.md"

def merge_extracted_files():
    if not OUTPUT_DIR.exists():
        print("❌ Export folder not found on Desktop.")
        return
        
    all_files = sorted([f for f in OUTPUT_DIR.glob("claude_extracted_*.md")])
    
    if not all_files:
        print("⚠️ No extracted Claude files found to merge.")
        return

    print(f"🔄 Merging {len(all_files)} files into one document...")
    
    with open(MERGED_FILE, "w", encoding="utf-8") as outfile:
        outfile.write("# Unified AI Chat History Export\n")
        outfile.write(f"Generated on: {os.path.basename(str(MERGED_FILE))}\n")
        outfile.write("="*40 + "\n\n")
        
        for file_path in all_files:
            outfile.write(f"\n\n## 📄 SOURCE FILE: {file_path.name}\n")
            outfile.write("-" * 40 + "\n\n")
            
            with open(file_path, "r", encoding="utf-8", errors="ignore") as infile:
                outfile.write(infile.read())
                
    print(f"✅ Success! Created unified file: {MERGED_FILE.name}")

if __name__ == "__main__":
    merge_extracted_files()
