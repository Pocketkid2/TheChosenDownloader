import sqlite3
from prettytable import from_db_cursor
import argparse
import os
import subprocess
import time
import locale

# Start the timer
start_time = time.time()

def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f}{unit}"

# Get the system's default language
try:
    default_language = locale.getdefaultlocale()[0]
    if default_language is not None:
        default_language = default_language.split('_')[0]  # e.g., 'en' for English
    else:
        default_language = 'en'  # Default to English if the system's default locale cannot be determined
except ValueError:
    default_language = 'en'  # Default to English if an error occurs

# Create an argument parser
parser = argparse.ArgumentParser(description='Filter rows by season, episode, language, and resolution.')
parser.add_argument('-s', '--season', type=int, help='Season number to filter by')
parser.add_argument('-e', '--episode', type=int, help='Episode number to filter by')
parser.add_argument('-al', '--audio_language', type=str, default=default_language, help='Audio language to filter by')
parser.add_argument('-sl', '--subtitle_language', type=str, default=default_language, help='Subtitle language to filter by')
parser.add_argument('-vq', '--video_quality', type=str, default='max', help='Video quality to filter by')
parser.add_argument('-n', '--dry-run', action='store_true', help='Print the results without downloading the files')


# Parse the arguments
args = parser.parse_args()

# Connect to the SQLite database
conn = sqlite3.connect('chosen_links.db')

# Create a cursor object
cur = conn.cursor()

# Base query
query = """
    SELECT 
        video.season, 
        video.episode, 
        video.title,
        video.duration,
        video.bandwidth,
        video.url AS video_url, 
        audio.url AS audio_url, 
        subtitles.url AS subtitles_url
    FROM 
        (SELECT season, episode, duration, bandwidth, title, url FROM links WHERE type = 'video' AND {quality_condition}) AS video
    LEFT JOIN 
        (SELECT season, episode, url FROM links WHERE type = 'audio' AND language = ?) AS audio
    ON 
        video.season = audio.season AND video.episode = audio.episode
    LEFT JOIN 
        (SELECT season, episode, url FROM links WHERE type = 'subtitles' AND language = ?) AS subtitles
    ON 
        video.season = subtitles.season AND video.episode = subtitles.episode
"""

# Determine the quality condition based on the video quality argument
if args.video_quality in ['min', 'max']:
    quality_condition = f"(season, episode, average_bandwidth) IN (SELECT season, episode, {args.video_quality.upper()}(average_bandwidth) FROM links WHERE type = 'video' GROUP BY season, episode)"
else:  # custom resolution
    quality_condition = f"resolution = '{args.video_quality}'"

# Insert the quality condition into the query
query = query.format(quality_condition=quality_condition)

# Add filters to the query based on the command line arguments
conditions = []
if args.season is not None:
    conditions.append(f"video.season = {args.season}")
if args.episode is not None:
    conditions.append(f"video.episode = {args.episode}")

if conditions:
    query += " WHERE " + " AND ".join(conditions)

# Add ORDER BY clause to sort by season and episode
query += " ORDER BY video.season, video.episode"

# Execute the query
cur.execute(query, (args.audio_language, args.subtitle_language))

rows = cur.fetchall()

# If dry-run is enabled, print the results and exit
if args.dry_run:
    total_max_file_size = 0
    for row in rows:
        season, episode, title, duration, bandwidth, video_url, audio_url, subtitles_url = row
        max_file_size = duration * bandwidth / 20
        total_max_file_size += max_file_size
    cur.execute(query, (args.audio_language, args.subtitle_language))
    table = from_db_cursor(cur)
    print(table)
    print(f"For this download you will need no more than {human_readable_size(total_max_file_size)} storage space")
    exit(0)  # Exit the script

# Check if any rows were returned
if not rows:
    print("Warning: Your query returned zero results. Please check your season number, episode number, or resolution.")
    exit(1)  # Exit the script

# Iterate over each row
for row in rows:
    season, episode, title, duration, bandwidth, video_url, audio_url, subtitles_url = row

    # Create a directory for the season if it doesn't exist
    if args.season is None and season != 0:
        os.makedirs(f"Season {season}", exist_ok=True)

    # Prepare the output file names
    output_video = "output_video.mp4"
    output_audio = "output_audio.aac"
    output_subs = "output_subs.vtt"

    # Download the video, audio, and subtitles
    if video_url is not None:
        subprocess.run(["ffmpeg", "-i", video_url, output_video])
    if audio_url is not None:
        subprocess.run(["ffmpeg", "-i", audio_url, output_audio])
    if subtitles_url is not None:
        subprocess.run(["ffmpeg", "-i", subtitles_url, output_subs])

    # Prepare the ffmpeg command to merge the files
    ffmpeg_command = ["ffmpeg"]

    # Add the input files
    if video_url is not None:
        ffmpeg_command.extend(["-i", output_video])
    if audio_url is not None:
        ffmpeg_command.extend(["-i", output_audio])
    if subtitles_url is not None:
        ffmpeg_command.extend(["-i", output_subs])

    # Add the map arguments to copy all video and audio tracks
    if video_url is not None or audio_url is not None:
        ffmpeg_command.extend(["-c:v", "copy", "-c:a", "copy"])

    # Add the codec arguments to convert the subtitles format to mov_text
    if subtitles_url is not None:
        ffmpeg_command.extend(["-c:s", "mov_text"])

    # Prepare the output file name
    if season == 0:
        output_file = f"{title}.mp4"
    else:
        output_file = f"[S{season} E{episode}] {title}.mp4"

    # If the user did not specify a season, put the output file in the season directory
    if args.season is None and season != 0:
        output_file = os.path.join(f"Season {season}", output_file)

    # Add the output file to the ffmpeg command
    ffmpeg_command.append(output_file)

    # Run the ffmpeg command to merge the files
    subprocess.run(ffmpeg_command)

    # Delete the temporary files
    if video_url is not None:
        os.remove(output_video)
    if audio_url is not None:
        os.remove(output_audio)
    if subtitles_url is not None:
        os.remove(output_subs)

# Close the connection
conn.close()

# Print the time taken to execute the script
end_time = time.time()
print(f"Execution time: {end_time - start_time:.2f} seconds")