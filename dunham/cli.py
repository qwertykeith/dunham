"""CLI entry point for Dunham — the montage supercut machine."""

import json
from pathlib import Path

import click

from dunham.download import download_video
from dunham.montage import create_montage
from dunham.search import search_transcripts
from dunham.transcribe import transcribe_folder


@click.group()
def cli():
    """Dunham — transcribe, search and montage audio/video files."""


@cli.command()
@click.argument("folder", type=click.Path(exists=True))
@click.option("--model", default="medium", help="Whisper model size.")
@click.option("--force", is_flag=True, help="Re-transcribe even if output exists.")
@click.option(
    "--transcripts-dir",
    default="data/transcripts",
    help="Directory to write transcript JSON files.",
)
def transcribe(folder: str, model: str, force: bool, transcripts_dir: str):
    """Transcribe all audio/video files in FOLDER."""
    created = transcribe_folder(
        Path(folder), Path(transcripts_dir), model_size=model, force=force
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
@click.argument("folder", type=click.Path(exists=True))
@click.argument("word")
@click.option(
    "--output",
    default="data/output/montage.mp4",
    help="Output path for the montage video.",
)
@click.option("--model", default="medium", help="Whisper model size.")
def run(folder: str, word: str, output: str, model: str):
    """Full pipeline: transcribe FOLDER, search for WORD, build montage."""
    transcripts_dir = Path("data/transcripts")

    click.echo("Step 1/3: Transcribing...")
    created = transcribe_folder(
        Path(folder), transcripts_dir, model_size=model
    )
    click.echo(f"  {len(created)} new transcript(s)")

    click.echo("Step 2/3: Searching...")
    hits = search_transcripts(word, transcripts_dir)
    click.echo(f"  {len(hits)} hit(s) found")

    if not hits:
        click.echo("No hits — nothing to montage.")
        return

    click.echo("Step 3/3: Building montage...")
    out = create_montage(hits, Path(folder), Path(output))
    click.echo(f"Done! Montage at {out}")
