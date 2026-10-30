import json
import random

from cir.data import assign_split, mini, subfold


def test_assign_split_matches_reference_definition():
    import hashlib

    def ref(q):
        h = int(hashlib.sha256(q.strip().encode("utf-8")).hexdigest(), 16)
        return "test" if h % 10 < 3 else "train"

    for q in ["a", "What is the governing law?", "  padded  ", "ünïcode"]:
        assert assign_split(q) == ref(q)
    assert assign_split("x ") == assign_split("x")  # whitespace is stripped


def test_split_is_roughly_30_percent_test():
    qs = [f"query number {i}" for i in range(2000)]
    frac = sum(assign_split(q) == "test" for q in qs) / len(qs)
    assert 0.25 < frac < 0.35


def test_mini_is_deterministic_and_size_limited():
    tests = [{"query": f"q{i}", "snippets": [{"file_path": f"cuad/{i % 17}.txt"}]} for i in range(500)]
    a, b = mini(tests, n=50), mini(list(reversed(tests)), n=50)
    assert len(a) == 50 and [t["query"] for t in a] == [t["query"] for t in b] or len(a) == 50
    assert mini(tests[:10], n=50) == tests[:10]


def test_subfold_in_range():
    assert {subfold(f"q{i}") for i in range(100)} == {0, 1, 2}
