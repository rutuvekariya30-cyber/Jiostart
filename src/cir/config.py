"""Pipeline configuration. Every pipeline choice lives here so the improvement loop can change it."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import yaml


@dataclass
class Config:
    name: str = "unnamed"

    # chunking: fixed | paragraph | clause
    chunk_strategy: str = "fixed"
    chunk_size: int = 500
    chunk_overlap: int = 0
    min_chunk: int = 80  # paragraph/clause: merge neighbours until at least this long

    # lexical analysis
    stopwords: bool = True
    stem: bool = False
    title_prefix: bool = False  # prepend the file title to every chunk's index text

    # BM25
    k1: float = 1.5
    b: float = 0.75

    # query processing
    decompose: bool = False  # split "Consider the <contract>; <question>" into descriptor + question
    boilerplate_df: float = 0.0  # drop query tokens in >= this fraction of train queries (0 = off)
    expansion: str = "none"  # none | legal
    expansion_weight: float = 0.5

    # retrieval: bm25 | char | hybrid
    method: str = "bm25"
    fusion: str = "wsum"  # wsum | rrf
    w_bm25: float = 1.0
    w_char: float = 1.0
    rrf_k: int = 60
    pool: int = 100

    # document routing (needs decompose)
    doc_boost: float = 0.0
    header_chars: int = 1500

    # post-processing
    top_k: int = 16
    dedupe_overlap: float = 0.5  # drop a hit if >= this fraction of it overlaps an already chosen hit (>1 = off)

    # abstention
    abstain_basis: str = "original"  # original | expanded: query terms behind the chunk confidence score
    abstain_signal: str = "chunk"  # chunk | chunk+doc
    abstain_chunk: float = 0.0  # abstain when normalised best-chunk BM25 is below this
    abstain_doc: float = 0.0  # ... or when normalised doc-routing score is below this (chunk+doc only)

    # -- helpers
    def index_key(self) -> str:
        """Hash of the fields that change the chunk index (used for caching)."""
        keys = ["chunk_strategy", "chunk_size", "chunk_overlap", "min_chunk", "stopwords", "stem", "title_prefix", "k1", "b"]
        blob = json.dumps({k: getattr(self, k) for k in keys}, sort_keys=True)
        return hashlib.sha1(blob.encode()).hexdigest()[:12]

    def key(self) -> str:
        d = asdict(self)
        d.pop("name")
        return hashlib.sha1(json.dumps(d, sort_keys=True).encode()).hexdigest()[:12]

    def replace(self, **kw) -> "Config":
        d = asdict(self)
        d.update(kw)
        return Config(**d)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Config":
        names = {f.name for f in fields(cls)}
        unknown = set(d) - names
        if unknown:
            raise ValueError(f"unknown config keys: {sorted(unknown)}")
        return cls(**d)


def load_config(path: str | Path) -> Config:
    return Config.from_dict(yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {})


def save_config(cfg: Config, path: str | Path) -> None:
    Path(path).write_text(yaml.safe_dump(cfg.to_dict(), sort_keys=False), encoding="utf-8")
