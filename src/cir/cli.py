"""Command-line interface:  cir search | eval | loop | verify"""
from __future__ import annotations

import argparse
import sys
import textwrap

from .config import load_config
from .data import load_dataset, verify_offsets
from .evaluate import build_pipeline


def cmd_search(args) -> int:
    cfg = load_config(args.config)
    ds = load_dataset(args.data, all_docs=args.all_docs)
    pipe = build_pipeline(cfg, ds)
    res = pipe.search(args.query, k=args.k)
    if res.abstained:
        print(f"No relevant passage found (confidence {res.chunk_conf:.2f}"
              + (f", contract match {res.doc_conf:.2f}" if res.doc_conf is not None else "") + ").")
        if args.show_candidates:
            print("(candidates below the abstention threshold:)")
        else:
            return 0
    for h in res.hits[: args.k]:
        snippet = " ".join(h.text.split())
        print(f"#{h.rank}  score={h.score:.3f}  {h.doc}  [{h.start}:{h.end}]")
        print(textwrap.indent(textwrap.fill(snippet[: args.chars], 100), "    "))
    return 0


def cmd_eval(args) -> int:
    from . import evaluate
    sys.argv = ["cir eval", "--config", args.config, "--split", args.split, "--data", args.data] + (["--json", args.json] if args.json else [])
    evaluate.main()
    return 0


def cmd_loop(args) -> int:
    from . import loop
    sys.argv = ["cir loop", "--iters", str(args.iters), "--start", args.start, "--data", args.data]
    loop.main()
    return 0


def cmd_verify(args) -> int:
    ds = load_dataset(args.data)
    bad = verify_offsets(ds)
    print(f"{len(ds.answerable)} queries, {len(ds.corpus)} indexed contracts, {len(bad)} offset mismatches")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="cir", description="Contract clause search")
    ap.add_argument("--data", default="data/legalbench-rag")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="find the clauses that answer a question")
    s.add_argument("query")
    s.add_argument("--config", default="configs/final.yaml")
    s.add_argument("-k", type=int, default=5)
    s.add_argument("--chars", type=int, default=400, help="characters of each passage to print")
    s.add_argument("--all-docs", action="store_true", help="index all 462 CUAD contracts, not just the 29 in the mini benchmark")
    s.add_argument("--show-candidates", action="store_true", help="print ranked passages even when the system abstains")
    s.set_defaults(fn=cmd_search)
    e = sub.add_parser("eval", help="evaluate a config on train or test")
    e.add_argument("--config", default="configs/final.yaml")
    e.add_argument("--split", choices=["train", "test"], default="train")
    e.add_argument("--json")
    e.set_defaults(fn=cmd_eval)
    l = sub.add_parser("loop", help="run the self-improvement loop (train only)")
    l.add_argument("--iters", type=int, default=20)
    l.add_argument("--start", default="configs/baseline.yaml")
    l.set_defaults(fn=cmd_loop)
    v = sub.add_parser("verify", help="check document[start:end] == answer for every benchmark snippet")
    v.set_defaults(fn=cmd_verify)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
