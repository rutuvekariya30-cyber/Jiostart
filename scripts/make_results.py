"""Produce every number in REPORT.md: baseline vs final (train, and test with --test), abstention by kind, ablation.

The test split is only touched with --test (once per config); each use is appended to experiments/test_runs.jsonl.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from cir.config import load_config
from cir.data import load_dataset
from cir.evaluate import (abstained, aggregate, build_pipeline, diagnose, diagnosis_counts, evaluate_split, fit_abstention,
                          log_test_run, run_queries)

COLS = ["recall@1", "recall@4", "recall@8", "precision@1", "precision@4", "precision@8", "doc_hit@4", "hit@4", "mrr",
        "answer_rate", "correct_abstain_rate", "abstain_balanced_acc", "e2e_recall@4"]


def row(m):
    return " | ".join(f"{m[c]:.3f}" for c in COLS)


def by_kind(cfg, recs):
    d = defaultdict(list)
    for r in recs:
        if not r.answerable:
            d[r.kind].append(abstained(cfg, r))
    return {k: (sum(v), len(v)) for k, v in d.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--out", default="experiments/results.json")
    args = ap.parse_args()
    ds = load_dataset()
    base, final = load_config("configs/baseline.yaml"), load_config("configs/final.yaml")
    out, md = {}, []
    splits = ["train"] + (["test"] if args.test else [])
    md += ["| config | split | n_ans | n_unans | " + " | ".join(COLS) + " |", "|---|---|---|---|" + "---|" * len(COLS)]
    kinds = {}
    for name, cfg in [("baseline", base), ("final", final)]:
        for sp in splits:
            recs, m = evaluate_split(cfg, ds, sp)
            if sp == "test":
                log_test_run(f"configs/{name}.yaml", cfg.key())
            out[f"{name}/{sp}"] = {**m, "diagnosis@4": diagnosis_counts(diagnose(cfg, recs))}
            kinds[f"{name}/{sp}"] = by_kind(cfg, recs)
            md.append(f"| {name} | {sp} | {m['n_answerable']} | {m['n_unanswerable']} | {row(m)} |")
    md += ["", "Correct abstentions by kind (abstained / total):", "", "| config/split | " + " | ".join(sorted({k for v in kinds.values() for k in v})) + " |", "|---|---|---|---|---|"]
    allk = sorted({k for v in kinds.values() for k in v})
    for key, v in kinds.items():
        md.append(f"| {key} | " + " | ".join(f"{v.get(k, (0, 0))[0]}/{v.get(k, (0, 0))[1]}" for k in allk) + " |")

    # ablation on TRAIN: switch off one component of the final config at a time (thresholds re-fitted on train each time)
    ablations = {
        "final (all components)": {},
        "- query decomposition & doc routing": {"decompose": False, "doc_boost": 0.0, "abstain_signal": "chunk"},
        "- legal synonym expansion": {"expansion": "none"},
        "- stemming": {"stem": False},
        "- char n-gram retriever (BM25 only)": {"method": "bm25"},
        "- chunk overlap": {"chunk_overlap": 0},
        "- contract-match abstention signal": {"abstain_signal": "chunk"},
    }
    md += ["", "Ablation on train (one component removed from the final config; abstention thresholds re-fitted on train):", "",
           "| variant | recall@4 | precision@4 | doc_hit@4 | abstain bal. acc | e2e recall@4 |", "|---|---|---|---|---|---|"]
    a, u = ds.split("train")
    abl = {}
    for label, ch in ablations.items():
        cfg = final.replace(**ch)
        recs = run_queries(build_pipeline(cfg, ds), a, u)
        cfg = fit_abstention(cfg, recs)
        m = aggregate(cfg, recs)
        abl[label] = m
        md.append(f"| {label} | {m['recall@4']:.3f} | {m['precision@4']:.3f} | {m['doc_hit@4']:.3f} | {m['abstain_balanced_acc']:.3f} | {m['e2e_recall@4']:.3f} |")
    out["ablation_train"] = abl
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    Path(args.out).with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
