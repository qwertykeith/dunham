# Dunham

CLI tool that transcribes video files with word-level timestamps, finds target words or phrases (including soundalikes), and cuts together a montage of those moments.

Named after Agent Olivia Dunham from *Fringe* -- the original test case was "find every time someone says *Dunham*."


## Stack

| Component | Role |
|---|---|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Speech-to-text with word-level timestamps |
| [jellyfish](https://github.com/jamesturk/jellyfish) | Phonetic matching (Metaphone) and Levenshtein distance |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Video downloading |
| [ffmpeg](https://ffmpeg.org/) | Clip extraction and concatenation |
| [Click](https://click.palletsprojects.com/) | CLI framework |

Python 3.11+.


## Getting started

### Local (venv)

```sh
# ffmpeg and yt-dlp must be on PATH
brew install ffmpeg yt-dlp   # macOS

python -m venv .venv && source .venv/bin/activate
pip install .
dunham --help
```

### Docker

```sh
docker compose build          # builds image, pre-downloads whisper model
docker compose run dunham --help
```

The `data/` directory is mounted as a volume, so videos, transcripts, and output persist between runs.


## Commands

| Command | Description |
|---|---|
| `dunham transcribe FOLDER` | Transcribe all video files in `FOLDER`. Writes JSON to `data/transcripts/`. |
| `dunham search WORD` | Fuzzy-search transcripts for `WORD` (or a multi-word phrase). Prints or saves hit list as JSON. |
| `dunham montage HITS_JSON` | Cut together a montage from a search results JSON file. |
| `dunham download URL` | Download a video via yt-dlp. |
| `dunham run FOLDER WORD` | Full pipeline: transcribe, search, and montage in one command. |

Run `dunham <command> --help` for all options (model size, Levenshtein threshold, output paths, etc.).


## Project structure

```
dunham/
  __init__.py
  cli.py            # Click command group + subcommands
  transcribe.py     # faster-whisper transcription, word-level timestamps
  search.py         # Fuzzy matching: exact, Metaphone, Levenshtein
  montage.py        # ffmpeg clip extraction + concatenation
  download.py       # yt-dlp wrapper
tests/
  test_transcribe.py
  test_search.py
  test_montage.py
seed.py             # Downloads Fringe clips from YouTube for testing
Dockerfile
docker-compose.yml
pyproject.toml
```


## Pipeline overview

```
  Video files
      |
      v
  1. TRANSCRIBE  (faster-whisper, word_timestamps=True)
      |           Outputs per-file JSON with segments and per-word start/end times
      v
  2. SEARCH      (jellyfish)
      |           Matches target word/phrase against every transcribed word
      |           Three match strategies: exact, Metaphone phonetic, Levenshtein distance
      |           Each hit includes padded clip boundaries (word timestamp +/- 0.3s)
      v
  3. MONTAGE     (ffmpeg)
                  Extracts each hit as a clip, concatenates into a single video
```

Transcripts are cached as JSON. Re-running `transcribe` on the same folder skips already-processed files (use `--force` to override).


## Quick example: the Fringe use case

```sh
# 1. Seed some Fringe clips (uses yt-dlp search)
python seed.py

# 2. One-shot pipeline: transcribe everything, find "dunham", build montage
dunham run data/videos dunham

# Output lands at data/output/montage.mp4
```

Or step by step:

```sh
# Transcribe with the large model for better accuracy
dunham transcribe data/videos --model large-v3

# Search with a tighter threshold (default is 2)
dunham search dunham --threshold 1 --output data/hits.json

# Review hits, then build the montage
dunham montage data/hits.json --output data/output/every-dunham.mp4
```

The phonetic matching means "Dunham", "Dunam", and other soundalikes all get caught -- you don't need an exact transcript.
