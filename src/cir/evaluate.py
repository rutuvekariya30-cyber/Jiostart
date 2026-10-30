"""Evaluation: char-level retrieval metrics, abstention metrics, failure diagnosis, threshold fitting."""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .config import Config, load_config, save_config
from .data import Dataset, load_dataset
from .metrics import overlap_chars, precision_recall
from .pipeline import Pipeline, should_abstain

KS = (1, 2, 4, 8, 16)
TEST_RUNS_LOG = Path("experiments/test_runs.jsonl")


@dataclass
class QueryRecord:
    query: str
    answerable: bool
    kind: str
    chunk_conf: float
    doc_conf: float | None
    hits: list[tuple[str, int, int]]  # ranked (doc, start, end), before abstention
    truth: list[tuple[str, int, int]] = field(default_factory=list)
    P: dict[int, float] = field(default_factory=dict)
    R: dict[int, float] = field(default_factory=dict)
    doc_hit: dict[int, bool] = field(default_factory=dict)
    hit: dict[int, bool] = field(default_factory=dict)
    rr: float = 0.0


def run_queries(pipe: Pipeline, answerable: list[dict], unanswerable: list[dict]) -> list[QueryRecord]:
    recs = []
    for t in answerable:
        res = pipe.search(t["query"], k=max(KS))
        truth = [(s["file_path"], s["span"][0], s["span"][1]) for s in t["snippets"]]
        hits = [(h.doc, h.start, h.end) for h in res.hits]
        r = QueryRecord(t["query"], True, "answerable", res.chunk_conf, res.doc_conf, hits, truth)
        truth_docs = {d for d, _, _ in truth}
        for k in KS:
            top = hits[:k]
            r.P[k], r.R[k] = precision_recall(top, truth)
            r.doc_hit[k] = any(d in truth_docs for d, _, _ in top)
            r.hit[k] = overlap_chars(top, truth) > 0
        for rank, h in enumerate(hits, 1):
            if overlap_chars([h], truth) > 0:
                r.rr = 1.0 / rank
                break
        recs.append(r)
    for t in unanswerable:
        res = pipe.search(t["query"], k=max(KS))
        recs.append(QueryRecord(t["query"], False, t.get("kind", "unanswerable"), res.chunk_conf, res.doc_conf,
                                [(h.doc, h.start, h.end) for h in res.hits]))
    return recs


def abstained(cfg: Config, r: QueryRecord) -> bool:
    return should_abstain(cfg, r.chunk_conf, r.doc_conf)


def aggregate(cfg: Config, recs: list[QueryRecord]) -> dict[str, float]:
    ans = [r for r in recs if r.answerable]
    una = [r for r in recs if not r.answerable]
    m: dict[str, float] = {"n_answerable": len(ans), "n_unanswerable": len(una)}
    for k in KS:
        m[f"precision@{k}"] = float(np.mean([r.P[k] for r in ans])) if ans else float("nan")
        m[f"recall@{k}"] = float(np.mean([r.R[k] for r in ans])) if ans else float("nan")
        m[f"doc_hit@{k}"] = float(np.mean([r.doc_hit[k] for r in ans])) if ans else float("nan")
        m[f"hit@{k}"] = float(np.mean([r.hit[k] for r in ans])) if ans else float("nan")
    m["mrr"] = float(np.mean([r.rr for r in ans])) if ans else float("nan")
    # abstention, both directions
    accept_ans = [not abstained(cfg, r) for r in ans]
    reject_una = [abstained(cfg, r) for r in una]
    m["answer_rate"] = float(np.mean(accept_ans)) if ans else float("nan")  # answerable queries answered
    m["false_abstain_rate"] = 1.0 - m["answer_rate"] if ans else float("nan")  # benchmark queries wrongly refused
    m["correct_abstain_rate"] = float(np.mean(reject_una)) if una else float("nan")  # unanswerable refused
    m["missed_abstain_rate"] = 1.0 - m["correct_abstain_rate"] if una else float("nan")
    if ans and una:
        m["abstain_balanced_acc"] = 0.5 * (m["answer_rate"] + m["correct_abstain_rate"])
    else:
        m["abstain_balanced_acc"] = float("nan")
    # end-to-end: a wrongly abstained query gets zero precision/recall
    for k in (4, 8):
        m[f"e2e_recall@{k}"] = float(np.mean([r.R[k] if a else 0.0 for r, a in zip(ans, accept_ans)])) if ans else float("nan")
    return m


