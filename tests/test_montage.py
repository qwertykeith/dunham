"""Tests for montage creation and video downloading."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

from dunham.download import download_video
from dunham.montage import create_montage, extract_clip


# ---------------------------------------------------------------------------
# extract_clip
# ---------------------------------------------------------------------------

@patch("dunham.montage.subprocess.run")
def test_extract_clip_builds_correct_ffmpeg_command(mock_run: MagicMock):
    source = Path("/videos/ep01.mp4")
    out = Path("/tmp/clip.mp4")

    result = extract_clip(source, start=1.5, end=4.0, output=out)

    mock_run.assert_called_once_with(
        [
            "ffmpeg",
            "-ss", "1.5",
            "-to", "4.0",
            "-i", "/videos/ep01.mp4",
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24",
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "aac",
            "-ar", "44100",
            "-ac", "2",
            "-y",
            "/tmp/clip.mp4",
        ],
        check=True,
        capture_output=True,
    )
    assert result == out


# ---------------------------------------------------------------------------
# create_montage
# ---------------------------------------------------------------------------

@patch("dunham.montage.subprocess.run")
def test_create_montage_generates_concat_file(mock_run: MagicMock, tmp_path: Path):
    hits = [
        {"source": "a.mp4", "clip_start": 0.0, "clip_end": 1.0},
        {"source": "b.mp4", "clip_start": 2.0, "clip_end": 3.0},
    ]
    videos_dir = tmp_path / "videos"
    videos_dir.mkdir()
    output = tmp_path / "out" / "montage.mp4"

    create_montage(hits, videos_dir, output)

    # Two extract calls + one concat call
    assert mock_run.call_count == 3

    # Verify the concat call uses the concat demuxer
    concat_call = mock_run.call_args_list[-1]
    concat_cmd = concat_call.args[0] if concat_call.args else concat_call[0][0]
    assert "-f" in concat_cmd
    assert "concat" in concat_cmd
    assert "-safe" in concat_cmd


@patch("dunham.montage.subprocess.run")
def test_create_montage_temp_files_cleaned_up(mock_run: MagicMock, tmp_path: Path):
    """Temp directory should not persist after create_montage returns."""
    import tempfile

    hits = [{"source": "a.mp4", "clip_start": 0.0, "clip_end": 1.0}]
    videos_dir = tmp_path / "videos"
    videos_dir.mkdir()
    output = tmp_path / "montage.mp4"

    # Track which temp directories are created
    original_cls = tempfile.TemporaryDirectory

    created_dirs: list[str] = []

    class TrackingTempDir(original_cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            created_dirs.append(self.name)

    with patch("dunham.montage.tempfile.TemporaryDirectory", TrackingTempDir):
        create_montage(hits, videos_dir, output)

    # Every temp dir should have been cleaned up
    for d in created_dirs:
        assert not Path(d).exists(), f"Temp directory {d} was not cleaned up"


# ---------------------------------------------------------------------------
# download_video
# ---------------------------------------------------------------------------

@patch("dunham.download.subprocess.run")
def test_download_video_calls_ytdlp(mock_run: MagicMock, tmp_path: Path):
    output_dir = tmp_path / "downloads"
    output_dir.mkdir()

    # Simulate yt-dlp creating a file
    def _side_effect(*args, **kwargs):
        (output_dir / "My Video.mp4").touch()

    mock_run.side_effect = _side_effect

    result = download_video("https://example.com/video", output_dir)

    mock_run.assert_called_once_with(
        ["yt-dlp", "-o", str(output_dir / "%(title)s.%(ext)s"), "https://example.com/video"],
        check=True,
        capture_output=True,
    )
    assert result == [output_dir / "My Video.mp4"]
