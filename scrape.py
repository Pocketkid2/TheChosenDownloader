#!/usr/bin/env python3
import urllib.error
import argparse
import requests
import sqlite3
import m3u8
import time
import re
import os

# Start the timer
start_time = time.time()

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--viewer_token', type=str, help='Optional viewer token', default=None)
args = parser.parse_args()

# Database file path
db_path = 'chosen_links.db'

# Check if the database exists and delete it
if os.path.exists(db_path):
    os.remove(db_path)

# Connect to the SQLite database (this will create a new database if it doesn't exist)
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Create table
c.execute('''
    CREATE TABLE IF NOT EXISTS links (
        url text PRIMARY KEY,
        season integer NOT NULL,
        episode integer NOT NULL,
        duration integer NOT NULL,
        title text NOT NULL,
        type text NOT NULL,
        language text,
        resolution text,
        bandwidth integer,
        average_bandwidth integer
    )
''')

def parse_m3u8(url, season, episode, duration, title):
    print("Loading URL " + url + " for season " + str(season) + " episode " + str(episode) + "...")
    try:
        m3u8_obj = m3u8.load(url)
    except urllib.error.HTTPError as e:
        if e.code == 500 and args.viewer_token:
            # Retry with viewer_token if available
            tokenized_url = f"{url}?viewerToken={args.viewer_token}"
            print(f"Retrying with viewer token: {tokenized_url}")
            try:
                m3u8_obj = m3u8.load(tokenized_url)
            except urllib.error.HTTPError as e_retry:
                print(f"Failed to load URL {tokenized_url}: HTTP Error {e_retry.code} {e_retry.reason}")
                return  # Early return to skip processing this URL
        else:
            print(f"Failed to load URL {url}: HTTP Error {e.code} {e.reason}")
            return  # Early return to skip processing this URL

    # Parse media URLs
    for media in m3u8_obj.media:
        c.execute("INSERT OR IGNORE INTO links VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
            media.uri,
            season,
            episode,
            duration,
            title,
            media.type.lower(),
            media.language,
            None,
            None,
            None
        ))

    # Parse playlists
    for playlist in m3u8_obj.playlists:
        c.execute("INSERT OR IGNORE INTO links VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
            playlist.uri,
            season,
            episode,
            duration,
            title,
            'video',
            None,
            str(playlist.stream_info.resolution[1]) + 'p',
            playlist.stream_info.bandwidth,
            playlist.stream_info.average_bandwidth
        ))

query = """
query Videos($ChannelID: ID!, $OrderByField: VideoOrderField!, $OrderByDirection: OrderDirection!) {
  videos(
    ChannelID: $ChannelID
    OrderBy: {field: $OrderByField, direction: $OrderByDirection}
  ) {
    edges {
      node {
        ... on Video {
          id
          title
          description
          duration
          url
          tags {
            edges {
              node {
                  id
                  value
              }
            }
          }
        }
      }
    }
  }
}
"""

response = requests.post(url='https://api.frontrow.cc/graphql',json={"query": query, "operationName": "Videos", "variables": {
  "ChannelID": "12884901895",
  "OrderByField": "CREATED_AT",
  "OrderByDirection": "ASC"
}})
videos = response.json()['data']['videos']['edges']

def filter_video_for_full_episodes(video):
    tags = video['node']['tags']['edges']
    return any(map(lambda tag: tag['node']['value'] == 'Full Episode', tags))

full_episodes = sorted(filter(filter_video_for_full_episodes, videos), key=lambda video: video['node']['title'])

# Initialize the counter for independent videos
independent_video_episode = 1

for i, video in enumerate(full_episodes):
  #print(f"GraphQL response: ID({video['node']['id']}) TITLE({video['node']['title']}) URL({video['node']['url']}) OBJ({video})")
  url = video['node']['url'] or f"https://api.frontrow.cc/channels/12884901895/VIDEO/{video['node']['id']}/hls.m3u8"
  match = re.search(r'Season ([0-9]+) Episode ([0-9]+)', video['node']['title'])
  if match is not None:
    season, episode = map(int, match.groups())
    title = re.sub(r'Season ([0-9]+) Episode ([0-9]+): ', '', video['node']['title'])
  else:
    # If the video is independent, assign it the next episode number
    season, episode = 0, independent_video_episode
    title = video['node']['title']
    # Increment the counter for the next independent video
    independent_video_episode += 1
  parse_m3u8(url, season, episode, video['node']['duration'], title)

# Commit the changes and close the connection
conn.commit()
conn.close()

# End the timer and print the total runtime
end_time = time.time()
print(f"Execution time: {round(end_time - start_time, 3)} seconds")