"""95% bootstrap CI for recall@4 and Wilson CIs for the abstention rates of the final config (train and test).

Reading the test split counts as an evaluation: each run appends to experiments/test_runs.jsonl.
"""
import math

import numpy as np

from cir.config import load_config
from cir.data import load_dataset
from cir.evaluate import abstained, build_pipeline, log_test_run, run_queries

cfg = load_config("configs/final.yaml")
ds = load_dataset()
pipe = build_pipeline(cfg, ds)
rng = np.random.default_rng(0)


def boot(x, n=5000):
    x = np.array(x)
    return np.percentile([rng.choice(x, len(x)).mean() for _ in range(n)], [2.5, 97.5])


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


for sp in ["train", "test"]:
    a, u = ds.split(sp)
    recs = run_queries(pipe, a, u)
    if sp == "test":
        log_test_run("configs/final.yaml (confidence intervals)", cfg.key())
    ans = [r for r in recs if r.answerable]
    una = [r for r in recs if not r.answerable]
    lo, hi = boot([r.R[4] for r in ans])
    print(f"{sp} recall@4 mean {np.mean([r.R[4] for r in ans]):.3f} 95% bootstrap CI [{lo:.3f}, {hi:.3f}] n={len(ans)}")
    k = sum(abstained(cfg, r) for r in una)
    print(f"  correct abstain {k}/{len(una)} Wilson95 [{wilson(k, len(una))[0]:.2f}, {wilson(k, len(una))[1]:.2f}]")
    k = sum(not abstained(cfg, r) for r in ans)
    print(f"  answered {k}/{len(ans)} Wilson95 [{wilson(k, len(ans))[0]:.2f}, {wilson(k, len(ans))[1]:.2f}]")
