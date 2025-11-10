def log_print(*args, **kwargs):
    message = ' '.join(str(arg) for arg in args)
    print(message, **kwargs)
    try:
        with open('output.log', 'a', encoding='utf-8') as f:
            f.write(message + '\n')
    except Exception:
        pass
#!/usr/bin/env python3
"""
Script to read URLs from CSV, parse m3u8 files, and download/combine
video, audio, and subtitle streams into MP4 or MKV files.
"""

import argparse
import csv
import locale
import os
import shutil
import subprocess
import sys
import tempfile
import requests
import m3u8
from pathlib import Path
from urllib.parse import urljoin, urlparse


def parse_m3u8(url):
    """Download and parse an m3u8 file."""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 403:
            # Try to get viewer token
            token_path = 'viewer-token.txt'
            if not os.path.exists(token_path):
                log_print(f"  Error parsing m3u8: HTTP 403 Forbidden for {url}")
                log_print(f"  viewer-token.txt not found. Creating viewer-token.txt...")
                try:
                    with open(token_path, 'w', encoding='utf-8') as tf:
                        tf.write('')
                    log_print(f"  viewer-token.txt created. Please populate this file with your viewer token and run the script again.")
                except Exception as e:
                    log_print(f"  Could not create viewer-token.txt: {e}")
                return None, '403_no_token'
            with open(token_path, 'r', encoding='utf-8') as tf:
                viewer_token = tf.read().strip()
            # Append viewerToken to URL
            sep = '&' if '?' in url else '?'
            url_with_token = f"{url}{sep}viewerToken={viewer_token}"
            log_print(f"  403 Forbidden. Retrying with viewerToken from viewer-token.txt...")
            response = requests.get(url_with_token, timeout=10)
            if response.status_code == 403:
                log_print(f"  Error: viewer token is incorrect for {url_with_token}")
                return None, '403_bad_token'
            elif response.status_code != 200:
                log_print(f"  Error parsing m3u8: HTTP {response.status_code} for {url_with_token}")
                return None, f"http_{response.status_code}"
            # Success, parse
            playlist = m3u8.loads(response.text, uri=url_with_token)
            return playlist, None
        response.raise_for_status()
        # Parse the m3u8 content
        playlist = m3u8.loads(response.text, uri=url)
        return playlist, None
    except Exception as e:
        log_print(f"  Error parsing m3u8: {e}")
        return None, str(e)


def get_default_language():
    """Get the default language code from the system locale."""
    try:
        lang, _ = locale.getlocale()
        if lang and lang != 'C':
            # Extract language code (e.g., 'en_US' -> 'en')
            # Skip 'C' locale (POSIX) which doesn't represent a real language
            return lang.split('_')[0]
    except:
        pass
    return 'en'  # Default to English if locale detection fails or locale is 'C'


def parse_resolution(resolution_str):
    """Parse resolution string like '720p' or '1080p' to get height value."""
    if not resolution_str:
        return None
    resolution_str = resolution_str.lower().strip()
    if resolution_str.endswith('p'):
        try:
            return int(resolution_str[:-1])
        except ValueError:
            return None
    return None


def select_video_stream(playlist, target_resolution, base_url):
    """Select the appropriate video stream based on resolution preference.
    Returns (variant, error_message). If error_message is not None, selection failed.
    """
    if not playlist:
        return None, "No playlist available"
    
    if not playlist.is_variant:
        # Single stream playlist - return it if no specific resolution requested
        if target_resolution:
            return None, f"No variant streams available (single stream playlist), cannot match resolution {target_resolution}"
        return playlist, None
    
    if target_resolution:
        target_height = parse_resolution(target_resolution)
        if not target_height:
            return None, f"Invalid resolution format: {target_resolution}. Expected format like '720p' or '1080p'"
        
        # Find stream matching the target resolution
        for variant in playlist.playlists:
            if variant.stream_info.resolution:
                height = variant.stream_info.resolution[1]
                if height == target_height:
                    return variant, None
        
        # Resolution not found - list available resolutions
        available = []
        for variant in playlist.playlists:
            if variant.stream_info.resolution:
                height = variant.stream_info.resolution[1]
                available.append(f"{height}p")
        available_str = ", ".join(available) if available else "none"
        return None, f"No video stream found with resolution {target_resolution}. Available resolutions: {available_str}"
    
    # Default: return the stream with the highest resolution
    best_variant = None
    max_resolution = 0
    
    for variant in playlist.playlists:
        if variant.stream_info.resolution:
            height = variant.stream_info.resolution[1]
            if height > max_resolution:
                max_resolution = height
                best_variant = variant
    
    if not best_variant and playlist.playlists:
        return playlist.playlists[0], None
    
    if best_variant:
        return best_variant, None
    return None, "No video streams available"


