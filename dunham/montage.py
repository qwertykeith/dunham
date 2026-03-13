"""Montage creation — extract clips and concatenate via ffmpeg."""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path


def _clip_key(source: str, start: float, end: float) -> str:
    """Deterministic clip filename based on source, start, and end."""
    stem = Path(source).stem
    digest = hashlib.sha256(f"{source}|{start}|{end}".encode()).hexdigest()[:12]
    return f"{stem}_{digest}.mp4"


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


def create_montage(
    hits: list[dict],
    videos_dir: Path,
    output: Path,
    clips_dir: Path | None = None,
) -> Path:
    """Build a montage by extracting and concatenating clips for each hit.

    Each item in *hits* must carry ``source``, ``clip_start`` and ``clip_end``.

    When *clips_dir* is ``None`` (default), clips are extracted into a temp
    directory that is cleaned up automatically.  When provided, clips are
    cached in that directory — pre-existing clips are skipped — and the
    caller is responsible for cleanup.
    """
    output.parent.mkdir(parents=True, exist_ok=True)

    def _extract_clips(work_dir: Path) -> list[Path]:
        clip_paths: list[Path] = []
        for hit in hits:
            clip_name = _clip_key(hit["source"], hit["clip_start"], hit["clip_end"])
            clip_path = work_dir / clip_name
            if not clip_path.exists():
                extract_clip(
                    source=videos_dir / hit["source"],
                    start=hit["clip_start"],
                    end=hit["clip_end"],
                    output=clip_path,
                )
            clip_paths.append(clip_path)
        return clip_paths

    def _concat(clip_paths: list[Path], work_dir: Path) -> None:
        concat_file = work_dir / "concat.txt"
        concat_file.write_text(
            "\n".join(f"file '{clip.name}'" for clip in clip_paths) + "\n"
        )
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

    if clips_dir is not None:
        clips_dir.mkdir(parents=True, exist_ok=True)
        clip_paths = _extract_clips(clips_dir)
        _concat(clip_paths, clips_dir)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            clip_paths = _extract_clips(tmp_dir)
            _concat(clip_paths, tmp_dir)

    return output
