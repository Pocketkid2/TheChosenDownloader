# TheChosenDownloader

### Getting stream links

The python script `scrape_graphql.py` can be run to create a SQLite DB that contains every currently known stream resource. It does this by querying the GraphQL API to find all official videos, then querying the CDN to get the stream indexes for each video. Python requirements: `sqlite3`, `m3u8`, and `requests`
