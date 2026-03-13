"""CLI entry point for Dunham — the montage supercut machine."""

import json
import shutil
from pathlib import Path

import click

from dunham.download import download_video
from dunham.montage import create_montage
from dunham.search import search_transcript, search_transcripts
from dunham.transcribe import discover_videos, transcribe_folder


@click.group()
def cli():
    """Dunham — transcribe, search and montage audio/video files."""


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--model", default="medium", help="Whisper model size.")
@click.option("--force", is_flag=True, help="Re-transcribe even if output exists.")
@click.option(
    "--transcripts-dir",
    default="data/transcripts",
    help="Directory to write transcript JSON files.",
)
def transcribe(path: str, model: str, force: bool, transcripts_dir: str):
    """Transcribe audio/video file or folder at PATH."""
    created = transcribe_folder(
        Path(path), Path(transcripts_dir), model_size=model, force=force
    )
    click.echo(f"Transcribed {len(created)} file(s)")
    for p in created:
        click.echo(f"  {p}")


@cli.command()
@click.argument("word")
@click.option(
    "--transcripts-dir",
    default="data/transcripts",
    help="Directory containing transcript JSON files.",
)
@click.option(
    "--threshold",
    default=2,
    type=int,
    help="Levenshtein distance threshold for fuzzy matching.",
)
@click.option(
    "--output",
    default=None,
    help="Write hits JSON to file (prints to stdout if omitted).",
)
def search(word: str, transcripts_dir: str, threshold: int, output: str | None):
    """Search transcripts for WORD (fuzzy match)."""
    hits = search_transcripts(word, Path(transcripts_dir), threshold=threshold)
    click.echo(f"Found {len(hits)} hit(s)")

    payload = json.dumps(hits, indent=2, ensure_ascii=False)
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(payload)
        click.echo(f"Wrote hits to {output}")
    else:
        click.echo(payload)


@cli.command()
@click.argument("hits_json", type=click.Path(exists=True))
@click.option(
    "--output",
    default="data/output/montage.mp4",
    help="Output path for the montage video.",
)
@click.option(
    "--videos-dir",
    default="data/videos",
    help="Directory containing source video files.",
)
def montage(hits_json: str, output: str, videos_dir: str):
    """Create a montage video from HITS_JSON search results."""
    hits = json.loads(Path(hits_json).read_text())
    out = create_montage(hits, Path(videos_dir), Path(output))
    click.echo(f"Montage written to {out}")


@cli.command()
@click.argument("url")
@click.option(
    "--output-dir",
    default="data/videos",
    help="Directory to save downloaded videos.",
)
def download(url: str, output_dir: str):
    """Download a video from URL using yt-dlp."""
    files = download_video(url, Path(output_dir))
    click.echo(f"Downloaded {len(files)} file(s)")
    for f in files:
        click.echo(f"  {f}")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.argument("word")
@click.option(
    "--output",
    default="data/output/montage.mp4",
    help="Output path for the montage video.",
)
@click.option("--model", default="medium", help="Whisper model size.")
def run(path: str, word: str, output: str, model: str):
    """Full pipeline: transcribe PATH (file or folder), search for WORD, build montage.

    Processes each video incrementally — the montage is rebuilt after every
    video so there's always a usable output even if the process is interrupted.
    """
    input_path = Path(path)
    transcripts_dir = Path("data/transcripts")
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    videos_dir = input_path.parent if input_path.is_file() else input_path
    videos = [input_path] if input_path.is_file() else discover_videos(input_path)
    output_path = Path(output)
    clips_dir = output_path.parent / ".clips"

    all_hits: list[dict] = []

    try:
        for i, video in enumerate(videos, 1):
            click.echo(f"[{i}/{len(videos)}] {video.name}")

            # Transcribe (skips if already done)
            transcript_path = transcripts_dir / f"{video.stem}.json"
            created = transcribe_folder(video, transcripts_dir, model_size=model)
            if created:
                click.echo("  Transcribed")

            # Search its transcript
            if transcript_path.exists():
                hits = search_transcript(word, transcript_path)
                if hits:
                    click.echo(f"  {len(hits)} hit(s)")
                    all_hits.extend(hits)

                    # Rebuild montage incrementally
                    create_montage(all_hits, videos_dir, output_path, clips_dir=clips_dir)
                    click.echo(f"  Montage updated ({len(all_hits)} total clips)")
    finally:
        if clips_dir.exists():
            shutil.rmtree(clips_dir)

    if all_hits:
        click.echo(f"Done! Montage at {output_path} ({len(all_hits)} clips)")
    else:
        click.echo("No hits — nothing to montage.")
