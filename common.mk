# Commands
YOUTUBE_DL_CMD = yt-dlp
FFMPEG_CMD = ffmpeg
YOUTUBE_DL_ARGS = --quiet --progress
FFMPEG_ARGS = -y -v quiet -stats

# Extensions
FINAL_VIDEO_EXTENSION_1080 = 1080p.mp4
FINAL_VIDEO_EXTENSION_720 = 720p.mp4
FINAL_VIDEO_EXTENSION_480 = 480p.mp4
INTERMEDIATE_VIDEO_EXTENSION = mp4
SUBTITLE_FILE_EXTENSION = vtt

# Options
RE_ENCODE_720 = NO
RE_ENCODE_480 = NO
CRF_720 = 22
CRF_480 = 22
PRESET_720 = slow
PRESET_480 = slow

# More macros
RE_ENCODE_720_FFMPEG_ARGS = -vf scale=1280:-1 -c:a copy -c:v libx264 -preset $(PRESET_720) -crf $(CRF_720) -tune film
RE_ENCODE_480_FFMPEG_ARGS = -vf scale=854:-1 -c:a copy -c:v libx264 -preset $(PRESET_480) -crf $(CRF_480) -tune film
FFMPEG_MERGE_ARGS = -c:a copy -c:v copy -c:s mov_text

# Compute the first target based on what re-encode settings are enabled
ifeq ($(RE_ENCODE_720), YES)
TARGET_EXTENSION = .$(FINAL_VIDEO_EXTENSION_720)
else ifeq ($(RE_ENCODE_480), YES)
TARGET_EXTENSION = .$(FINAL_VIDEO_EXTENSION_480)
else
TARGET_EXTENSION = .$(FINAL_VIDEO_EXTENSION_1080)
endif

# Define a rule to download all episodes
.PHONY: all
all: $(addsuffix $(TARGET_EXTENSION),$(EPISODE_TITLES))

# Define a function to generate a rule to download an episode
define download_episode

ifeq ($(RE_ENCODE_720), YES)

$(2).$(FINAL_VIDEO_EXTENSION_720): $(if $(filter $(RE_ENCODE_480), YES), $(2).$(FINAL_VIDEO_EXTENSION_480), $(2).$(FINAL_VIDEO_EXTENSION_1080))
	@echo "Re-encoding 1080p file at 720p with CRF $(CRF_720) and preset $(PRESET_720)"
	@$(FFMPEG_CMD) $(FFMPEG_ARGS) -i $(2).$(FINAL_VIDEO_EXTENSION_1080) $(RE_ENCODE_720_FFMPEG_ARGS) $(2).$(FINAL_VIDEO_EXTENSION_720)

endif

ifeq ($(RE_ENCODE_480), YES)

$(2).$(FINAL_VIDEO_EXTENSION_480): $(2).$(FINAL_VIDEO_EXTENSION_1080)
	@echo "Re-encoding 1080p file at 480p with CRF $(CRF_480) and preset $(PRESET_480)"
	@$(FFMPEG_CMD) $(FFMPEG_ARGS) -i $(2).$(FINAL_VIDEO_EXTENSION_1080) $(RE_ENCODE_480_FFMPEG_ARGS) $(2).$(FINAL_VIDEO_EXTENSION_480)

endif

$(2).$(FINAL_VIDEO_EXTENSION_1080): $(1).$(INTERMEDIATE_VIDEO_EXTENSION) $(1).*.$(SUBTITLE_FILE_EXTENSION)
	@echo "Merging episode $(1) video and subtitle into mp4"
	@$(FFMPEG_CMD) $(FFMPEG_ARGS) -i $(1).$(INTERMEDIATE_VIDEO_EXTENSION) -i $(1).*.$(SUBTITLE_FILE_EXTENSION) $(FFMPEG_MERGE_ARGS) $(2).$(FINAL_VIDEO_EXTENSION_1080)

$(1).$(INTERMEDIATE_VIDEO_EXTENSION):
	@echo "Downloading episode $(1) video"
	@$(YOUTUBE_DL_CMD) $(YOUTUBE_DL_ARGS) -f$(FORMAT) -o $(1).$(INTERMEDIATE_VIDEO_EXTENSION) $(3)

$(1).*.$(SUBTITLE_FILE_EXTENSION):
	@echo "Downloading episode $(1) subtitles"
	@$(YOUTUBE_DL_CMD) $(YOUTUBE_DL_ARGS) --write-sub --skip-download -o $(1) $(3)

endef

# Use the "foreach" function to apply "download_episode" to each episode number
EPISODE_NUMBERS := $(shell seq 1 8)

# Create the rules for each episode
$(foreach episode,$(EPISODE_NUMBERS),$(eval $(call download_episode,$(episode),$(word $(episode),$(EPISODE_TITLES)),$(word $(episode),$(EPISODE_URLS)))))

# Define a rule to re-encode all episodes at 720p
.PHONY: re-encode-720
re-encode-720:
	@$(MAKE) RE_ENCODE_720=YES

# Define a rule to re-encode all episodes at 480p
.PHONY: re-encode-480
re-encode-480:
	@$(MAKE) RE_ENCODE_480=YES

# Define rule for just downloading a single episode
.PHONY: episode%
episode%:
	@$(MAKE) EPISODE_NUMBERS=$*

# Define rules for cleaning
.PHONY: clean
clean: clean1 clean2 clean3 clean4 clean5 clean6 clean7 clean8

clean%:
	@rm $*.*