def select_audio_track(playlist, target_language, base_url):
    """Select the appropriate audio track based on language preference.
    Returns (audio_track, error_message). If error_message is not None, selection failed.
    """
    if not playlist or not playlist.media:
        return None, "No media groups available in playlist"
    
    audio_media = [m for m in playlist.media if m.type == 'AUDIO']
    if not audio_media:
        return None, "No audio tracks available"
    
    if target_language:
        # Try to find exact language match
        for audio in audio_media:
            if audio.language and audio.language.lower() == target_language.lower():
                return audio, None
        # Try to find partial match (e.g., 'en' matches 'en-US')
        for audio in audio_media:
            if audio.language and audio.language.lower().startswith(target_language.lower()):
                return audio, None
        
        # Language not found - list available languages
        available = []
        for audio in audio_media:
            if audio.language:
                available.append(audio.language)
        available_str = ", ".join(set(available)) if available else "none"
        return None, f"No audio track found with language '{target_language}'. Available languages: {available_str}"
    
    # Default: return first audio track
    return audio_media[0], None


def select_subtitle_track(playlist, target_language, base_url):
    """Select the appropriate subtitle track based on language preference.
    Returns (subtitle_track, error_message). If error_message is not None, selection failed.
    """
    if not playlist or not playlist.media:
        return None, "No media groups available in playlist"
    
    subtitle_media = [m for m in playlist.media if m.type == 'SUBTITLES']
    if not subtitle_media:
        return None, "No subtitle tracks available"
    
    if target_language:
        # Try to find exact language match
        for subtitle in subtitle_media:
            if subtitle.language and subtitle.language.lower() == target_language.lower():
                return subtitle, None
        # Try to find partial match
        for subtitle in subtitle_media:
            if subtitle.language and subtitle.language.lower().startswith(target_language.lower()):
                return subtitle, None
        
        # Language not found - list available languages
        available = []
        for subtitle in subtitle_media:
            if subtitle.language:
                available.append(subtitle.language)
        available_str = ", ".join(set(available)) if available else "none"
        return None, f"No subtitle track found with language '{target_language}'. Available languages: {available_str}"
    
    # Default: return first subtitle track
    if subtitle_media:
        return subtitle_media[0], None
    return None, "No subtitle tracks available"


def print_selected_tracks(selected_video, selected_audio, selected_subtitle, base_url, log_func=print):
    """Print only the selected video, audio, and subtitle tracks."""
    log_func("\n  Selected Tracks:")

    # Print selected video stream
    log_func("  Video Stream:")
    if selected_video:
        if hasattr(selected_video, 'stream_info') and selected_video.stream_info:
            # Variant stream
            resolution = f"{selected_video.stream_info.resolution[0]}x{selected_video.stream_info.resolution[1]}" if selected_video.stream_info.resolution else "Unknown"
            bandwidth = f"{selected_video.stream_info.bandwidth // 1000} kbps" if selected_video.stream_info.bandwidth else "Unknown"
            codecs = selected_video.stream_info.codecs if selected_video.stream_info.codecs else "Unknown"
            uri = urljoin(base_url, selected_video.uri)
            log_func(f"    Resolution: {resolution}")
            log_func(f"    Bandwidth: {bandwidth}")
            log_func(f"    Codecs: {codecs}")
            log_func(f"    URI: {uri}")
        elif hasattr(selected_video, 'segments'):
            # Media playlist
            log_func(f"    Type: Single video stream (media playlist)")
            log_func(f"    Segments: {len(selected_video.segments)}")
    else:
        log_func("    None")

    # Print selected audio track
    log_func("\n  Audio Track:")
    if selected_audio:
        name = selected_audio.name if selected_audio.name else "Unknown"
        language = selected_audio.language if selected_audio.language else "Unknown"
        uri = urljoin(base_url, selected_audio.uri) if selected_audio.uri else "N/A"
        group_id = selected_audio.group_id if selected_audio.group_id else "N/A"
        log_func(f"    Language Name: {name}")
        log_func(f"    Language Code: {language}")
        if selected_audio.uri:
            log_func(f"    URI: {uri}")
    else:
        log_func("    None")

    # Print selected subtitle track
    log_func("\n  Subtitle Track:")
    if selected_subtitle:
        name = selected_subtitle.name if selected_subtitle.name else "Unknown"
        language = selected_subtitle.language if selected_subtitle.language else "Unknown"
        uri = urljoin(base_url, selected_subtitle.uri) if selected_subtitle.uri else "N/A"
        group_id = selected_subtitle.group_id if selected_subtitle.group_id else "N/A"
        log_func(f"    Language Name: {name}")
        log_func(f"    Language Code: {language}")
        if selected_subtitle.uri:
            log_func(f"    URI: {uri}")
    else:
        log_func("    None")


