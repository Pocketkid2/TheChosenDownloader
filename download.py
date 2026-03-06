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


def log_print(*args, **kwargs):
    message = ' '.join(str(arg) for arg in args)
    print(message, **kwargs)
    try:
        with open('output.log', 'a', encoding='utf-8') as f:
            f.write(message + '\n')
    except Exception:
        pass


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


def select_video_stream(playlist, target_resolution, base_url, prefer_h265=False):
    """Select the appropriate video stream based on resolution and codec preference.
    Returns (variant, error_message). If error_message is not None, selection failed.
    """
    if not playlist:
        return None, "No playlist available"
    
    if not playlist.is_variant:
        # Single stream playlist - return it if no specific resolution requested
        if target_resolution:
            return None, f"No variant streams available (single stream playlist), cannot match resolution {target_resolution}"
        return playlist, None
    
    # Filter variants based on codec preference
    codec_tag = "hvc1" if prefer_h265 else "avc1"
    url_tag = "h265" if prefer_h265 else "h264"
    
    target_variants = []
    for variant in playlist.playlists:
        codecs = (variant.stream_info.codecs or "").lower()
        uri = (variant.uri or "").lower()
        if codec_tag in codecs or url_tag in uri:
            target_variants.append(variant)
            
    # If no variants match the preferred codec, fall back to all variants
    if not target_variants:
        target_variants = playlist.playlists
    
    if target_resolution:
        target_height = parse_resolution(target_resolution)
        if not target_height:
            return None, f"Invalid resolution format: {target_resolution}. Expected format like '720p' or '1080p'"
        
        # Find stream matching the target resolution within the filtered variants
        for variant in target_variants:
            if variant.stream_info.resolution:
                height = variant.stream_info.resolution[1]
                if height == target_height:
                    return variant, None
        
        # Resolution not found - list available resolutions in the filtered variants
        available = []
        for variant in target_variants:
            if variant.stream_info.resolution:
                height = variant.stream_info.resolution[1]
                available.append(f"{height}p")
        available_str = ", ".join(available) if available else "none"
        return None, f"No video stream found with resolution {target_resolution}. Available resolutions: {available_str}"
    
    # Default: return the stream with the highest resolution from filtered variants
    best_variant = None
    max_resolution = 0
    
    for variant in target_variants:
        if variant.stream_info.resolution:
            height = variant.stream_info.resolution[1]
            if height > max_resolution:
                max_resolution = height
                best_variant = variant
    
    if not best_variant and target_variants:
        return target_variants[0], None
    
    if best_variant:
        return best_variant, None
    return None, "No video streams available"


def select_audio_track(playlist, target_language, base_url, descriptive_audio=False):
    """Select the appropriate audio track based on language preference and descriptive audio flag."""
    if not playlist or not playlist.media:
        return None, "No media groups available in playlist"
    audio_media = [m for m in playlist.media if m.type == 'AUDIO']
    if not audio_media:
        return None, "No audio tracks available"
    lang_base = target_language.lower().replace('audio', '').replace('description', '').strip()
    # Find all matching language tracks
    candidates = [a for a in audio_media if a.language and a.language.lower() == lang_base]
    if candidates:
        if descriptive_audio:
            filtered = [a for a in candidates if a.name and 'description' in a.name.lower()]
            if filtered:
                return filtered[0], None
        filtered = [a for a in candidates if not (a.name and 'description' in a.name.lower())]
        if filtered:
            return filtered[0], None
        return candidates[0], None
    # Partial match
    candidates = [a for a in audio_media if a.language and a.language.lower().startswith(lang_base)]
    if candidates:
        if descriptive_audio:
            filtered = [a for a in candidates if a.name and 'description' in a.name.lower()]
            if filtered:
                return filtered[0], None
        filtered = [a for a in candidates if not (a.name and 'description' in a.name.lower())]
        if filtered:
            return filtered[0], None
        return candidates[0], None
    available = [a.language for a in audio_media if a.language]
    available_str = ", ".join(set(available)) if available else "none"
    return None, f"No audio track found with language '{target_language}'. Available languages: {available_str}"


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


