"""Clause search pipeline: chunk -> index -> (route, retrieve, fuse) -> rank -> abstain."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from .chunking import Chunk, chunk_text
from .config import Config
from .data import title_of
from .index import BM25, CharTfidf
from .text import decompose, expand_query, tokenize


@dataclass
class Hit:
    rank: int
    doc: str
    start: int
    end: int
    text: str
    score: float


@dataclass
class SearchResult:
    query: str
    hits: list[Hit]  # always the ranked candidates; callers should honour `abstained`
    abstained: bool
    chunk_conf: float  # normalised BM25 of the best chunk (0..1)
    doc_conf: float | None  # normalised doc-routing score, None when the query names no contract

    def passages(self) -> list[Hit]:
        return [] if self.abstained else self.hits


def should_abstain(cfg: Config, chunk_conf: float, doc_conf: float | None) -> bool:
    if chunk_conf < cfg.abstain_chunk:
        return True
    if cfg.abstain_signal == "chunk+doc" and doc_conf is not None and doc_conf < cfg.abstain_doc:
        return True
    return False


def fit_boilerplate(queries: list[str], cfg: Config) -> set[str]:
    """Tokens that occur in >= cfg.boilerplate_df of the given (train) questions carry no signal."""
    if cfg.boilerplate_df <= 0 or not queries:
        return set()
    df: Counter = Counter()
    for q in queries:
        _, question = decompose(q) if cfg.decompose else ("", q)
        df.update(set(tokenize(question, cfg.stopwords, cfg.stem)))
    return {t for t, c in df.items() if c / len(queries) >= cfg.boilerplate_df}


class Pipeline:
    def __init__(self, cfg: Config, corpus: dict[str, str], fit_queries: list[str] | None = None):
        self.cfg = cfg
        self.corpus = corpus
        self.chunks: list[Chunk] = []
        for doc, text in sorted(corpus.items()):
            self.chunks += chunk_text(doc, text, cfg.chunk_strategy, cfg.chunk_size, cfg.chunk_overlap, cfg.min_chunk)
        texts = [(title_of(c.doc) + " . " if cfg.title_prefix else "") + c.text for c in self.chunks]
        self.bm25 = BM25(texts, cfg.k1, cfg.b, cfg.stopwords, cfg.stem)
        self.char = CharTfidf([c.text for c in self.chunks]) if cfg.method in ("char", "hybrid") else None

        # document-level index for routing: title + header of each contract
        self.docs = sorted(corpus)
        headers = [title_of(d) + " . " + corpus[d][: cfg.header_chars] for d in self.docs]
        self.doc_bm25 = BM25(headers, cfg.k1, cfg.b, cfg.stopwords, cfg.stem)
        doc_pos = {d: i for i, d in enumerate(self.docs)}
        self.chunk_doc = np.array([doc_pos[c.doc] for c in self.chunks])

        self.boilerplate = fit_boilerplate(fit_queries or [], cfg)

    # -- query processing
    def _query_terms(self, question: str, expand: bool = True) -> dict[str, float]:
        cfg = self.cfg
        terms = {t: 1.0 for t in tokenize(question, cfg.stopwords, cfg.stem) if t not in self.boilerplate}
        if expand and cfg.expansion == "legal":
            for t in tokenize(expand_query(question), cfg.stopwords, cfg.stem):
                if t not in terms and t not in self.boilerplate:
                    terms[t] = cfg.expansion_weight
        return terms

    @staticmethod
    def _norm(s: np.ndarray) -> np.ndarray:
        m = s.max() if s.size else 0.0
        return s / m if m > 0 else s

    def _fuse(self, parts: list[tuple[float, np.ndarray]]) -> np.ndarray:
        cfg = self.cfg
        if cfg.fusion == "rrf":
            fused = np.zeros(len(self.chunks))
            for w, s in parts:
                top = np.argsort(-s)[: cfg.pool]
                top = top[s[top] > 0]
                fused[top] += w / (cfg.rrf_k + np.arange(1, len(top) + 1))
            return self._norm(fused)
        return self._norm(sum(w * self._norm(s) for w, s in parts))

    def search(self, query: str, k: int | None = None) -> SearchResult:
        cfg = self.cfg
        k = k or cfg.top_k
        desc, question = decompose(query) if cfg.decompose else ("", query)
        terms = self._query_terms(question)

        s_bm25 = self.bm25.score(terms)
        if cfg.abstain_basis == "original" and cfg.expansion != "none":
            # confidence must reflect what the user asked, not the synonyms we added
            o_terms = self._query_terms(question, expand=False)
            o_bound = self.bm25.upper_bound(o_terms)
            chunk_conf = float(self.bm25.score(o_terms).max() / o_bound) if o_bound > 0 else 0.0
        else:
            bound = self.bm25.upper_bound(terms)
            chunk_conf = float(s_bm25.max() / bound) if bound > 0 else 0.0

        parts: list[tuple[float, np.ndarray]] = []
        if cfg.method in ("bm25", "hybrid"):
            parts.append((cfg.w_bm25, s_bm25))
        if cfg.method in ("char", "hybrid"):
            q_text = question + " " + (expand_query(question) if cfg.expansion == "legal" else "")
            parts.append((cfg.w_char, self.char.score(q_text)))
        final = self._fuse(parts)

        doc_conf = None
        if desc:
            dterms = {t: 1.0 for t in tokenize(desc, cfg.stopwords, cfg.stem)}
            d_scores = self.doc_bm25.score(dterms)
            dbound = self.doc_bm25.upper_bound(dterms)
            doc_conf = float(d_scores.max() / dbound) if dbound > 0 else 0.0
            if cfg.doc_boost > 0:
                final = final + cfg.doc_boost * self._norm(d_scores)[self.chunk_doc]

        hits = self._select(final, k)
        return SearchResult(query, hits, should_abstain(cfg, chunk_conf, doc_conf), chunk_conf, doc_conf)

    def _select(self, final: np.ndarray, k: int) -> list[Hit]:
        order = np.argsort(-final, kind="stable")
        chosen: list[Chunk] = []
        out: list[Hit] = []
        for i in order:
            if final[i] <= 0 or len(out) >= k:
                break
            c = self.chunks[i]
            if self.cfg.dedupe_overlap <= 1.0 and self._overlaps(c, chosen):
                continue
            chosen.append(c)
            out.append(Hit(len(out) + 1, c.doc, c.start, c.end, c.text, float(final[i])))
        return out

    def _overlaps(self, c: Chunk, chosen: list[Chunk]) -> bool:
        for o in chosen:
            if o.doc != c.doc:
                continue
            inter = min(c.end, o.end) - max(c.start, o.start)
            if inter > 0 and inter / (c.end - c.start) >= self.cfg.dedupe_overlap:
                return True
        return False
