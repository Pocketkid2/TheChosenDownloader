# TheChosenDownloader
A tool (makefile) for downloading episodes of the TV show The Chosen as MP4 files direct from the website for free

### Prerequisites
You will need:
* `ffmpeg` with `libx264` (for re-encodes)
* `youtube-dl` or its preferred fork, `yt-dlp` (makefiles are configured for yt-dlp but this can easily be changed)

### Usage
Simply enter a directory, and type `make` to download all episodes for that season in full 1080p.

To build just a single episode, you can type `make episodeX` to download just that episode in full 1080p.

### Options
To enable re-encoding, you can set the the command line Make variables `RE_ENCODE_720=YES` and `RE_ENCODE_480=YES` which will apply to whatever target you have selected. These flags can both be used at the same time. 

There are also Make targets for `re-encode-720` and `re-encode-480` that will target the entire season re-encoded at the respective resolution, but these will run sequentially and not simultaneously if used together.

Encoding uses `libx264` through ffmpeg. To set the quality for 720p or 480p encodes, you can change the CRF (Compression Rate Factor) by adding `CRF_720=X` and/or `CRF_480=Y` to the command line. It is not recommended to choose a value smaller than 17 or larger than 28. Default is 23, which is already pretty highly compressed. If you want to increase the quality above default you probably want between 20-22. 

In addition to setting the CRF, you can also set a preset that will determine the trade-off between encode quality and time spent. This is done via command line with `PRESET_720=X` and `PRESET_480=Y`. The default preset is `medium` but the available options are `ultrafast`, `superfast`, `veryfast`, `faster`, `fast`, `medium`, `slow`, `slower`, `veryslow`. According to [the ffmpeg wiki](https://trac.ffmpeg.org/wiki/Encode/H.264), there are diminishing returns for the slower presets but if you don't care about time then that may be what you want.

## Known Issues
Season 1 and Season 2 appear to have a different download format than Season 3, as the audio and video can be downloaded separately to account for different audio languages. This means that the common makefile setup that currently exists does not work correctly for those two seasons. I will fix this as soon as I can.