# -- abstention threshold fitting (train only)
def fit_abstention(cfg: Config, recs: list[QueryRecord]) -> Config:
    """Choose abstention thresholds maximising balanced accuracy on the given records.

    Ties are broken towards the lowest thresholds (prefer answering over refusing).
    """
    ans = [r for r in recs if r.answerable]
    una = [r for r in recs if not r.answerable]
    if not ans or not una:
        return cfg
    c_ans = np.array([r.chunk_conf for r in ans]); c_una = np.array([r.chunk_conf for r in una])
    grid_c = np.unique(np.concatenate([[0.0], np.quantile(np.concatenate([c_ans, c_una]), np.linspace(0, 1, 60))]))
    use_doc = cfg.abstain_signal == "chunk+doc"
    if use_doc:
        d_ans = np.array([r.doc_conf if r.doc_conf is not None else 1.0 for r in ans])
        d_una = np.array([r.doc_conf if r.doc_conf is not None else 1.0 for r in una])
        grid_d = np.unique(np.concatenate([[0.0], np.quantile(np.concatenate([d_ans, d_una]), np.linspace(0, 1, 60))]))
    else:
        d_ans = d_una = None
        grid_d = np.array([0.0])
    best = (-1.0, 0.0, 0.0)
    eps = 1e-9
    for tc in grid_c:
        for td in grid_d:
            acc = c_ans >= tc - eps
            rej = c_una < tc - eps
            if use_doc:
                acc &= d_ans >= td - eps
                rej |= d_una < td - eps
            bal = 0.5 * (acc.mean() + rej.mean())
            if bal > best[0] + 1e-12:
                best = (bal, float(tc), float(td))
    # thresholds sit on observed scores; nudge slightly below so that score == threshold is accepted
    return cfg.replace(abstain_chunk=round(max(best[1] - 1e-6, 0.0), 6), abstain_doc=round(max(best[2] - 1e-6, 0.0), 6))


# -- failure diagnosis
CATEGORIES = ["success", "false_abstention", "wrong_document", "right_doc_wrong_section", "partial_span", "missed_abstention"]


def diagnose(cfg: Config, recs: list[QueryRecord], k: int = 4, full_recall: float = 0.9) -> dict[str, list[QueryRecord]]:
    out: dict[str, list[QueryRecord]] = {c: [] for c in CATEGORIES}
    for r in recs:
        if not r.answerable:
            if not abstained(cfg, r):
                out["missed_abstention"].append(r)
            continue
        if abstained(cfg, r):
            out["false_abstention"].append(r)
        elif not r.doc_hit[k]:
            out["wrong_document"].append(r)
        elif not r.hit[k]:
            out["right_doc_wrong_section"].append(r)
        elif r.R[k] < full_recall:
            out["partial_span"].append(r)
        else:
            out["success"].append(r)
    return out


def diagnosis_counts(d: dict[str, list[QueryRecord]]) -> dict[str, int]:
    return {c: len(v) for c, v in d.items()}


# -- plumbing
def build_pipeline(cfg: Config, ds: Dataset) -> Pipeline:
    """Boilerplate statistics are fitted on TRAIN benchmark queries only."""
    train_q = [t["query"] for t in ds.split("train")[0]]
    return Pipeline(cfg, ds.corpus, fit_queries=train_q)


def evaluate_split(cfg: Config, ds: Dataset, split: str, pipe: Pipeline | None = None):
    pipe = pipe or build_pipeline(cfg, ds)
    a, u = ds.split(split)
    recs = run_queries(pipe, a, u)
    return recs, aggregate(cfg, recs)


def _fmt(m: dict) -> str:
    keys = ["precision@1", "precision@4", "recall@1", "recall@4", "recall@8", "doc_hit@4", "hit@4", "mrr",
            "answer_rate", "correct_abstain_rate", "abstain_balanced_acc", "e2e_recall@4"]
    return "  ".join(f"{k}={m[k]:.3f}" for k in keys)


def main():
    ap = argparse.ArgumentParser(description="Evaluate a pipeline config on the train or test split.")
    ap.add_argument("--config", required=True)
    ap.add_argument("--split", choices=["train", "test"], default="train")
    ap.add_argument("--fit-abstention", action="store_true", help="fit abstention thresholds on train and write them back into the config")
    ap.add_argument("--json", help="write metrics to this path")
    ap.add_argument("--data", default="data/legalbench-rag")
    args = ap.parse_args()
    cfg = load_config(args.config)
    ds = load_dataset(args.data)
    if args.fit_abstention:
        recs, _ = evaluate_split(cfg, ds, "train")
        cfg = fit_abstention(cfg, recs)
        save_config(cfg, args.config)
        print(f"fitted abstention on train: chunk={cfg.abstain_chunk} doc={cfg.abstain_doc} -> {args.config}")
    recs, m = evaluate_split(cfg, ds, args.split)
    print(f"[{cfg.name}] split={args.split} n_answerable={m['n_answerable']} n_unanswerable={m['n_unanswerable']}")
    print(_fmt(m))
    d = diagnose(cfg, recs)
    print("diagnosis (k=4):", diagnosis_counts(d))
    if args.json:
        Path(args.json).write_text(json.dumps(m, indent=2), encoding="utf-8")
    if args.split == "test":  # count every look at the test set
        TEST_RUNS_LOG.parent.mkdir(exist_ok=True)
        with TEST_RUNS_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "config": args.config, "config_key": cfg.key()}) + "\n")
        n = sum(1 for _ in TEST_RUNS_LOG.open(encoding="utf-8"))
        print(f"(test split evaluated {n} time(s) so far; logged in {TEST_RUNS_LOG})")


if __name__ == "__main__":
    main()
