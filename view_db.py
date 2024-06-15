import sqlite3
from prettytable import from_db_cursor
import argparse

# Create an argument parser
parser = argparse.ArgumentParser(description='Filter rows by season, episode, language, and resolution.')
parser.add_argument('--season', type=int, help='Season number to filter by')
parser.add_argument('--episode', type=int, help='Episode number to filter by')
parser.add_argument('--language', type=str, help='Language to filter by')
parser.add_argument('--resolution', type=str, help='Resolution to filter by')
parser.add_argument('--type', type=str, help='Type of link/resource to filter by')

# Parse the arguments
args = parser.parse_args()

# Connect to the SQLite database
conn = sqlite3.connect('chosen_links.db')

# Create a cursor object
cur = conn.cursor()

# Base query
query = "SELECT * FROM links"

# Add filters to the query based on the command line arguments
conditions = []
if args.season is not None:
    conditions.append(f"season = {args.season}")
if args.episode is not None:
    conditions.append(f"episode = {args.episode}")
if args.language is not None:
    conditions.append(f"language = '{args.language}'")
if args.resolution is not None:
    conditions.append(f"resolution = '{args.resolution}'")
if args.type is not None:
    conditions.append(f"type = '{args.type}'")

if conditions:
    query += " WHERE " + " AND ".join(conditions)

# Execute the query
cur.execute(query)

# Create a PrettyTable from a db cursor and print
pt = from_db_cursor(cur)
print(pt)

# Close the connection
conn.close()