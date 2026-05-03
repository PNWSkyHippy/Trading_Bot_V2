import re
import sys

def replace_in_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(
        r"use_container_width\s*=\s*True",
        "width='stretch'",
        content
    )

    content = re.sub(
        r"use_container_width\s*=\s*False",
        "width='content'",
        content
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✔ Updated: {filepath}")


if __name__ == "__main__":
    replace_in_file(sys.argv[1])