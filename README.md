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
- [`download_stage1.py`](#download_stage1py)
    - [How it works](#how-it-works-1)
    - [Command Line Arguments](#command-line-arguments)
- [`download_stage2.py`](#download_stage2py)
    - [How it works](#how-it-works-2)
    - [Command Line Arguments](#command-line-arguments-1)
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

## `download_stage1.py`

This Python script is used to query the SQLite database `chosen_links.db` and generate a results table based on the provided command line arguments. It's important to note that this script does not download any content; it only helps the user understand their query by presenting the results in a table format.

### How it works

The script starts by parsing command line arguments for season number, episode number, audio language, subtitle language, and video quality. These arguments are used to filter the results.

It then connects to the SQLite database `chosen_links.db` and constructs a SQL query based on the provided arguments. The query selects video, audio, and subtitle URLs from the `links` table, joining on season and episode number.

The script then executes the query and prints the results in a table format using the `prettytable` library.

Finally, it closes the connection to the database.

### Command Line Arguments

- `--season`: An integer representing the season number to filter by.
- `--episode`: An integer representing the episode number to filter by.
- `--audio_language`: A string representing the audio language code to filter by. This argument is required.
- `--subtitle_language`: A string representing the subtitle language code to filter by. This argument is required.
- `--video_quality`: A string representing the video quality to filter by. This argument is required. It can be 'min', 'max', or a custom resolution (e.g., '720p').

The `--season` and `--episode` arguments are optional. If they are not provided, the script will return results for all seasons and episodes.

The `--audio_language`, `--subtitle_language`, and `--video_quality` arguments are required. The script will return results that match the provided audio language, subtitle language, and video quality. See `list_languages.py` script for details on finding available language codes.

The results are sorted by season and episode number.

## `download_stage2.py`

This Python script is an extension of `download_stage1.py`. It not only queries the SQLite database `chosen_links.db` and generates a results table based on the provided command line arguments, but also downloads the streams as temporary files, merges them, and labels them accordingly.

### How it works

After parsing the command line arguments and executing the SQL query (as in `download_stage1.py`), this script iterates over each row of the results. For each row, it:

1. Creates a directory for the season (if it doesn't already exist).
2. Prepares the output file names for the video, audio, and subtitles.
3. Downloads the video, audio, and subtitles using `ffmpeg`.
4. Merges the downloaded files into a single MP4 file, also using `ffmpeg`. The output file is named according to the season, episode, and title.
5. Deletes the temporary files.

The script then closes the connection to the database and prints the total execution time.

### Command Line Arguments

The command line arguments are the same as in `download_stage1.py`:

- `--season`: An integer representing the season number to filter by.
- `--episode`: An integer representing the episode number to filter by.
- `--audio_language`: A string representing the audio language to filter by. This argument is required.
- `--subtitle_language`: A string representing the subtitle language to filter by. This argument is required.
- `--video_quality`: A string representing the video quality to filter by. This argument is required. It can be 'min', 'max', or a custom resolution (e.g., '720p').

The `--season` and `--episode` arguments are optional. If they are not provided, the script will return results for all seasons and episodes.

The `--audio_language`, `--subtitle_language`, and `--video_quality` arguments are required. The script will return results that match the provided audio language, subtitle language, and video quality. See `list_languages.py` script for details on finding available language codes.

The results are sorted by season and episode number.

## Examples

Here are some examples of how to use the scripts:

1. To scrape the video data and store it in a SQLite database, simply run the `scrape.py` script:

    ```bash
    python3 scrape.py
    ```

2. To query the database and generate a results table, run the `download_stage1.py` script with the desired command line arguments. For example, to get the download link table for Season 4 with English audio, English subtitles, and maximum video quality:

    ```bash
    python3 download_stage1.py --season 4 --audio_language en --subtitle_language en --video_quality max
    ```

3. To download the streams, merge them, and label them, run the `download_stage2.py` script with the same command line arguments as `download_stage1.py`. For example:

    ```bash
    python3 download_stage2.py --season 4 --audio_language en --subtitle_language en --video_quality max
    ```