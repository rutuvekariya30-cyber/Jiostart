from cir.loop import GUARDRAILS, MIN_DELTA, decide


def metrics(**kw):
    m = {"recall@4": 0.5, "precision@4": 0.1, "abstain_balanced_acc": 0.8, "doc_hit@4": 0.9}
    m.update(kw)
    return m


def test_accepts_clear_improvement():
    ok, _ = decide(metrics(), [0.5, 0.5, 0.5], metrics(**{"recall@4": 0.6}), [0.6, 0.6, 0.6])
    assert ok


def test_rejects_small_gain():
    ok, why = decide(metrics(), [0.5] * 3, metrics(**{"recall@4": 0.5 + MIN_DELTA / 2}), [0.51] * 3)
    assert not ok and "required" in why


def test_rejects_gain_on_one_fold_only():
    ok, why = decide(metrics(), [0.5] * 3, metrics(**{"recall@4": 0.6}), [0.9, 0.4, 0.4])
    assert not ok and "sub-folds" in why


def test_rejects_guardrail_violation():
    ok, why = decide(metrics(), [0.5] * 3, metrics(**{"recall@4": 0.7, "abstain_balanced_acc": 0.8 - GUARDRAILS["abstain_balanced_acc"] - 0.01}), [0.7] * 3)
    assert not ok and "guardrail" in why


def test_accepts_abstention_only_gain():
    ok, why = decide(metrics(), [0.5] * 3, metrics(**{"abstain_balanced_acc": 0.9}), [0.5] * 3)
    assert ok and "abstention-only" in why
    ok, _ = decide(metrics(), [0.5] * 3, metrics(**{"abstain_balanced_acc": 0.9, "recall@4": 0.45}), [0.45] * 3)
    assert not ok
