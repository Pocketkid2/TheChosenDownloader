import sqlite3
from prettytable import from_db_cursor
import argparse
import os
import subprocess

# Create an argument parser
parser = argparse.ArgumentParser(description='Filter rows by season, episode, language, and resolution.')
parser.add_argument('--season', type=int, help='Season number to filter by')
parser.add_argument('--episode', type=int, help='Episode number to filter by')
parser.add_argument('--audio_language', type=str, help='Audio language to filter by', required=True)
parser.add_argument('--subtitle_language', type=str, help='Subtitle language to filter by', required=True)
parser.add_argument('--video_quality', type=str, help='Video quality to filter by', required=True)

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
        video.url AS video_url, 
        audio.url AS audio_url, 
        subtitles.url AS subtitles_url
    FROM 
        (SELECT season, episode, title, url FROM links WHERE type = 'video' AND {quality_condition}) AS video
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

# Fetch all rows
rows = cur.fetchall()

# Iterate over each row
for row in rows:
    season, episode, title, video_url, audio_url, subtitles_url = row

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
    if video_url is not None:
        ffmpeg_command.extend(["-map", "0"])
    if audio_url is not None:
        ffmpeg_command.extend(["-map", "1"])

    # Add the codec arguments to convert the subtitles format to mov_text
    if subtitles_url is not None:
        ffmpeg_command.extend(["-scodec", "mov_text", "-map", "2"])

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

# Close the connection
conn.close()