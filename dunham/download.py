"""Video downloading — thin wrapper around yt-dlp."""

from __future__ import annotations

import subprocess
from pathlib import Path


def download_video(url: str, output_dir: Path) -> list[Path]:
    """Download video(s) from *url* into *output_dir* using yt-dlp.

    Supports playlist URLs; yt-dlp handles expansion naturally.
    Returns a list of downloaded file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    before = set(output_dir.iterdir())

    subprocess.run(
        ["yt-dlp", "-o", str(output_dir / "%(title)s.%(ext)s"), url],
        check=True,
        capture_output=True,
    )

    after = set(output_dir.iterdir())
    return sorted(after - before)
