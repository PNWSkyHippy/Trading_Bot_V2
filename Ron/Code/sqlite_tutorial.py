import sqlite3

# Connect to a database file (or use ':memory:' for a temporary database)
conn = sqlite3.connect("company.db")

# Create a cursor object
cursor = conn.cursor()

# Insert a single record
cursor.execute(
    "INSERT INTO employees (name, role, salary) VALUES (?, ?, ?)",
    ("Alice", "Developer", 85000.00),
)

# Insert multiple records at once
new_employees = [
    ("Bob", "Designer", 70000.00),
    ("Charlie", "Manager", 95000.00),
]
cursor.executemany(
    "INSERT INTO employees (name, role, salary) VALUES (?, ?, ?)",
    new_employees,
)

conn.commit()  # Always commit after making modifications

# Query all employees
cursor.execute("SELECT * FROM employees")

# Fetch all results into a list of tuples
rows = cursor.fetchall()

for row in rows:
    print(
        f"ID: {row[0]} | Name: {row[1]} | Role: {row[2]} | Salary: ${row[3]:,.2f}"
    )


# Remove Charlie from the database
cursor.execute(
    "DELETE FROM employees WHERE name = ?",
    ("Charlie",),
)
conn.commit()

cursor.close()
conn.close()


# import sqlite3

# The connection automatically commits inside this block
with sqlite3.connect("company.db") as conn:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM employees WHERE salary > ?",
        (80000,),
    )
    print(cursor.fetchall())
