import csv
import sqlite3

try:
    conn = sqlite3.connect("practice.db")
    cursor = conn.cursor()

    # 1. Create the table manually (match your CSV column types)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            signup_date TEXT
        )
    """)

    # 2. Open the CSV file and read rows
    with open("users.csv", "r") as file:
        csv_reader = csv.reader(file)
        next(csv_reader)  # Skip the header row if your CSV has one

        # 3. Bulk insert the rows safely using placeholders
        cursor.executemany(
            "INSERT INTO users VALUES (?, ?, ?)",
            csv_reader,
        )

    conn.commit()
    print("Data inserted successfully using pure Python!")

except sqlite3.Error as e:
    print(f"Database error: {e}")
finally:
    if "conn" in locals():
        conn.close()
