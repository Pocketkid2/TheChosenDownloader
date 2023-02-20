# Commands
YOUTUBE_DL_CMD = yt-dlp
FFMPEG_CMD = ffmpeg

# Extensions
FINAL_VIDEO_EXTENSION_1080 = 1080p.mp4
FINAL_VIDEO_EXTENSION_720 = 720p.mp4
FINAL_VIDEO_EXTENSION_480 = 480p.mp4
INTERMEDIATE_VIDEO_EXTENSION = video
SUBTITLE_FILE_EXTENSION = vtt

# Options
RE_ENCODE_720 = NO
RE_ENCODE_480 = NO

CRF_720 = 23
CRF_480 = 23

PRESET_720 = medium
PRESET_480 = medium

# Episode URLs
EPISODE_URLS = https://chosendl.noxsolutions.com/thechosen/hls/episodes/s02e01/s02e01-en-1080p.m3u8 \
https://chosendl.noxsolutions.com/thechosen/hls/episodes/s02e02/s02e02-en-1080p.m3u8 \
https://chosendl.noxsolutions.com/thechosen/hls/episodes/s02e03/s02e03-en-1080p.m3u8 \
https://chosendl.noxsolutions.com/thechosen/hls/episodes/s02e04/s02e04-en-1080p.m3u8 \
https://chosendl.noxsolutions.com/thechosen/hls/episodes/s02e05/s02e05-en-1080p.m3u8 \
https://chosendl.noxsolutions.com/thechosen/hls/episodes/s02e06/s02e06-en-1080p.m3u8 \
https://chosendl.noxsolutions.com/thechosen/hls/episodes/s02e07/s02e07-en-1080p.m3u8 \
https://chosendl.noxsolutions.com/thechosen/hls/episodes/s02e08/s02e08-en-1080p.m3u8

# Episode titles
EPISODE_TITLES = [S2E1]_Thunder \
[S2E2]_I_Saw_You \
[S2E3]_Matthew_4_24 \
[S2E4]_The_Perfect_Opportunity \
[S2E5]_Spirit \
[S2E6]_Unlawful \
[S2E7]_Reckoning \
[S2E8]_Beyond_Mountains \

# Define a rule to download an episode
define download_episode

ifeq ($(RE_ENCODE_720), YES)

$(2).$(FINAL_VIDEO_EXTENSION_720): $(if $(filter $(RE_ENCODE_480), YES), $(2).$(FINAL_VIDEO_EXTENSION_480), $(2).$(FINAL_VIDEO_EXTENSION_1080))
	@ffmpeg -i $(2).$(FINAL_VIDEO_EXTENSION_1080) -vf scale=1280:-1 -c:a copy -c:v libx264 -preset $(PRESET_720) -crf $(CRF_720) -tune film $(2).$(FINAL_VIDEO_EXTENSION_720)

endif

ifeq ($(RE_ENCODE_480), YES)

$(2).$(FINAL_VIDEO_EXTENSION_480): $(2).$(FINAL_VIDEO_EXTENSION_1080)
	@ffmpeg -i $(2).$(FINAL_VIDEO_EXTENSION_1080) -vf scale=854:-1 -c:a copy -c:v libx264 -preset $(PRESET_480) -crf $(CRF_480) -tune film $(2).$(FINAL_VIDEO_EXTENSION_480)

endif

$(2).$(FINAL_VIDEO_EXTENSION_1080): $(1).$(INTERMEDIATE_VIDEO_EXTENSION) $(1).*.$(SUBTITLE_FILE_EXTENSION)
	@echo "Merging episode $(1) video and subtitle into mp4"
	@$(FFMPEG_CMD) -i $(1).$(INTERMEDIATE_VIDEO_EXTENSION) -i $(1).*.$(SUBTITLE_FILE_EXTENSION) -c copy -c:s mov_text $(2).$(FINAL_VIDEO_EXTENSION_1080)

$(1).$(INTERMEDIATE_VIDEO_EXTENSION):
	@echo "Downloading episode $(1) video"
	@$(YOUTUBE_DL_CMD) -o $(1).$(INTERMEDIATE_VIDEO_EXTENSION) $(3)

$(1).*.$(SUBTITLE_FILE_EXTENSION):
	@echo "Downloading episode $(1) subtitles"
	@$(YOUTUBE_DL_CMD) --write-sub --skip-download -o $(1) $(3)

endef

# Use the "foreach" function to apply "download_episode" to each episode number
EPISODE_NUMBERS := $(shell seq 1 8)

$(foreach episode,$(EPISODE_NUMBERS),$(eval $(call download_episode,$(episode),$(word $(episode),$(EPISODE_TITLES)),$(word $(episode),$(EPISODE_URLS)))))

# Define a rule to download all episodes
.PHONY: all
all: $(addsuffix .1080p.mp4,$(EPISODE_TITLES))

# Define a rule to re-encode all episodes at 720p
.PHONY: re-encode-720
re-encode-720:
	@$(MAKE) RE_ENCODE_720=YES

# Define a rule to re-encode all episodes at 480p
.PHONY: re-encode-480
re-encode-480:
	@$(MAKE) RE_ENCODE_480=YES

.PHONY: episode%
episode%:
	@$(MAKE) EPISODE_NUMBERS=$*

.PHONY: clean
clean: clean1 clean2 clean3 clean4 clean5 clean6 clean7 clean8

clean%:
	@rm $*.*