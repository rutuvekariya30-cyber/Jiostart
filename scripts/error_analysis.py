"""List failures of a config on a split (default: train) grouped by diagnosis category."""
import argparse
import sys
from pathlib import Path

from cir.config import load_config
from cir.data import load_dataset
from cir.evaluate import build_pipeline, diagnose, diagnosis_counts, evaluate_split
from cir.text import decompose


def one_line(s, n=170):
    return " ".join(s.split())[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/final.yaml")
    ap.add_argument("--split", default="train")
    ap.add_argument("--per-cat", type=int, default=6)
    ap.add_argument("--out", default="experiments/error_analysis_train.md")
    args = ap.parse_args()
    cfg = load_config(args.config)
    ds = load_dataset()
    pipe = build_pipeline(cfg, ds)
    recs, m = evaluate_split(cfg, ds, args.split, pipe)
    d = diagnose(cfg, recs)
    lines = [f"# Error analysis: {args.config} on {args.split}", "", f"Counts (k=4): {diagnosis_counts(d)}", ""]
    for cat in ["false_abstention", "wrong_document", "right_doc_wrong_section", "partial_span", "missed_abstention"]:
        lines += [f"## {cat} ({len(d[cat])})", ""]
        for r in d[cat][: args.per_cat]:
            _, q = decompose(r.query)
            lines.append(f"- **Q:** {q}  (conf={r.chunk_conf:.2f}, doc_conf={r.doc_conf if r.doc_conf is None else round(r.doc_conf, 2)})")
            if r.answerable:
                doc, s, e = r.truth[0]
                text = ds.corpus[doc][s:e]
                lines.append(f"  - truth [{s}:{e}] ({e - s} chars): {one_line(text)}")
                if r.hits:
                    h = r.hits[0]
                    ht = ds.corpus[h[0]][h[1]:h[2]]
                    lines.append(f"  - top-1 [{h[1]}:{h[2]}] same_doc={h[0] == doc}: {one_line(ht)}")
                rank = next((i for i, h in enumerate(r.hits, 1) if h[0] == doc and h[1] < e and h[2] > s), None)
                lines.append(f"  - rank of first overlapping chunk: {rank}")
            else:
                lines.append(f"  - kind={r.kind}")
        lines.append("")
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
