# TheChosenDownloader

This project contains the tools to download all episodes of [The Chosen (TV show)](https://en.wikipedia.org/wiki/The_Chosen_(TV_series)) as mp4's in any available language and video quality.

This repository contains a Python script designed to scrape video data from The Chosen's GraphQL API, parse the data, and store it in a SQLite database. It also includes scripts to query the database and download the video, audio, and subtitle streams. The scripts are designed to be used in sequence, with each script building on the data generated by the previous one.

## Table of Contents

- [`scrape.py`](#scrapepy)
    - [How it works](#how-it-works)
    - [Output](#output)
- [`view_db.py`](#view_dbpy)
    - [Usage](#usage)
    - [Output](#output-1)
    - [Example Output](#example-output)
- [`list_languages.py`](#list_languagespy)
    - [Usage](#usage-1)
    - [Output](#output-2)
    - [Example Output](#example-output-1)
- [`download.py`](#downloadpy)
    - [Usage](#usage-2)
    - [Examples](#examples)

## `scrape.py`
This script is used to scrape video stream links from The Chosen's GraphQL API, parse the data, and store it in a SQLite database. It's written in Python and requires the additional Python libraries `requests` and `m3u8`.

### How it works
The script starts by creating a SQLite database named `chosen_links.db` and creating a table named `links`. If this file and table already exist, nothing new will be added. NOTE: It is not advisable to run this script again while the file exists, so delete it first before re-running.

It then defines a function `parse_m3u8` that takes a URL, season number, episode number, and title as arguments. This function loads the M3U8 file from the URL and parses it, extracting the media URLs (audio and subtitle tracks) and playlist URLs (video tracks) and inserting them into the `links` table in the database.

The script sends a POST request to the GraphQL API and retrieves a list of all videos available on The Chosen's website. It filters this list to include only full episodes and sorts them by title.

For each video, the script extracts the URL, season number, episode number, and title. If the video is an independent video (i.e., not part of a season), it assigns it a season number of 0 and an episode number that increments with each independent video.

The script then calls the `parse_m3u8` function for each video, passing it the URL, season number, episode number, and title.

Finally, the script commits the changes to the database and closes the connection. It also prints the total execution time.

### Output
The output of this script is a SQLite database named `chosen_links.db` that contains a table named `links`. Each row in the table represents a media or playlist URL from a video. The columns in the table are:

- `url`: The URL of the media or playlist.
- `season`: The season number of the video.
- `episode`: The episode number of the video.
- `title`: The title of the video.
- `type`: The type of the media (e.g., 'video', 'audio', 'subtitles').
- `language`: The language of the media (if applicable).
- `resolution`: The resolution of the video (if applicable).
- `bandwidth`: The bandwidth of the video (if applicable).

## `view_db.py`

This python script simply lists rows in the SQLite database containing the scraped links, with some optional filters. It's essentially a simplified Python wrapper for sqlite3. It helps you understand what's in the database.

### Usage

Run the script from the command line with optional arguments:

```bash
python3 view_db.py --season <season_number> --episode <episode_number> --language <language_code> --resolution <resolution> --type <type>
```

All arguments are optional. If provided, they filter the output:

* `--season`: Filter by season number
* `--episode`: Filter by episode number
* `--language`: Filter by language code
* `--resolution`: Filter by resolution
* `--type`: Filter by type of link/resource

### Output

The script outputs a table of rows from the database that match the specified filters. If no filters are specified, it displays all rows.

### Example Output

```bash
+-----+--------+---------+-------------------------------+-----------+----------+------------+-----------+-------------------+
| url | season | episode |             title             |    type   | language | resolution | bandwidth | average_bandwidth |
+--------------+---------+-------------------------------+-----------+----------+------------+-----------+-------------------+
| ... |   1    |    4    | The Rock On Which It Is Built |   audio   |    en    |    None    |    None   |        None       |
| ... |   1    |    4    | The Rock On Which It Is Built |   video   |   None   |   1080p    |  16970132 |      5056517      |
...
+-----+--------+---------+-------------------------------+-----------+----------+------------+-----------+-------------------+
```

In this example, the script displays rows with season 1, episode 1, language 'en', resolution '1080p', and type 'audio', and season 1, episode 2, language 'es', resolution '720p', and type 'subtitles'.



## `list_languages.py`

This Python script is used to list all available audio and subtitle languages from the SQLite database containing the scraped links. The options vary from season to season, and episode to episode, so you may want to filter by season or episode to make sure you get the correct information.

### Usage 

You can run the script from the command line with optional arguments for the season and episode number:

```bash
python3 list_languages.py --season <season_number> --episode <episode_number>
```

Both `--season` and `--episode` are optional arguments. If you don't provide a season number, the script will list languages for all seasons. Similarly, if you don't provide an episode number, the script will list languages for all episodes.

### Output

The script outputs two lists:

**Audio Languages**: This list contains all distinct audio languages for the specified season and episode. The languages are sorted by their language code. Each line of the list contains the display name of the language and its language code.

**Subtitle Languages**: This list contains all distinct subtitle languages for the specified season and episode. The languages are sorted by their language code. Each line of the list contains the display name of the language and its language code.

The count of languages in each list is also displayed.

### Example Output
In this example, the script found 19 audio languages and 25 subtitle languages. The languages are displayed with their display name and language code. ```
```bash
Audio Languages (Count: 19):
----------------------------------------
English                          (en)
Spanish                          (es)
French                           (fr)
...

Subtitle Languages (Count: 25):
----------------------------------------
English                          (en)
Spanish                          (es)
French                           (fr)
...
```

## `download.py`

This script does the actual download work by querying the SQLite database file for the links you want, downloading the streams, merging them into MP4s, and labelling them. 

### Usage

The script accepts the following command-line arguments:

`-s` or `--season`: This argument filters the media files by the season number. By default, the script downloads videos for all seasons (including "season 0") unless this argument is specified. For example, `-s 2` will only download files from season 2.

`-e` or `--episode`: This argument filters the media files by the episode number. By default, the script downloads videos for all episodes unless this argument is specified. For example, `-e 3` will only download files marked episode 3.

`-al` or `--audio_language`: This argument filters the media files by the audio language. By default, the OS language is used, unless this argument is specified. For example, `-al en` will download English audio.

`-sl` or `--subtitle_language`: This argument filters the media files by the subtitle language. By default, the OS language is used, unless this argument is specified. For example, `-sl es` will download Spanish subtitles.

`-vq` or `--video_quality`: This argument filters the media files by the video quality. This argument defaults to `max` but can be specified as `min` or a custom resolution. For example, `-vq 720p` will download the 720p video streams. Not all videos support all resolutions, so you'll want to test this beforehand with the dry run flag before downloading.

`-n` or `--dry-run`: If this argument is provided, the script will print the results without downloading the files. This is helpful as it allows you to test the arguments you provided, to make sure you will be getting the videos and tracks you want.

### Examples
Here are some examples of how to use the script:

To download all media files with English audio, Spanish subtitles, and maximum video quality:

```bash
python download.py -al en -sl es -vq max
```

To download media files from season 2, episode 3, with French audio, German subtitles, and 720p video quality:

```bash
python download.py -s 2 -e 3 -al fr -sl de -vq 720p
```

To print the results without downloading the files:

```bash
python download.py -al en -sl es -vq max -n
```

Please note that the script uses `ffmpeg` to download and merge the media files, so you need to have `ffmpeg` installed on your system to use this script.