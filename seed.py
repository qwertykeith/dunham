#!/usr/bin/env python3
"""Seed script — download Fringe (2008) clips from YouTube for testing.

Uses yt-dlp's built-in YouTube search to find clips featuring "Dunham".
Run this before testing the pipeline.

Usage:
    python seed.py                    # download all seed clips
    python seed.py --search-only      # just print URLs, don't download
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

OUTPUT_DIR = Path("data/videos")

# Curated YouTube search queries that reliably surface Fringe clips
# where the name "Dunham" is spoken frequently.
# yt-dlp supports "ytsearchN:" prefix to grab the first N results.
SEARCH_QUERIES = [
    # Official-ish clips and fan compilations
    "ytsearch3:fringe olivia dunham scene season 1",
    "ytsearch2:fringe agent dunham walter bishop clip",
    "ytsearch2:fringe pilot scene dunham FBI",
]

# Known direct URLs (trailers, promos) — these are more stable than search
DIRECT_URLS = [
    # Fringe Season 1 trailers/promos typically on Warner/Fox channels
    # Add specific URLs here as you find them, e.g.:
    # "https://www.youtube.com/watch?v=XXXXX",
]


def search_only():
    """Print what yt-dlp would find without downloading."""
    for query in SEARCH_QUERIES:
        print(f"\n--- {query} ---")
        result = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--print", "%(url)s %(title)s", query],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(result.stdout.strip() or "  (no results)")
        else:
            print(f"  Error: {result.stderr.strip()}")


def download_all():
    """Download all seed clips into data/videos/."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_sources = DIRECT_URLS + SEARCH_QUERIES

    for source in all_sources:
        print(f"\n>>> Downloading: {source}")
        cmd = [
            "yt-dlp",
            "-o", str(OUTPUT_DIR / "%(title)s.%(ext)s"),
            # Keep videos short for testing — max 5 min each
            "--match-filter", "duration < 300",
            # Prefer mp4
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
        ]
        if source.startswith("http"):
            cmd.append("--no-playlist")
        cmd.append(source)

        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"  Warning: failed to download {source}", file=sys.stderr)

    print(f"\nDone! Videos saved to {OUTPUT_DIR}/")
    print("Next steps:")
    print(f"  dunham transcribe {OUTPUT_DIR}")
    print("  dunham search dunham")
    print("  dunham run data/videos dunham")


def main():
    parser = argparse.ArgumentParser(description="Seed Fringe test videos")
    parser.add_argument(
        "--search-only",
        action="store_true",
        help="Just print search results, don't download",
    )
    args = parser.parse_args()

    if args.search_only:
        search_only()
    else:
        download_all()


if __name__ == "__main__":
    main()
