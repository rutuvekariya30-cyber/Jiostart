import pytest

from cir.metrics import merge, overlap_chars, precision_recall


def test_merge_overlapping_and_adjacent():
    assert merge([(5, 10), (0, 3), (3, 4), (8, 12)]) == [(0, 4), (5, 12)]
    assert merge([(2, 2), (5, 3)]) == []


def test_perfect_retrieval():
    p, r = precision_recall([("d", 10, 20)], [("d", 10, 20)])
    assert (p, r) == (1.0, 1.0)


def test_partial_overlap():
    p, r = precision_recall([("d", 0, 100)], [("d", 50, 70)])
    assert p == pytest.approx(0.2) and r == 1.0
    p, r = precision_recall([("d", 50, 60)], [("d", 50, 70)])
    assert p == 1.0 and r == pytest.approx(0.5)


def test_overlapping_retrieved_chunks_are_not_double_counted():
    p, r = precision_recall([("d", 0, 10), ("d", 5, 15)], [("d", 0, 15)])
    assert (p, r) == (1.0, 1.0)


def test_wrong_document_scores_zero():
    assert precision_recall([("x", 0, 10)], [("y", 0, 10)]) == (0.0, 0.0)
    assert overlap_chars([("x", 0, 10)], [("y", 0, 10)]) == 0


def test_empty_retrieval():
    assert precision_recall([], [("d", 0, 10)]) == (0.0, 0.0)


def test_multi_snippet_truth():
    p, r = precision_recall([("d", 0, 10), ("e", 0, 10)], [("d", 0, 10), ("e", 5, 15)])
    assert p == pytest.approx(15 / 20) and r == pytest.approx(15 / 20)
