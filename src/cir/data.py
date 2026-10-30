"""Loading LegalBench-RAG (CUAD), the mini subset, the train/test split and the unanswerable set."""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_ROOT = Path("data/legalbench-rag")
UNANSWERABLE_PATH = Path("data/unanswerable.jsonl")


def mini(tests: list[dict], n: int = 194) -> list[dict]:
    """The benchmark authors' selection of the mini subset (deterministic)."""
    if len(tests) <= n:
        return tests

    def key(t):
        random.seed(t["snippets"][0]["file_path"])
        return random.random()

    return sorted(tests, key=key)[:n]


def assign_split(query: str) -> str:
    h = int(hashlib.sha256(query.strip().encode("utf-8")).hexdigest(), 16)
    return "test" if h % 10 < 3 else "train"


def subfold(query: str, n: int = 3) -> int:
    """Sub-split inside train, used by the improvement loop for a robustness check."""
    h = int(hashlib.sha256(("fold|" + query.strip()).encode("utf-8")).hexdigest(), 16)
    return h % n


@dataclass
class Dataset:
    root: Path
    answerable: list[dict]  # benchmark tests (query + snippets)
    unanswerable: list[dict]  # {"query", "kind", ...}
    corpus: dict[str, str] = field(default_factory=dict)  # file_path -> text (only mini docs)

    def split(self, name: str) -> tuple[list[dict], list[dict]]:
        a = [t for t in self.answerable if assign_split(t["query"]) == name]
        u = [t for t in self.unanswerable if assign_split(t["query"]) == name]
        return a, u


def read_doc(root: Path, file_path: str) -> str:
    # Default text mode + UTF-8 is what the character offsets assume (universal newlines).
    return (Path(root) / "corpus" / file_path).read_text(encoding="utf-8")


def load_unanswerable(path: Path = UNANSWERABLE_PATH) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_dataset(root: str | Path = DEFAULT_ROOT, unanswerable_path: Path = UNANSWERABLE_PATH,
                 all_docs: bool = False) -> Dataset:
    root = Path(root)
    raw = (root / "benchmarks" / "cuad.json").read_text(encoding="utf-8")
    tests = mini(json.loads(raw)["tests"])
    files = sorted({s["file_path"] for t in tests for s in t["snippets"]})
    if all_docs:
        files = sorted(f"cuad/{p.name}" for p in (root / "corpus" / "cuad").glob("*.txt"))
    corpus = {f: read_doc(root, f) for f in files}
    return Dataset(root=root, answerable=tests, unanswerable=load_unanswerable(unanswerable_path), corpus=corpus)


def verify_offsets(ds: Dataset) -> list[tuple[str, str]]:
    """Return (query, file) for every snippet whose document[start:end] != answer."""
    bad = []
    for t in ds.answerable:
        for s in t["snippets"]:
            a, b = s["span"]
            if ds.corpus[s["file_path"]][a:b] != s["answer"]:
                bad.append((t["query"], s["file_path"]))
    return bad


def title_of(file_path: str) -> str:
    return Path(file_path).stem
