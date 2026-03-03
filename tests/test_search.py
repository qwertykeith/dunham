"""Tests for the search module."""

from __future__ import annotations

import json
from pathlib import Path

from dunham.search import is_match, search_transcripts


# -- is_match unit tests --


def test_exact_case_insensitive_match():
    assert is_match("Dunham", "dunham", threshold=2)
    assert is_match("dunham", "DUNHAM", threshold=2)
    assert is_match("Hello", "hello", threshold=2)


def test_exact_match_rejects_unrelated():
    assert not is_match("Dunham", "Olivia", threshold=2)


def test_phonetic_match():
    """Words with the same metaphone code should match."""
    assert is_match("cat", "kat", threshold=0)  # Same phonetics, even with 0 threshold
    assert is_match("Dunham", "Dunhum", threshold=0)


def test_levenshtein_match_within_threshold():
    assert is_match("Dunham", "Dunnam", threshold=2)  # lev distance = 1
    assert is_match("Dunham", "Dunhom", threshold=2)  # lev distance = 1


def test_levenshtein_match_at_boundary():
    """Distance exactly equal to threshold should still match."""
    assert is_match("Dunham", "Dunxyz", threshold=3)  # lev = 3
    assert not is_match("Dunham", "Dunxyz", threshold=2)  # lev = 3, over threshold


def test_levenshtein_rejects_beyond_threshold():
    assert not is_match("Dunham", "xxxxxx", threshold=2)


# -- Clip padding tests --


def test_clip_padding(tmp_path: Path):
    """clip_start should be start - 0.3 (min 0), clip_end should be end + 0.3."""
    transcript = {
        "source": "test.mp4",
        "segments": [
            {
                "text": "Agent Dunham reporting",
                "words": [
                    {"word": "Agent", "start": 0.1, "end": 0.4},
                    {"word": "Dunham", "start": 0.5, "end": 0.9},
                    {"word": "reporting", "start": 1.0, "end": 1.5},
                ],
            }
        ],
    }
    _write_transcript(tmp_path, "test.json", transcript)

    results = search_transcripts("Dunham", tmp_path, threshold=2)
    assert len(results) == 1
    hit = results[0]
    assert hit["clip_start"] == round(0.5 - 0.3, 4)
    assert hit["clip_end"] == round(0.9 + 0.3, 4)


def test_clip_padding_clamps_to_zero(tmp_path: Path):
    """clip_start must not go below 0."""
    transcript = {
        "source": "test.mp4",
        "segments": [
            {
                "text": "Dunham here",
                "words": [
                    {"word": "Dunham", "start": 0.1, "end": 0.4},
                    {"word": "here", "start": 0.5, "end": 0.8},
                ],
            }
        ],
    }
    _write_transcript(tmp_path, "test.json", transcript)

    results = search_transcripts("Dunham", tmp_path, threshold=2)
    assert results[0]["clip_start"] == 0


# -- Phrase matching tests --


def test_phrase_matching(tmp_path: Path):
    """Consecutive words should be matched as a phrase."""
    transcript = {
        "source": "episode.mp4",
        "segments": [
            {
                "text": "Agent Dunham please report",
                "words": [
                    {"word": "Agent", "start": 1.0, "end": 1.3},
                    {"word": "Dunham", "start": 1.4, "end": 1.8},
                    {"word": "please", "start": 1.9, "end": 2.2},
                    {"word": "report", "start": 2.3, "end": 2.7},
                ],
            }
        ],
    }
    _write_transcript(tmp_path, "ep.json", transcript)

    results = search_transcripts("Agent Dunham", tmp_path, threshold=2)
    assert len(results) == 1
    assert results[0]["word"] == "Agent Dunham"
    assert results[0]["start"] == 1.0
    assert results[0]["end"] == 1.8


def test_phrase_no_match_when_not_consecutive(tmp_path: Path):
    """Non-adjacent words should not match a phrase query."""
    transcript = {
        "source": "episode.mp4",
        "segments": [
            {
                "text": "Agent hello Dunham",
                "words": [
                    {"word": "Agent", "start": 1.0, "end": 1.3},
                    {"word": "hello", "start": 1.4, "end": 1.7},
                    {"word": "Dunham", "start": 1.8, "end": 2.1},
                ],
            }
        ],
    }
    _write_transcript(tmp_path, "ep.json", transcript)

    results = search_transcripts("Agent Dunham", tmp_path, threshold=2)
    assert len(results) == 0


