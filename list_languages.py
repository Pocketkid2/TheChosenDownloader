import argparse
import sqlite3
import langcodes

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Filter by season and episode.')
parser.add_argument('--season', type=int, help='Season number')
parser.add_argument('--episode', type=int, help='Episode number')
args = parser.parse_args()

# Connect to the SQLite database
conn = sqlite3.connect('chosen_links.db')

# Create a cursor object
cur = conn.cursor()

# Execute a SQL query to fetch all distinct audio language values
query = "SELECT DISTINCT language FROM links where type = 'audio'"
if args.season is not None:
    query += f" AND season = {args.season}"
if args.episode is not None:
    query += f" AND episode = {args.episode}"
cur.execute(query)

# Fetch all distinct audio language values and sort them by language code
audio_languages = sorted(cur.fetchall(), key=lambda x: x[0])

# Execute a SQL query to fetch all distinct subtitle language values
query = "SELECT DISTINCT language FROM links where type = 'subtitles'"
if args.season is not None:
    query += f" AND season = {args.season}"
if args.episode is not None:
    query += f" AND episode = {args.episode}"
cur.execute(query)

# Fetch all distinct subtitle language values and sort them by language code
subtitle_languages = sorted(cur.fetchall(), key=lambda x: x[0])

# Close the connection
conn.close()

# Print out all distinct audio language values and their count
print(f"\nAudio Languages (Count: {len(audio_languages)}):\n{'-'*40}")
for language in audio_languages:
    lang_code = language[0]
    lang_obj = langcodes.get(lang_code)
    if lang_obj:
        print(f"{lang_obj.display_name().ljust(30)} ({lang_code})")
    else:
        print(lang_code)

# Print out all distinct subtitle language values and their count
print(f"\nSubtitle Languages (Count: {len(subtitle_languages)}):\n{'-'*40}")
for language in subtitle_languages:
    lang_code = language[0]
    lang_obj = langcodes.get(lang_code)
    if lang_obj:
        print(f"{lang_obj.display_name().ljust(30)} ({lang_code})")
    else:
        print(lang_code)