def sanitize_filename(filename):
    """Sanitize a string to be used as a filename."""
    # Remove or replace invalid filename characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    return filename


def download_segments(playlist_url, base_url, temp_dir, stream_type="video"):
    """Download all segments from an m3u8 playlist and return the path to the concatenated file."""
    try:
        # Use yt-dlp to download the m3u8 stream to a local file
        os.makedirs(temp_dir, exist_ok=True)
        output_file = os.path.join(temp_dir, f"{stream_type}.ts")
        cmd = [
            "yt-dlp",
            "-o", output_file,
            playlist_url
        ]
        print(f"    Downloading {stream_type} stream with yt-dlp...")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            return None, f"yt-dlp error: process exited with code {result.returncode}"
        if not os.path.exists(output_file):
            return None, f"yt-dlp did not produce output file for {stream_type}"
        return output_file, None
    except Exception as e:
        return None, f"Error downloading {stream_type} with yt-dlp: {e}"


def download_subtitle(subtitle_uri, base_url, temp_dir):
    """Download subtitle file and return the path."""
    try:
        subtitle_url = urljoin(base_url, subtitle_uri)
        response = requests.get(subtitle_url, timeout=10)
        response.raise_for_status()
        content = response.text
        # Check if it's an m3u8 playlist
        if content.strip().startswith('#EXTM3U'):
            playlist = m3u8.loads(content, uri=subtitle_url)
            if not playlist.segments:
                return None, "No subtitle segments found in m3u8 playlist"
            segment_files = []
            for i, segment in enumerate(playlist.segments):
                seg_url = urljoin(subtitle_url, segment.uri)
                seg_response = requests.get(seg_url, timeout=10)
                seg_response.raise_for_status()
                seg_file = os.path.join(temp_dir, f"subtitle_seg_{i:05d}.vtt")
                with open(seg_file, 'wb') as f:
                    f.write(seg_response.content)
                segment_files.append(seg_file)
            # Concatenate segments into one subtitle file
            subtitle_file = os.path.join(temp_dir, "subtitle.vtt")
            with open(subtitle_file, 'wb') as outfile:
                for seg_file in segment_files:
                    with open(seg_file, 'rb') as infile:
                        outfile.write(infile.read())
            return subtitle_file, None
        else:
            # Direct subtitle file
            subtitle_file = os.path.join(temp_dir, "subtitle.vtt")
            if subtitle_url.endswith('.srt'):
                subtitle_file = os.path.join(temp_dir, "subtitle.srt")
            with open(subtitle_file, 'wb') as f:
                f.write(response.content.encode('utf-8') if isinstance(response.content, str) else response.content)
            return subtitle_file, None
    except Exception as e:
        return None, f"Error downloading subtitle: {e}"