# -- Transcript loading tests --


def test_loads_multiple_transcript_files(tmp_path: Path):
    """Should search across all JSON files in the directory."""
    for i, name in enumerate(["a.json", "b.json"]):
        transcript = {
            "source": f"video_{i}.mp4",
            "segments": [
                {
                    "text": "Dunham",
                    "words": [
                        {"word": "Dunham", "start": float(i), "end": float(i) + 0.5}
                    ],
                }
            ],
        }
        _write_transcript(tmp_path, name, transcript)

    results = search_transcripts("Dunham", tmp_path, threshold=2)
    assert len(results) == 2
    sources = {r["source"] for r in results}
    assert sources == {"video_0.mp4", "video_1.mp4"}


def test_context_is_segment_text(tmp_path: Path):
    transcript = {
        "source": "test.mp4",
        "segments": [
            {
                "text": "Agent Dunham please",
                "words": [
                    {"word": "Agent", "start": 0.5, "end": 0.8},
                    {"word": "Dunham", "start": 0.9, "end": 1.2},
                    {"word": "please", "start": 1.3, "end": 1.6},
                ],
            }
        ],
    }
    _write_transcript(tmp_path, "test.json", transcript)

    results = search_transcripts("Dunham", tmp_path, threshold=2)
    assert results[0]["context"] == "Agent Dunham please"


def test_source_field_from_transcript(tmp_path: Path):
    transcript = {
        "source": "my_video.mp4",
        "segments": [
            {
                "text": "Dunham",
                "words": [{"word": "Dunham", "start": 0.0, "end": 0.5}],
            }
        ],
    }
    _write_transcript(tmp_path, "test.json", transcript)

    results = search_transcripts("Dunham", tmp_path, threshold=2)
    assert results[0]["source"] == "my_video.mp4"


def test_empty_query_returns_nothing(tmp_path: Path):
    transcript = {
        "source": "test.mp4",
        "segments": [
            {
                "text": "Dunham",
                "words": [{"word": "Dunham", "start": 0.0, "end": 0.5}],
            }
        ],
    }
    _write_transcript(tmp_path, "test.json", transcript)

    assert search_transcripts("", tmp_path) == []
    assert search_transcripts("   ", tmp_path) == []


def test_phonetic_match_in_transcript(tmp_path: Path):
    """Phonetic soundalikes should be found in full transcript search."""
    transcript = {
        "source": "test.mp4",
        "segments": [
            {
                "text": "Hello Dunhum",
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 0.3},
                    {"word": "Dunhum", "start": 0.4, "end": 0.8},
                ],
            }
        ],
    }
    _write_transcript(tmp_path, "test.json", transcript)

    results = search_transcripts("Dunham", tmp_path, threshold=0)
    assert len(results) == 1
    assert results[0]["word"] == "Dunhum"


def test_levenshtein_match_in_transcript(tmp_path: Path):
    """Levenshtein near-matches should be found even without phonetic match."""
    transcript = {
        "source": "test.mp4",
        "segments": [
            {
                "text": "Agent Dunnam reporting",
                "words": [
                    {"word": "Agent", "start": 0.0, "end": 0.3},
                    {"word": "Dunnam", "start": 0.4, "end": 0.8},
                    {"word": "reporting", "start": 0.9, "end": 1.3},
                ],
            }
        ],
    }
    _write_transcript(tmp_path, "test.json", transcript)

    # Dunnam vs Dunham: lev=1, metaphone differs — should match via lev
    results = search_transcripts("Dunham", tmp_path, threshold=2)
    assert len(results) == 1
    assert results[0]["word"] == "Dunnam"


# -- Helper --


def _write_transcript(directory: Path, filename: str, data: dict) -> Path:
    path = directory / filename
    path.write_text(json.dumps(data))
    return path
