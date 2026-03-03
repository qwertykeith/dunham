"""Montage creation — extract clips and concatenate via ffmpeg."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def extract_clip(source: Path, start: float, end: float, output: Path) -> Path:
    """Extract a single clip from *source*, normalised to 1280x720 @ 24fps.

    All clips get the same resolution, frame rate, pixel format, and audio
    sample rate so the concat demuxer can stitch them without re-encoding.
    """
    cmd = [
        "ffmpeg",
        "-ss", str(start),
        "-to", str(end),
        "-i", str(source),
        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24",
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        "-ar", "44100",
        "-ac", "2",
        "-y",
        str(output),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output


def create_montage(hits: list[dict], videos_dir: Path, output: Path) -> Path:
    """Build a montage by extracting and concatenating clips for each hit.

    Each item in *hits* must carry ``source``, ``clip_start`` and ``clip_end``.
    Temporary clips are cleaned up after the final concatenation.
    """
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        clip_paths: list[Path] = []

        # Extract individual clips
        for idx, hit in enumerate(hits):
            clip_path = tmp_dir / f"clip_{idx:04d}.mp4"
            extract_clip(
                source=videos_dir / hit["source"],
                start=hit["clip_start"],
                end=hit["clip_end"],
                output=clip_path,
            )
            clip_paths.append(clip_path)

        # Write concat manifest
        concat_file = tmp_dir / "concat.txt"
        concat_file.write_text(
            "\n".join(f"file '{clip}'" for clip in clip_paths) + "\n"
        )

        # Concatenate all clips into the final output
        subprocess.run(
            [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                "-y",
                str(output),
            ],
            check=True,
            capture_output=True,
        )

    return output
