"""Tests for dunham.transcribe — video discovery, JSON output, skip & force logic."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from dunham.transcribe import VIDEO_EXTENSIONS, _discover_videos, transcribe_folder


# -- helpers ------------------------------------------------------------------


def _touch_video(tmp_path: Path, name: str) -> Path:
    """Create an empty file to act as a fake video."""
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch()
    return p


def _fake_segments():
    """Return mock segment objects matching faster-whisper's interface."""
    word_a = SimpleNamespace(word="Agent", start=1.0, end=1.3)
    word_b = SimpleNamespace(word="Dunham", start=1.4, end=1.8)
    seg = SimpleNamespace(text="Agent Dunham", start=1.0, end=1.8, words=[word_a, word_b])
    return [seg]


# -- tests --------------------------------------------------------------------


def test_discover_finds_supported_extensions(tmp_path: Path):
    for ext in VIDEO_EXTENSIONS:
        _touch_video(tmp_path, f"clip{ext}")

    # Non-video files should be ignored
    _touch_video(tmp_path, "readme.txt")
    _touch_video(tmp_path, "photo.jpg")

    found = _discover_videos(tmp_path)
    assert len(found) == len(VIDEO_EXTENSIONS)
    assert all(p.suffix.lower() in VIDEO_EXTENSIONS for p in found)


def test_discover_walks_subdirectories(tmp_path: Path):
    _touch_video(tmp_path / "season1", "ep01.mp4")
    _touch_video(tmp_path / "season2", "ep02.mkv")

    found = _discover_videos(tmp_path)
    assert len(found) == 2


@patch("dunham.transcribe._transcribe_video")
def test_json_output_structure(mock_transcribe, tmp_path: Path):
    videos_dir = tmp_path / "videos"
    transcripts_dir = tmp_path / "transcripts"
    _touch_video(videos_dir, "fringe_s01e01.mp4")

    mock_transcribe.return_value = {
        "source": "fringe_s01e01.mp4",
        "segments": [
            {
                "text": "Agent Dunham",
                "start": 1.0,
                "end": 1.8,
                "words": [
                    {"word": "Agent", "start": 1.0, "end": 1.3},
                    {"word": "Dunham", "start": 1.4, "end": 1.8},
                ],
            }
        ],
    }

    created = transcribe_folder(videos_dir, transcripts_dir)

    assert len(created) == 1
    data = json.loads(created[0].read_text())
    assert data["source"] == "fringe_s01e01.mp4"
    assert len(data["segments"]) == 1

    seg = data["segments"][0]
    assert "text" in seg and "start" in seg and "end" in seg
    assert len(seg["words"]) == 2
    assert seg["words"][0]["word"] == "Agent"


@patch("dunham.transcribe._transcribe_video")
def test_skips_existing_transcript(mock_transcribe, tmp_path: Path):
    videos_dir = tmp_path / "videos"
    transcripts_dir = tmp_path / "transcripts"
    _touch_video(videos_dir, "clip.mp4")

    # Pre-create the transcript so it should be skipped
    transcripts_dir.mkdir(parents=True)
    (transcripts_dir / "clip.json").write_text("{}")

    created = transcribe_folder(videos_dir, transcripts_dir)

    assert created == []
    mock_transcribe.assert_not_called()


@patch("dunham.transcribe._transcribe_video")
def test_force_overrides_skip(mock_transcribe, tmp_path: Path):
    videos_dir = tmp_path / "videos"
    transcripts_dir = tmp_path / "transcripts"
    _touch_video(videos_dir, "clip.mp4")

    transcripts_dir.mkdir(parents=True)
    (transcripts_dir / "clip.json").write_text("{}")

    mock_transcribe.return_value = {"source": "clip.mp4", "segments": []}

    created = transcribe_folder(videos_dir, transcripts_dir, force=True)

    assert len(created) == 1
    mock_transcribe.assert_called_once()
