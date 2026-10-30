"""Chunkers. Every chunk is (start, end) into the original text, so offsets are exact by construction."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    doc: str
    start: int
    end: int
    text: str


_PARA_BREAK = re.compile(r"\n[ \t]*\n+")
# a new numbered section / article / lettered sub-clause begins on its own line
_CLAUSE_START = re.compile(
    r"(?m)^[ \t]*(?:(?:article|section|clause)\s+[\dIVXivx]+[\.\):]?|\d+(?:\.\d+)*[\.\)]\s|\([a-zA-Z0-9]{1,4}\)\s|[A-Z][A-Z \-]{6,}\s*$)",
)


# inline enumerators / section numbers that follow a sentence end ("...; (b) ...", "... 12.3 Term. ...")
_INLINE_CLAUSE = re.compile(r"(?<=[;:.])[ \t]+(?=\([a-zA-Z0-9]{1,4}\)\s|\d{1,2}(?:\.\d{1,2})+\.?\s+[A-Z]|(?:Section|Article)\s+\d)")


def _snap_back(text: str, i: int, lo: int) -> int:
    """Move a cut point back to just after whitespace (but not before lo) so words aren't split."""
    j = i
    while j > lo and not text[j - 1].isspace():
        j -= 1
    return j if j > lo else i


def fixed_windows(text: str, start: int, end: int, size: int, overlap: int) -> list[tuple[int, int]]:
    spans = []
    pos = start
    step = max(1, size - overlap)
    while pos < end:
        stop = min(end, pos + size)
        if stop < end:
            stop = _snap_back(text, stop, pos + 1)
        spans.append((pos, stop))
        if stop >= end:
            break
        nxt = max(stop - overlap, pos + 1) if overlap else stop
        pos = nxt if nxt > pos else pos + step
    return spans


def _segments(text: str, strategy: str) -> list[tuple[int, int]]:
    """Natural segments (paragraphs, or paragraphs further split at clause headings)."""
    cuts = {0, len(text)}
    for m in _PARA_BREAK.finditer(text):
        cuts.add(m.end())
    if strategy == "clause":
        for m in _CLAUSE_START.finditer(text):
            cuts.add(m.start())
        for m in _INLINE_CLAUSE.finditer(text):
            cuts.add(m.end())
    pts = sorted(cuts)
    segs = [(a, b) for a, b in zip(pts, pts[1:]) if text[a:b].strip()]
    return segs


def chunk_text(doc: str, text: str, strategy: str, size: int, overlap: int, min_chunk: int) -> list[Chunk]:
    if strategy == "fixed":
        spans = fixed_windows(text, 0, len(text), size, overlap)
    elif strategy in ("paragraph", "clause"):
        spans = []
        cur_s = cur_e = None
        for a, b in _segments(text, strategy):
            if b - a > size:  # oversized segment: flush, then window it
                if cur_s is not None:
                    spans.append((cur_s, cur_e))
                    cur_s = cur_e = None
                spans.extend(fixed_windows(text, a, b, size, overlap))
                continue
            if cur_s is None:
                cur_s, cur_e = a, b
            elif (cur_e - cur_s) < min_chunk and (b - cur_s) <= size:
                cur_e = b  # too short: absorb the next segment
            else:
                spans.append((cur_s, cur_e))
                cur_s, cur_e = a, b
        if cur_s is not None:
            spans.append((cur_s, cur_e))
    else:
        raise ValueError(f"unknown chunk strategy {strategy!r}")
    return [Chunk(doc, a, b, text[a:b]) for a, b in spans if text[a:b].strip()]
