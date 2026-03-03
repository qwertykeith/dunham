"""Transcribe video files using faster-whisper and output per-video JSON."""

from __future__ import annotations

import json
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".webm", ".mov"}


def _discover_videos(folder: Path) -> list[Path]:
    """Walk folder recursively for supported video formats."""
    return sorted(
        p
        for p in folder.rglob("*")
        if p.suffix.lower() in VIDEO_EXTENSIONS and p.is_file()
    )


def _transcribe_video(video: Path, model_size: str) -> dict:
    """Run faster-whisper on a single video and return the transcript dict."""
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size)
    segments, _info = model.transcribe(str(video), word_timestamps=True)

    result_segments = []
    for seg in segments:
        words = [
            {"word": w.word, "start": w.start, "end": w.end}
            for w in (seg.words or [])
        ]
        result_segments.append(
            {"text": seg.text, "start": seg.start, "end": seg.end, "words": words}
        )

    return {"source": video.name, "segments": result_segments}


def transcribe_folder(
    folder: Path,
    transcripts_dir: Path,
    model_size: str = "medium",
    force: bool = False,
) -> list[Path]:
    """Transcribe all videos in *folder*, writing JSON transcripts to *transcripts_dir*.

    Skips videos whose transcript already exists unless *force* is True.
    Returns a list of transcript paths that were created this run.
    """
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    videos = _discover_videos(folder)
    created: list[Path] = []

    for video in videos:
        out_path = transcripts_dir / f"{video.stem}.json"

        if out_path.exists() and not force:
            continue

        transcript = _transcribe_video(video, model_size)
        out_path.write_text(json.dumps(transcript, indent=2, ensure_ascii=False))
        created.append(out_path)

    return created
