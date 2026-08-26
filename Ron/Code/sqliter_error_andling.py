import sqlite3

try:
    conn = sqlite3.connect("company.db")
    cursor = conn.cursor()

    # Intentional error: column 'bonus' does not exist
    cursor.execute(
        "SELECT name, bonus FROM employees"
    )
    results = cursor.fetchall()

except sqlite3.OperationalError as e:
    print(
        f"Operational error occurred (e.g., syntax, missing table/column): {e}"
    )

except sqlite3.IntegrityError as e:
    print(
        f"Data integrity error occurred (e.g., UNIQUE constraint violation): {e}"
    )

except sqlite3.Error as e:
    print(f"A general SQLite error occurred: {e}")

finally:
    # This block always runs, ensuring resources are freed
    if "conn" in locals():
        cursor.close()
        conn.close()
        print(
            "Database connection closed cleanly."
        )
