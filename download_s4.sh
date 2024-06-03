#!/bin/bash

show_name="The Chosen"
season_number=4

# Video download quality
# Available options are:
#   360p - 884521 average bandwidth
#   480p - 1130073 average bandwidth
#   720p - 2576204 average bandwidth
#   1080p - 4983954 average bandwidth
#   1440p - 15337989 average bandwidth
#   2160p - 4983533 average bandwidth
video_resolution="1440p"

base_url="https://fastly.frontrowcdn.com/channels/12884901895/VIDEO"

# Array of episode details
episodes=(
    "184683596182|Promises|279172878841.m3u8|279172879547.m3u8"
    "184683596183|Confessions|279172878842.m3u8|279172879548.m3u8"
    "184683596185|Moon to Blood|279172878844.m3u8|"
    "184683596186|Calm Before|279172878845.m3u8|"
    "184683596187|Sitting, Serving, Scheming|279172878846.m3u8|"
    "184683596188|Dedication|279172878847.m3u8|"
    "184683596184|The Last Sign|279172878843.m3u8|"
    "184683596189|Humble|279172878848.m3u8|"
)

# Loop through the episodes
for ((i=0; i<${#episodes[@]}; i++))
do
    # Extract episode details from the current episode
    IFS='|' read -ra episode_details <<< "${episodes[$i]}"
    episode_id="${episode_details[0]}"
    episode_title="${episode_details[1]}"
    audio_link_file="${episode_details[2]}"
    subtitle_link_file="${episode_details[3]}"

    # Construct video link
    video_link="${base_url}/${episode_id}/video_${video_resolution}.m3u8"

    # Construct audio link
    audio_link="${base_url}/${episode_id}/${audio_link_file}"

    # Construct subtitle link if available
    if [ -n "$subtitle_link_file" ]; then
        subtitle_link="${base_url}/${episode_id}/${subtitle_link_file}"
    else
        subtitle_link=""
    fi

    # Download video and audio streams
    ffmpeg -i "$video_link" -c copy video.mp4
    ffmpeg -i "$audio_link" -c copy audio.aac

    # Download subtitle if available
    if [ -n "$subtitle_link" ]; then
        ffmpeg -i "$subtitle_link" -c:s mov_text subtitle.vtt
    fi

    # Create final filename
    output_filename="${show_name} S${season_number}E$((i+1)) - ${episode_title}.mp4"

    # Combine streams depending on whether subtitle file exists
    if [ -n "$subtitle_link" ]; then
        ffmpeg -i video.mp4 -i audio.aac -i subtitle.vtt -c:v copy -c:a copy -c:s mov_text -metadata:s:s:0 language=eng "$output_filename"
    else
        ffmpeg -i video.mp4 -i audio.aac -c:v copy -c:a copy "$output_filename"
    fi

    # Clean up temporary files
    if [ -n "$subtitle_link" ]; then
        rm video.mp4 audio.aac subtitle.vtt
    else
        rm video.mp4 audio.aac
    fi
done