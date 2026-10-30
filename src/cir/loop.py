"""Self-improvement loop: evaluate on TRAIN -> diagnose failures -> propose one change -> accept/reject -> log.

    python -m cir.loop                      # defaults: start from configs/baseline.yaml, 15 iterations

The loop only ever sees the train split. Ground-truth spans are used for scoring and diagnosis (as the brief allows),
never as input to the pipeline at inference time.

Objective
    primary   : char-level recall@4 on answerable train queries
    guardrails: precision@4, abstention balanced accuracy, doc_hit@4 must not drop by more than a tolerance
Accept a candidate iff
    1. primary improves by >= MIN_DELTA overall, and
    2. it is >= the incumbent on the primary metric in at least 2 of the 3 train sub-folds, and
    3. no guardrail is worse than the incumbent by more than its tolerance;
  or (abstention-only path) primary is unchanged within a small slack, abstention balanced accuracy improves by
  >= ABSTAIN_MIN_GAIN and the other guardrails hold.
Abstention thresholds are re-fitted on train for every candidate (they are part of the pipeline, not a tuning knob
the loop could forget about).
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

import numpy as np

from .config import Config, load_config, save_config
from .data import Dataset, load_dataset, subfold
from .evaluate import (CATEGORIES, QueryRecord, aggregate, build_pipeline, diagnose, diagnosis_counts, fit_abstention,
                       run_queries)

PRIMARY = "recall@4"
MIN_DELTA = 0.005
GUARDRAILS = {"precision@4": 0.01, "abstain_balanced_acc": 0.03, "doc_hit@4": 0.02}
N_FOLDS = 3

SEARCH_SPACE: dict[str, list] = {
    "chunk_strategy": ["fixed", "paragraph", "clause"],
    "chunk_size": [200, 300, 400, 600, 800, 1000],
    "chunk_overlap": [0, 50, 100, 150],
    "stem": [True, False],
    "stopwords": [True, False],
    "k1": [0.9, 1.2, 1.5, 2.0],
    "b": [0.3, 0.5, 0.75, 0.9],
    "method": ["bm25", "char", "hybrid"],
    "fusion": ["wsum", "rrf"],
    "w_char": [0.3, 0.6, 1.0, 1.5],
    "doc_boost": [0.0, 0.5, 1.0, 2.0],
    "boilerplate_df": [0.0, 0.05, 0.1, 0.2, 0.4],
    "expansion": ["none", "legal"],
    "expansion_weight": [0.3, 0.5, 1.0],
    "dedupe_overlap": [0.3, 0.5, 2.0],
    "title_prefix": [True, False],
    "abstain_signal": ["chunk", "chunk+doc"],
}


# ---------------------------------------------------------------- evaluation of one candidate
def evaluate_candidate(cfg: Config, ds: Dataset) -> tuple[Config, dict, list[float], list[QueryRecord]]:
    pipe = build_pipeline(cfg, ds)
    a, u = ds.split("train")
    recs = run_queries(pipe, a, u)
    cfg = fit_abstention(cfg, recs)
    metrics = aggregate(cfg, recs)
    folds = []
    for f in range(N_FOLDS):
        sub = [r for r in recs if subfold(r.query, N_FOLDS) == f]
        folds.append(aggregate(cfg, sub)[PRIMARY])
    return cfg, metrics, folds, recs


# ---------------------------------------------------------------- diagnosis -> proposals
def header_dominance(recs: list[QueryRecord], limit: int = 1000) -> float:
    """Among failed answerable queries, fraction whose top-ranked hit lies in the first `limit` chars of its file."""
    failed = [r for r in recs if r.answerable and r.hits and not r.hit[4]]
    if not failed:
        return 0.0
    return float(np.mean([r.hits[0][1] < limit for r in failed]))


def rule_proposals(cfg: Config, recs: list[QueryRecord]) -> list[tuple[dict, str]]:
    """Ordered (change, rationale) pairs, chosen from the dominant failure causes."""
    d = diagnose(cfg, recs)
    c = diagnosis_counts(d)
    fails = {k: v for k, v in c.items() if k != "success"}
    total_fail = sum(fails.values()) or 1
    hd = header_dominance(recs)
    out: list[tuple[dict, str]] = []

    def add(change, why):
        out.append((change, why))

    if hd > 0.5 and not cfg.decompose:
        add({"decompose": True, "doc_boost": 1.0},
            f"{hd:.0%} of failed queries rank a header/signature chunk first: party names from the query's contract "
            "descriptor out-score the question words. Split descriptor from question; use the descriptor only to route to the document.")
    if c["right_doc_wrong_section"] + c["wrong_document"] > 0.35 * total_fail:
        if cfg.boilerplate_df == 0:
            add({"boilerplate_df": 0.1}, "Template words shared by many train questions add noise to scoring; drop tokens that occur in >=10% of train questions.")
        if cfg.expansion == "none":
            add({"expansion": "legal"}, "Right document, wrong section dominates: question wording rarely matches clause wording "
                 "('anti-assignment' vs 'shall not assign'). Expand with a legal synonym lexicon.")
        if not cfg.stem:
            add({"stem": True}, "Vocabulary mismatch (assign/assignment/assigned); stemming merges inflections.")
        if cfg.method == "bm25":
            add({"method": "hybrid"}, "Add character n-gram TF-IDF to BM25 to catch morphological variants and phrase fragments.")
        if cfg.chunk_strategy == "fixed":
            add({"chunk_strategy": "clause"}, "Fixed windows cut clauses in half; split on paragraph/clause boundaries so a chunk is one clause.")
    if c["partial_span"] > 0.15 * total_fail:
        if cfg.chunk_strategy == "fixed":
            add({"chunk_strategy": "paragraph"}, "Partial coverage: align chunk boundaries with paragraphs.")
        add({"chunk_size": 300 if cfg.chunk_size > 300 else 600},
            "Partial coverage: change chunk granularity (precision vs completeness of the retrieved clause).")
        add({"chunk_overlap": 100}, "Partial coverage: overlap neighbouring chunks so a clause split by a boundary is still retrieved whole.")
    if c["false_abstention"] + c["missed_abstention"] > 0.25 * total_fail and cfg.abstain_signal == "chunk":
        add({"abstain_signal": "chunk+doc"}, "Abstention errors: add a second signal (does the query's contract descriptor match any indexed contract?) "
             "to catch questions about contracts that are not in the corpus.")
    return out


def random_proposal(cfg: Config, rng: random.Random, tried: set[str]) -> tuple[dict, str] | None:
    for _ in range(200):
        n = rng.choice([1, 1, 2])
        keys = rng.sample(list(SEARCH_SPACE), n)
        change = {k: rng.choice(SEARCH_SPACE[k]) for k in keys}
        if "doc_boost" in change and change["doc_boost"] > 0 and not (cfg.decompose or "decompose" in change):
            change["decompose"] = True
        cand = cfg.replace(**change)
        if cand.key() != cfg.key() and cand.key() not in tried:
            return change, "Random search over the configuration space (no diagnosis-driven rule left to try)."
    return None


# ---------------------------------------------------------------- accept / reject
ABSTAIN_MIN_GAIN = 0.02
PRIMARY_SLACK = 0.002


def decide(best: dict, best_folds: list[float], cand: dict, cand_folds: list[float]) -> tuple[bool, str]:
    delta = cand[PRIMARY] - best[PRIMARY]
    if delta < MIN_DELTA:
        # secondary path: retrieval unchanged (within slack) but abstention clearly better, other guardrails intact
        gain = cand["abstain_balanced_acc"] - best["abstain_balanced_acc"]
        if delta >= -PRIMARY_SLACK and gain >= ABSTAIN_MIN_GAIN and all(
                cand[g] >= best[g] - tol for g, tol in GUARDRAILS.items() if g != "abstain_balanced_acc"):
            return True, f"abstention-only gain: balanced acc {gain:+.4f}, {PRIMARY} {delta:+.4f} within slack"
        return False, f"{PRIMARY} {delta:+.4f} < required {MIN_DELTA:+.3f}"
    wins = sum(c >= b - 1e-12 for c, b in zip(cand_folds, best_folds))
    if wins < 2:
        return False, f"improved on only {wins}/{N_FOLDS} sub-folds"
    for g, tol in GUARDRAILS.items():
        if cand[g] < best[g] - tol:
            return False, f"guardrail {g} dropped {cand[g] - best[g]:+.4f} (tolerance -{tol})"
    return True, f"{PRIMARY} {delta:+.4f}, >= incumbent on {wins}/{N_FOLDS} sub-folds, guardrails ok"


KEEP = ["recall@1", "recall@4", "recall@8", "precision@1", "precision@4", "doc_hit@4", "hit@4", "mrr",
        "answer_rate", "correct_abstain_rate", "abstain_balanced_acc", "e2e_recall@4"]


def run_loop(start: Config, ds: Dataset, iters: int, seed: int, log_path: Path, md_path: Path) -> Config:
    rng = random.Random(seed)
    log: list[dict] = []
    best_cfg, best_m, best_folds, best_recs = evaluate_candidate(start, ds)
    tried = {start.key(), best_cfg.key()}
    log.append({"iter": 0, "proposer": "-", "change": {}, "rationale": "baseline", "decision": "baseline", "reason": "",
                "metrics": {k: round(best_m[k], 4) for k in KEEP}, "folds": [round(x, 4) for x in best_folds],
                "diagnosis_before": diagnosis_counts(diagnose(best_cfg, best_recs)), "config_key": best_cfg.key()})
    print(f"iter 0  baseline  {PRIMARY}={best_m[PRIMARY]:.4f}")
    queue: list[tuple[dict, str, str]] = []
    for it in range(1, iters + 1):
        diag = diagnosis_counts(diagnose(best_cfg, best_recs))
        # refresh rule proposals from the incumbent's failures; keep the untried ones in priority order
        queue = [(ch, why, "rules") for ch, why in rule_proposals(best_cfg, best_recs)
                 if best_cfg.replace(**ch).key() not in tried]
        if queue:
            change, why, who = queue[0]
        else:
            r = random_proposal(best_cfg, rng, tried)
            if r is None:
                print("no untried proposals left; stopping")
                break
            (change, why), who = r, "random"
        cand_cfg = best_cfg.replace(**change, name=f"iter{it}")
        tried.add(best_cfg.replace(**change).key())
        cand_cfg, m, folds, recs = evaluate_candidate(cand_cfg, ds)
        tried.add(cand_cfg.key())
        ok, reason = decide(best_m, best_folds, m, folds)
        log.append({"iter": it, "proposer": who, "change": change, "rationale": why, "decision": "accepted" if ok else "rejected",
                    "reason": reason, "metrics": {k: round(m[k], 4) for k in KEEP}, "folds": [round(x, 4) for x in folds],
                    "diagnosis_before": diag, "config_key": cand_cfg.key()})
        print(f"iter {it:<2} {who:<6} {change}  {PRIMARY}={m[PRIMARY]:.4f}  -> {'ACCEPT' if ok else 'reject'} ({reason})")
        if ok:
            best_cfg, best_m, best_folds, best_recs = cand_cfg, m, folds, recs
    log_path.write_text("\n".join(json.dumps(r) for r in log) + "\n", encoding="utf-8")
    md_path.write_text(render_md(log), encoding="utf-8")
    return best_cfg


def render_md(log: list[dict]) -> str:
    lines = ["# Experiment log (train split only)", "",
             f"Primary: **{PRIMARY}** (min delta {MIN_DELTA}); guardrails: " + ", ".join(f"{g} (tol {t})" for g, t in GUARDRAILS.items()), "",
             "| iter | proposer | change | decision | recall@4 | precision@4 | doc_hit@4 | abst. bal. acc | reason |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in log:
        m = r["metrics"]
        ch = ", ".join(f"{k}={v}" for k, v in r["change"].items()) or "baseline"
        lines.append(f"| {r['iter']} | {r['proposer']} | {ch} | {r['decision']} | {m['recall@4']:.3f} | {m['precision@4']:.3f} | "
                     f"{m['doc_hit@4']:.3f} | {m['abstain_balanced_acc']:.3f} | {r['reason']} |")
    lines += ["", "## Why each change was tried", ""]
    for r in log[1:]:
        lines.append(f"- **iter {r['iter']}** ({r['proposer']}, {r['decision']}): {r['rationale']}  \n  failures before: {r['diagnosis_before']}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Run the self-improvement loop on the train split.")
    ap.add_argument("--start", default="configs/baseline.yaml")
    ap.add_argument("--iters", type=int, default=15)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--data", default="data/legalbench-rag")
    ap.add_argument("--out", default="configs/final.yaml")
    ap.add_argument("--log", default="experiments/log.jsonl")
    ap.add_argument("--md", default="experiments/LOG.md")
    args = ap.parse_args()
    ds = load_dataset(args.data)
    best = run_loop(load_config(args.start), ds, args.iters, args.seed, Path(args.log), Path(args.md))
    save_config(best.replace(name="final"), args.out)
    print(f"final config -> {args.out}\nlog -> {args.log}, {args.md}")


if __name__ == "__main__":
    main()
