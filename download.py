import sqlite3
from prettytable import from_db_cursor

# Connect to the SQLite database
conn = sqlite3.connect('chosen_links.db')

# Create a cursor object
cur = conn.cursor()

# Execute a SELECT query
cur.execute("SELECT * FROM links")

# Create a PrettyTable from a db cursor and print
pt = from_db_cursor(cur)
print(pt)

# Close the connection
conn.close()