def combine_with_ffmpeg(video_file, audio_file, subtitle_file, output_file, output_format='mp4'):
    """Use ffmpeg to combine video, audio, and subtitle into final output file."""
    try:
        # Check if ffmpeg is available
        if not shutil.which('ffmpeg'):
            return False, "ffmpeg not found. Please install ffmpeg to combine streams."
        
        if not video_file or not os.path.exists(video_file):
            return False, "Video file not found"
        
        # Build ffmpeg command
        cmd = ['ffmpeg', '-y', '-loglevel', 'error']
        
        # Track input indices
        input_idx = 0
        video_idx = None
        audio_idx = None
        subtitle_idx = None
        
        # Add video input
        cmd.extend(['-i', video_file])
        video_idx = input_idx
        input_idx += 1
        
        # Add audio input if separate
        if audio_file and os.path.exists(audio_file):
            cmd.extend(['-i', audio_file])
            audio_idx = input_idx
            input_idx += 1
        
        # Add subtitle input
        if subtitle_file and os.path.exists(subtitle_file):
            cmd.extend(['-i', subtitle_file])
            subtitle_idx = input_idx
            input_idx += 1
        
        # Map streams
        # Map all streams from video (will include video and any embedded audio)
        cmd.extend(['-map', f'{video_idx}'])
        
        # If we have separate audio, override with that
        if audio_idx is not None:
            # Remove the auto-mapped audio and use separate audio instead
            cmd.extend(['-map', '-0:a'])  # Remove auto-mapped audio
            cmd.extend(['-map', f'{audio_idx}:a:0'])  # Use separate audio
        
        # Map subtitle if available
        if subtitle_idx is not None:
            cmd.extend(['-map', f'{subtitle_idx}:s:0'])  # Subtitle from subtitle input
        
        # Codec settings
        cmd.extend(['-c:v', 'copy'])  # Copy video codec
        cmd.extend(['-c:a', 'copy'])  # Copy audio codec
        
        # Subtitle codec based on format
        if subtitle_idx is not None:
            if output_format == 'mp4':
                cmd.extend(['-c:s', 'mov_text'])  # MP4 uses mov_text for subtitles
            else:  # mkv
                cmd.extend(['-c:s', 'copy'])  # MKV can copy subtitle codec
        
        # Output file
        cmd.append(output_file)
        
        # Run ffmpeg
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, f"ffmpeg error: {result.stderr}"
        
        return True, None
    
    except Exception as e:
        return False, f"Error running ffmpeg: {e}"


def parse_seasons(season_arg):
    """Parse season argument which can be a single integer or comma-separated list."""
    if not season_arg or not season_arg.strip():
        raise argparse.ArgumentTypeError("Season argument cannot be empty")
    
    try:
        seasons = [int(s.strip()) for s in season_arg.split(',') if s.strip()]
        if not seasons:
            raise argparse.ArgumentTypeError("At least one season number must be provided")
        return set(seasons)
    except ValueError as e:
        raise argparse.ArgumentTypeError("Seasons must be integers or comma-separated integers (e.g., '1,2,3')")


def parse_args():
    """Parse command line arguments."""
    default_language = get_default_language()
    
    parser = argparse.ArgumentParser(
        description='Download and parse m3u8 files from CSV to display available streams',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        default='urls.csv',
        help='Input CSV file name (default: urls.csv)'
    )
    
    parser.add_argument(
        '-s', '--season',
        type=parse_seasons,
        default=None,
        help='Season number(s) as integer or comma-separated list (e.g., "1" or "1,2,3"). Defaults to all seasons.'
    )
    
    parser.add_argument(
        '-a', '--audio-language',
        type=str,
        default=default_language,
        help=f'Audio language code (default: {default_language} from system locale)'
    )
    
    parser.add_argument(
        '--subtitle-language',
        type=str,
        default=default_language,
        help=f'Subtitle language code (default: {default_language} from system locale)'
    )
    
    parser.add_argument(
        '-v', '--video-stream',
        type=str,
        default=None,
        help='Video resolution preference (e.g., "720p", "1080p"). Defaults to highest available resolution.'
    )
    
    parser.add_argument(
        '-f', '--format',
        type=str,
        choices=['mp4', 'mkv'],
        default='mp4',
        help='Output video format (default: mp4)'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='.',
        help='Output directory for downloaded files (default: current directory)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be downloaded and check URL validity, but do not download or merge.'
    )

    return parser.parse_args()


