def save_log_to_file(filename, content_list):
    """Takes a list of string lines and writes them to a text file."""
    try:
        with open(
            filename, "w", encoding="utf-8"
        ) as file:
            for line in content_list:
                file.write(line + "\n")
        print(
            f"\n[SUCCESS] Reference guide saved to '{filename}'"
        )
    except IOError as e:
        print(
            f"\n[ERROR] Could not write to file: {e}"
        )


# 1. Create an empty list to hold your cheat sheet text
cheat_sheet_lines = []


# 2. A helper to print and store lines simultaneously
def log_step(text):
    print(text)  # Prints to your VS Code terminal
    cheat_sheet_lines.append(
        text
    )  # Saves it for the text file


# =====================================================================
# EXAMPLE USAGE IN YOUR BASIC LIST SECTION
# =====================================================================
log_step(
    "=================================================="
)
log_step(
    "          PYTHON DATA STRUCTURES REFERENCE        "
)
log_step(
    "=================================================="
)

log_step("\n--- 1. BASIC LISTS ---")
basic_list = ["131", "798", "465", "0"]
log_step(f"1. Created basic_list = {basic_list}")

basic_list.append("989")
log_step(f"2. After append '989' = {basic_list}")

# =====================================================================
# AT THE VERY END OF YOUR SCRIPT
# =====================================================================
# Call the file-writing function to dump everything into a file
save_log_to_file(
    "python_102_cheat_sheet.txt",
    cheat_sheet_lines,
)
