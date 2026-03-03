"""Search transcripts for words and phrases using fuzzy matching."""

from __future__ import annotations

import json
from pathlib import Path

import jellyfish


def is_match(query_word: str, candidate: str, threshold: int) -> bool:
    """Check whether candidate matches query_word via exact, phonetic, or edit distance."""
    q = query_word.lower()
    c = candidate.lower()

    # Exact case-insensitive match
    if q == c:
        return True

    # Metaphone phonetic match
    if jellyfish.metaphone(q) == jellyfish.metaphone(c):
        return True

    # Levenshtein distance within threshold
    if jellyfish.levenshtein_distance(q, c) <= threshold:
        return True

    return False


def _find_single_word_hits(
    query_word: str, words: list[dict], threshold: int
) -> list[int]:
    """Return indices of words that match a single query term."""
    return [
        i
        for i, w in enumerate(words)
        if is_match(query_word, w["word"], threshold)
    ]


def _find_phrase_hits(
    query_words: list[str], words: list[dict], threshold: int
) -> list[tuple[int, int]]:
    """Return (start_idx, end_idx) pairs for consecutive word matches of a phrase."""
    if not query_words:
        return []

    phrase_len = len(query_words)
    hits: list[tuple[int, int]] = []

    for i in range(len(words) - phrase_len + 1):
        if all(
            is_match(query_words[j], words[i + j]["word"], threshold)
            for j in range(phrase_len)
        ):
            hits.append((i, i + phrase_len - 1))

    return hits


def _build_result(
    source: str,
    words: list[dict],
    start_idx: int,
    end_idx: int,
    segment_text: str,
) -> dict:
    """Build a search result dict with clip padding."""
    first = words[start_idx]
    last = words[end_idx]
    matched = " ".join(words[i]["word"] for i in range(start_idx, end_idx + 1))

    return {
        "source": source,
        "word": matched,
        "start": first["start"],
        "end": last["end"],
        "clip_start": round(max(0, first["start"] - 0.3), 4),
        "clip_end": round(last["end"] + 0.3, 4),
        "context": segment_text,
    }


def search_transcripts(
    query: str,
    transcripts_dir: Path,
    threshold: int = 2,
) -> list[dict]:
    """Search all transcript JSON files for a word or phrase.

    Returns a list of hit dicts with source, matched word, timestamps,
    padded clip bounds, and surrounding context.
    """
    query_words = query.strip().split()
    if not query_words:
        return []

    results: list[dict] = []

    for transcript_path in sorted(transcripts_dir.glob("*.json")):
        with open(transcript_path) as f:
            transcript = json.load(f)

        source = transcript.get("source", transcript_path.stem)

        for segment in transcript.get("segments", []):
            words = segment.get("words", [])
            if not words:
                continue

            segment_text = segment.get("text", "").strip()

            if len(query_words) == 1:
                # Single-word search
                for idx in _find_single_word_hits(query_words[0], words, threshold):
                    results.append(
                        _build_result(source, words, idx, idx, segment_text)
                    )
            else:
                # Phrase search — consecutive matching words
                for start_idx, end_idx in _find_phrase_hits(
                    query_words, words, threshold
                ):
                    results.append(
                        _build_result(source, words, start_idx, end_idx, segment_text)
                    )

    return results
