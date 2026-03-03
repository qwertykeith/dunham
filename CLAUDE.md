# Dunham

Supercut montage generator: transcribe videos with faster-whisper, fuzzy-search transcripts for words/phrases, and stitch matching clips into a montage via ffmpeg.

## Architecture

Pipeline: **download** (yt-dlp) -> **transcribe** (faster-whisper) -> **search** (jellyfish fuzzy match) -> **montage** (ffmpeg concat).

Each module (`download.py`, `transcribe.py`, `search.py`, `montage.py`) exposes pure functions — no classes. `cli.py` is Click-based and wires them together. The `run` command executes the full pipeline in one shot.

## Key Conventions

- **Functional style** — no classes except where injecting deps. Modules are thin and single-responsibility.
- **Australian English** in comments and user-facing strings.
- **Tests live in `tests/`**, not co-located with source.
- **ffmpeg via `subprocess`**, not ffmpeg-python. Same for yt-dlp.
- **Phonetic matching** uses jellyfish: Metaphone equality first, then Levenshtein distance within a threshold (default 2).
- **faster-whisper model loaded lazily** inside `_transcribe_video` (deferred import) to avoid import-time GPU allocation. Mock `faster_whisper.WhisperModel` in tests.

## Development

- Python 3.11+, venv at `.venv`
- Install: `pip install -e .`
- Test: `pytest tests/`
- Docker: `docker compose build && docker compose run dunham`
- CLI entry point: `dunham` (registered in `pyproject.toml` as `dunham.cli:cli`)

## Data Layout

```
data/
  videos/        # Source video files (.mp4, .mkv, .avi, .webm, .mov)
  transcripts/   # Per-video JSON transcripts (word-level timestamps)
  output/        # Montage output (default: montage.mp4)
```

## CLI Commands

| Command      | Description                                    |
|--------------|------------------------------------------------|
| `download`   | Fetch video(s) from URL via yt-dlp             |
| `transcribe` | Transcribe all videos in a folder              |
| `search`     | Fuzzy-search transcripts for a word or phrase   |
| `montage`    | Stitch clips from a hits JSON into a video      |
| `run`        | Full pipeline: transcribe -> search -> montage  |
