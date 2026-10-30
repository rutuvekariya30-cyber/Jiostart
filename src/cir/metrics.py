"""Character-level precision / recall as defined for LegalBench-RAG (averaged over queries)."""
from __future__ import annotations

from collections import defaultdict

Span = tuple[int, int]


def merge(spans: list[Span]) -> list[Span]:
    out: list[Span] = []
    for s, e in sorted(spans):
        if e <= s:
            continue
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def length(spans: list[Span]) -> int:
    return sum(e - s for s, e in spans)


def intersect_len(a: list[Span], b: list[Span]) -> int:
    """Total overlap between two lists of merged, sorted spans."""
    i = j = total = 0
    while i < len(a) and j < len(b):
        lo, hi = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if hi > lo:
            total += hi - lo
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return total


def group(spans: list[tuple[str, int, int]]) -> dict[str, list[Span]]:
    d: dict[str, list[Span]] = defaultdict(list)
    for doc, s, e in spans:
        d[doc].append((s, e))
    return {k: merge(v) for k, v in d.items()}


def precision_recall(retrieved: list[tuple[str, int, int]], truth: list[tuple[str, int, int]]) -> tuple[float, float]:
    """Character precision and recall of the union of retrieved spans against the union of truth spans."""
    r, t = group(retrieved), group(truth)
    n_ret = sum(length(v) for v in r.values())
    n_tru = sum(length(v) for v in t.values())
    inter = sum(intersect_len(r[d], t[d]) for d in r if d in t)
    precision = inter / n_ret if n_ret else 0.0
    recall = inter / n_tru if n_tru else 0.0
    return precision, recall


def overlap_chars(retrieved: list[tuple[str, int, int]], truth: list[tuple[str, int, int]]) -> int:
    r, t = group(retrieved), group(truth)
    return sum(intersect_len(r[d], t[d]) for d in r if d in t)