def print_selected_tracks(selected_video, selected_audios, selected_subtitles, base_url, log_func=print):
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

    # Print selected audio tracks
    log_func("\n  Audio Tracks:")
    if selected_audios:
        for audio in selected_audios:
            name = audio.name if audio.name else "Unknown"
            language = audio.language if audio.language else "Unknown"
            uri = urljoin(base_url, audio.uri) if audio.uri else "N/A"
            group_id = audio.group_id if audio.group_id else "N/A"
            log_func(f"    Language Name: {name}")
            log_func(f"    Language Code: {language}")
            if audio.uri:
                log_func(f"    URI: {uri}")
    else:
        log_func("    None")

    # Print selected subtitle tracks
    log_func("\n  Subtitle Tracks:")
    if selected_subtitles:
        for subtitle in selected_subtitles:
            name = subtitle.name if subtitle.name else "Unknown"
            language = subtitle.language if subtitle.language else "Unknown"
            uri = urljoin(base_url, subtitle.uri) if subtitle.uri else "N/A"
            group_id = subtitle.group_id if subtitle.group_id else "N/A"
            log_func(f"    Language Name: {name}")
            log_func(f"    Language Code: {language}")
            if subtitle.uri:
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


def combine_with_ffmpeg(video_file, audio_files, subtitle_files, output_file, output_format='mp4'):
    """Use ffmpeg to combine video, audio, and subtitle into final output file.
    
    Args:
        video_file: Path to video file
        audio_files: List of paths to audio files (can be empty)
        subtitle_files: List of paths to subtitle files (can be empty)
        output_file: Path to output file
        output_format: 'mp4' or 'mkv'
    """
    try:
        # Check if ffmpeg is available
        if not shutil.which('ffmpeg'):
            return False, "ffmpeg not found. Please install ffmpeg to combine streams."
        
        if not video_file or not os.path.exists(video_file):
            return False, "Video file not found"
        
        # Normalize inputs to lists
        if not isinstance(audio_files, list):
            audio_files = [audio_files] if audio_files else []
        if not isinstance(subtitle_files, list):
            subtitle_files = [subtitle_files] if subtitle_files else []
        
        # Filter out None and non-existent files
        audio_files = [f for f in audio_files if f and os.path.exists(f)]
        subtitle_files = [f for f in subtitle_files if f and os.path.exists(f)]
        
        # Build ffmpeg command
        cmd = ['ffmpeg', '-y', '-loglevel', 'error']
        
        # Track input indices
        input_idx = 0
        video_idx = 0
        
        # Add video input
        cmd.extend(['-i', video_file])
        input_idx += 1
        
        # Add audio inputs
        audio_indices = []
        for audio_file in audio_files:
            cmd.extend(['-i', audio_file])
            audio_indices.append(input_idx)
            input_idx += 1
        
        # Add subtitle inputs
        subtitle_indices = []
        for subtitle_file in subtitle_files:
            cmd.extend(['-i', subtitle_file])
            subtitle_indices.append(input_idx)
            input_idx += 1
        
        # Map streams
        # Map video
        cmd.extend(['-map', f'{video_idx}:v:0'])
        
        # Map audio - prefer separate audio tracks, otherwise try video's embedded audio
        if audio_indices:
            for audio_idx in audio_indices:
                cmd.extend(['-map', f'{audio_idx}:a:0'])
        else:
            # Try to map audio from video (may not exist)
            cmd.extend(['-map', f'{video_idx}:a?'])
        
        # Map subtitles
        for subtitle_idx in subtitle_indices:
            cmd.extend(['-map', f'{subtitle_idx}:s:0'])
        
        # Codec settings
        cmd.extend(['-c:v', 'copy'])  # Copy video codec
        cmd.extend(['-c:a', 'copy'])  # Copy audio codec
        
        # Subtitle codec based on format
        if subtitle_indices:
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
        help=f'Audio language code(s), comma-separated (default: {default_language} from system locale)'
    )
    parser.add_argument(
        '--subtitle-language',
        type=str,
        default=default_language,
        help=f'Subtitle language code(s), comma-separated (default: {default_language} from system locale)'
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
    parser.add_argument(
        '--descriptive-audio',
        action='store_true',
        help='Select descriptive audio tracks (Audio Description) when available.'
    )
    parser.add_argument(
        '--h265',
        action='store_true',
        help='Prefer h265/HEVC video streams over h264/AVC.'
    )
    args = parser.parse_args()
    args.audio_languages = [lang.strip() for lang in args.audio_language.split(',') if lang.strip()]
    args.subtitle_languages = [lang.strip() for lang in args.subtitle_language.split(',') if lang.strip()]
    return args


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
                selected_video, video_error = select_video_stream(playlist, args.video_stream, base_url, prefer_h265=args.h265)
                selected_audios = []
                audio_errors = []
                for lang in args.audio_languages:
                    audio, error = select_audio_track(playlist, lang, base_url, descriptive_audio=args.descriptive_audio)
                    if audio:
                        selected_audios.append(audio)
                    else:
                        audio_errors.append(f"{lang}: {error}")
                selected_subtitles = []
                subtitle_errors = []
                for lang in args.subtitle_languages:
                    subtitle, error = select_subtitle_track(playlist, lang, base_url)
                    if subtitle:
                        selected_subtitles.append(subtitle)
                    else:
                        subtitle_errors.append(f"{lang}: {error}")
                if (len(selected_audios) > 1 or len(selected_subtitles) > 1) and args.format != 'mkv':
                    log_print("Warning: Multiple audio or subtitle tracks selected. MKV is recommended for proper multi-track playback.")
                if args.dry_run:
                    if video_error:
                        log_print(f"Warning: {video_error}")
                    for err in audio_errors:
                        log_print(f"Warning: Audio track: {err}")
                    for err in subtitle_errors:
                        log_print(f"Warning: Subtitle track: {err}")
                else:
                    if video_error:
                        log_print(f"Error: {video_error}")
                        sys.exit(1)
                    if audio_errors:
                        for err in audio_errors:
                            log_print(f"Error: Audio track: {err}")
                        sys.exit(1)
                    if subtitle_errors:
                        for err in subtitle_errors:
                            log_print(f"Error: Subtitle track: {err}")
                        sys.exit(1)
                print_selected_tracks(selected_video, selected_audios, selected_subtitles, base_url, log_func=log_print)
                if args.dry_run:
                    log_print("\n  DRY RUN: Showing URLs and checking validity...")
                    urls_to_check = []
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
                    for audio in selected_audios:
                        if audio.uri:
                            audio_playlist_url = urljoin(base_url, audio.uri)
                            log_print(f"  Would download audio: {audio_playlist_url}")
                            urls_to_check.append(audio_playlist_url)
                    for subtitle in selected_subtitles:
                        if subtitle.uri:
                            subtitle_url = urljoin(base_url, subtitle.uri)
                            log_print(f"  Would download subtitle: {subtitle_url}")
                            urls_to_check.append(subtitle_url)
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
                
                # Download and combine streams
                log_print("\n  Downloading and combining streams...")
                
                # Create output directory if it doesn't exist
                output_dir = Path(args.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate output filename
                safe_title = sanitize_filename(title)
                output_filename = f"S{season:02d}E{episode:02d} - {safe_title}.{args.format}"
                output_file = output_dir / output_filename
                
                # Create temporary directory for downloads
                with tempfile.TemporaryDirectory() as temp_dir:
                    video_file = None
                    audio_files = []
                    subtitle_files = []
                    
                    # Download video stream
                    if selected_video:
                        if hasattr(selected_video, 'uri'):
                            # Variant stream - need to get the playlist URL
                            video_playlist_url = urljoin(base_url, selected_video.uri)
                            log_print("  Downloading video stream...")
                            video_file, error = download_segments(video_playlist_url, base_url, temp_dir, "video")
                            if error:
                                log_print(f"Error: {error}")
                                sys.exit(1)
                        elif hasattr(selected_video, 'segments'):
                            # Media playlist - use the original URL
                            log_print("  Downloading video stream...")
                            video_file, error = download_segments(url, base_url, temp_dir, "video")
                            if error:
                                log_print(f"Error: {error}")
                                sys.exit(1)
                    
                    # Download audio streams
                    for i, audio in enumerate(selected_audios):
                        if audio.uri:
                            audio_playlist_url = urljoin(base_url, audio.uri)
                            log_print(f"  Downloading audio stream {i+1}/{len(selected_audios)}...")
                            audio_file, error = download_segments(audio_playlist_url, base_url, temp_dir, f"audio_{i}")
                            if error:
                                log_print(f"Error: {error}")
                                sys.exit(1)
                            audio_files.append(audio_file)
                    
                    # Download subtitles
                    for i, subtitle in enumerate(selected_subtitles):
                        if subtitle.uri:
                            log_print(f"  Downloading subtitle {i+1}/{len(selected_subtitles)}...")
                            subtitle_file, error = download_subtitle(subtitle.uri, base_url, temp_dir)
                            if error:
                                log_print(f"Warning: {error}")
                            else:
                                subtitle_files.append(subtitle_file)
                    
                    # Combine with ffmpeg
                    log_print("  Combining streams with ffmpeg...")
                    success, error = combine_with_ffmpeg(video_file, audio_files, subtitle_files, str(output_file), args.format)
                    if not success:
                        log_print(f"Error: {error}")
                        sys.exit(1)
                    
                    log_print(f"\n  ✓ Successfully created: {output_file}")

    except FileNotFoundError:
        log_print(f"Error: Could not find {csv_file}")
        sys.exit(1)
    except Exception as e:
        log_print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

