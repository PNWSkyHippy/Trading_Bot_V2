import pandas as pd
import sqlite3

with sqlite3.connect("company.db") as conn:
    # Read directly from SQL into a Pandas DataFrame
    df = pd.read_sql_query(
        "SELECT * FROM employees WHERE salary > 75000",
        conn,
    )

# Now you can instantly use Pandas features on your data
print(df.head())  # Preview the first few rows
print(df.describe())  # Get instant statistics (mean, max, min salary)

# Convert a DataFrame instantly into an SQLite table
# 'fail', 'replace', or 'append' if the table already exists
df.to_sql(
    "new_employees_table",
    conn,
    if_exists="append",
    index=False,
)