def main():
    """Main function to read CSV and process each URL."""
    args = parse_args()
    csv_file = args.input

    # Overwrite output.log at the start of each run
    try:
        with open('output.log', 'w', encoding='utf-8') as f:
            f.write('')
    except Exception:
        pass

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):  # Start at 2 because row 1 is header
                url = row['url'].strip()
                season = int(row['season'])
                episode = int(row['episode'])
                title = row['title'].strip('"')  # Remove quotes from title

                # Filter by season if specified
                if args.season and season not in args.season:
                    continue

                log_print(f"\n{'='*80}")
                log_print(f"Season {season}, Episode {episode}")
                log_print(f"Title: {title}")
                log_print(f"URL: {url}")
                log_print(f"{'='*80}")

                # Skip example.com URLs
                if 'example.com' in url:
                    log_print("  Skipping example.com URL")
                    continue

                # Parse the m3u8 file
                playlist, m3u8_error = parse_m3u8(url)
                if not playlist:
                    if m3u8_error == '403_no_token':
                        # Already logged, skip to next URL
                        continue
                    elif m3u8_error == '403_bad_token':
                        # Already logged, skip to next URL
                        continue
                    else:
                        log_print(f"Error: Failed to parse m3u8 file for Season {season}, Episode {episode}")
                        if args.dry_run:
                            continue
                        else:
                            sys.exit(1)

                # Extract base URL for resolving relative URIs
                parsed_url = urlparse(url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{'/'.join(parsed_url.path.split('/')[:-1])}/"

                # Select streams based on preferences
                selected_video, video_error = select_video_stream(playlist, args.video_stream, base_url)
                selected_audio, audio_error = select_audio_track(playlist, args.audio_language, base_url)
                selected_subtitle, subtitle_error = select_subtitle_track(playlist, args.subtitle_language, base_url)

                # Print warnings for missing tracks in dry-run mode
                if args.dry_run:
                    if video_error:
                        log_print(f"Warning: {video_error}")
                    if audio_error:
                        log_print(f"Warning: {audio_error}")
                    if subtitle_error:
                        log_print(f"Warning: {subtitle_error}")
                else:
                    if video_error:
                        log_print(f"Error: {video_error}")
                        sys.exit(1)
                    if audio_error:
                        log_print(f"Error: {audio_error}")
                        sys.exit(1)
                    if subtitle_error:
                        log_print(f"Error: {subtitle_error}")
                        sys.exit(1)

                # Print only selected tracks
                print_selected_tracks(selected_video, selected_audio, selected_subtitle, base_url, log_func=log_print)

                # DRY RUN MODE
                if args.dry_run:
                    log_print("\n  DRY RUN: Showing URLs and checking validity...")
                    urls_to_check = []
                    # Video
                    if selected_video and not video_error:
                        if hasattr(selected_video, 'uri'):
                            video_playlist_url = urljoin(base_url, selected_video.uri)
                        elif hasattr(selected_video, 'segments'):
                            video_playlist_url = url
                        else:
                            video_playlist_url = None
                        if video_playlist_url:
                            log_print(f"  Would download video: {video_playlist_url}")
                            urls_to_check.append(video_playlist_url)
                    # Audio
                    if selected_audio and selected_audio.uri and not audio_error:
                        audio_playlist_url = urljoin(base_url, selected_audio.uri)
                        log_print(f"  Would download audio: {audio_playlist_url}")
                        urls_to_check.append(audio_playlist_url)
                    # Subtitle
                    if selected_subtitle and selected_subtitle.uri and not subtitle_error:
                        subtitle_url = urljoin(base_url, selected_subtitle.uri)
                        log_print(f"  Would download subtitle: {subtitle_url}")
                        urls_to_check.append(subtitle_url)
                    # Check all URLs
                    for check_url in urls_to_check:
                        try:
                            resp = requests.head(check_url, timeout=10)
                            if resp.status_code == 200:
                                log_print(f"    ✓ {check_url} is valid (HTTP 200)")
                            else:
                                log_print(f"    ✗ {check_url} returned status {resp.status_code}")
                        except Exception as e:
                            log_print(f"    ✗ {check_url} error: {e}")
                    log_print("  DRY RUN complete. No files downloaded or merged.")
                    continue

                # ...existing code for download and merge...

    except FileNotFoundError:
        log_print(f"Error: Could not find {csv_file}")
        sys.exit(1)
    except Exception as e:
        log_print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

