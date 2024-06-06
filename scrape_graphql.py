#!/usr/bin/env python3
import requests # pip3 install requests
import re

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
    # check if tags include a node with value 'Full Episode'
    return any(map(lambda tag: tag['node']['value'] == 'Full Episode', tags)) # and re.search(r'^S[0-9]+ E[0-9]+: ', video['node']['title'])
full_episodes = sorted(filter(filter_video_for_full_episodes, videos), key=lambda video: video['node']['title'])

# use the url from the video node if it exists, otherwise compute it by interpolating the video id into the appropriate url pattern
hls_urls = [video['node']['url'] or f'https://api.frontrow.cc/channels/12884901895/VIDEO/{video['node']['id']}/hls.m3u8' for video in full_episodes]

for i, video in enumerate(full_episodes):
    print(hls_urls[i], video['node']['title'], video['node']['description'], sep='\t')
