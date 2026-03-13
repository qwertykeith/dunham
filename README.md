# Dunham

Supercut montage generator. Transcribes videos, fuzzy-searches for a word, and stitches every match into a montage.

Named after Agent Olivia Dunham from *Fringe*.

## Quick start

```sh
git clone <repo> && cd dunham

# Put your video files in data/videos/  (subfolders are fine)

docker compose build
docker compose run dunham run data/videos "dunham"

# Output: data/output/montage.mp4
```

## Commands

All commands are run via `docker compose run dunham <command>`.

| Command | Example |
|---|---|
| `run FOLDER WORD` | `docker compose run dunham run data/videos "olivia"` |
| `transcribe FOLDER` | `docker compose run dunham transcribe data/videos` |
| `search WORD` | `docker compose run dunham search dunham --output data/hits.json` |
| `montage HITS_JSON` | `docker compose run dunham montage data/hits.json` |
| `download URL` | `docker compose run dunham download "https://..."` |

Run `docker compose run dunham <command> --help` for all options.
