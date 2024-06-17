#!/usr/bin/env python3
import requests
import sqlite3
import m3u8
import time
import re

# Start the timer
start_time = time.time()

# Connect to the SQLite database
conn = sqlite3.connect('chosen_links.db')
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
    m3u8_obj = m3u8.load(url)

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
  url = video['node']['url'] or f"https://api.frontrow.cc/channels/12884901895/VIDEO/{video['node']['id']}/hls.m3u8"
  match = re.search(r'S([0-9]+) E([0-9]+)', video['node']['title'])
  if match is not None:
    season, episode = map(int, match.groups())
    title = re.sub(r'S([0-9]+) E([0-9]+): ', '', video['node']['title'])
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