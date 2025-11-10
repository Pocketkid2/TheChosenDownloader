# TheChosenDownloader

This project contains the tools to download all episodes of [The Chosen (TV show)](https://en.wikipedia.org/wiki/The_Chosen_(TV_series)) as mkv's in any available language and video quality.

Version 2.0 of this project simplifies the process by having just one script to do all the work.

## Usage Instructions

1. **Install dependencies**
   - Make sure you have Python 3.7+ installed.
   - Install required Python packages:
     ```bash
     pip install -r requirements.txt
     ```
   - You also need `yt-dlp` and `ffmpeg` installed and available in your PATH.

2. **Prepare your CSV file**
   - The default input file is `urls.csv`. It should contain columns: `url`, `season`, `episode`, `title`.

3. **Run the script**
   - Basic usage:
     ```bash
     python3 download.py
     ```
   - For a dry run (shows what would be downloaded, checks URLs):
     ```bash
     python3 download.py --dry-run
     ```
   - To specify options (see `python3 download.py --help` for all options):
     ```bash
     python3 download.py -s 1,2 -a en --subtitle-language en -v 1080p -f mkv -o downloads/
     ```

4. **Viewer Token**
   - If you encounter a 403 Forbidden error, the script will create a file called `viewer-token.txt` in the project directory.
   - You must obtain your viewer token and paste it into this file.
   - The script will automatically retry URLs using your token.

## How to Obtain Your Viewer Token

> **Note:** This step must be done manually until the login protocol for The Chosen's watch site is reverse-engineered.

Follow these steps to obtain your viewer token:

1. **Create an account** on [watch.thechosen.tv](https://watch.thechosen.tv) and log in.
2. **Navigate to any episode's watch page** (season 5 is recommended).
3. **Open your browser's developer tools**:
   - On Chrome: Right-click the page and select **Inspect**.
4. **Go to the Network tab** in developer tools.
   - Reload the page to capture all network requests.
5. **Look for a request** to `hls.m3u8` or `stream.m3u8`.
   - The request URL will look like: `hls.m3u8?viewerToken=XYZ`
6. **Copy the viewer token**:
   - The value after `viewerToken=` (a long string of characters).
7. **Paste the token** into the `viewer-token.txt` file in your project directory.

Once you have added your token, rerun the script. The script will use your token to access protected streams.