import pytest

from cir.chunking import chunk_text


@pytest.mark.parametrize("strategy", ["fixed", "paragraph", "clause"])
@pytest.mark.parametrize("overlap", [0, 40])
def test_offsets_reproduce_text_and_respect_size(corpus, strategy, overlap):
    for doc, text in corpus.items():
        chunks = chunk_text(doc, text, strategy, size=120, overlap=overlap, min_chunk=30)
        assert chunks
        for c in chunks:
            assert text[c.start:c.end] == c.text
            assert len(c.text) <= 120 + 1


@pytest.mark.parametrize("strategy", ["fixed", "paragraph", "clause"])
def test_no_overlap_means_full_coverage_of_non_blank_text(corpus, strategy):
    text = corpus["cuad/A.txt"]
    chunks = chunk_text("d", text, strategy, size=120, overlap=0, min_chunk=30)
    covered = set()
    for c in chunks:
        covered.update(range(c.start, c.end))
    missing = [i for i, ch in enumerate(text) if not ch.isspace() and i not in covered]
    assert missing == []


def test_fixed_does_not_split_words():
    text = "alpha beta gamma delta epsilon zeta eta theta " * 5
    for c in chunk_text("d", text, "fixed", size=30, overlap=0, min_chunk=0):
        assert not c.text.startswith("lpha")  # starts at a word boundary
        assert c.text.strip().split()[-1] in {"alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"}


def test_clause_splits_inline_enumerators():
    text = "The Supplier shall: (a) deliver the goods on time; (b) maintain insurance; (c) keep records of all deliveries made."
    para = chunk_text("d", text, "paragraph", size=45, overlap=0, min_chunk=10)
    clause = chunk_text("d", text, "clause", size=45, overlap=0, min_chunk=10)
    assert any(c.text.lstrip().startswith("(b)") for c in clause)
    assert len(clause) >= len(para)


def test_unknown_strategy():
    with pytest.raises(ValueError):
        chunk_text("d", "x", "nope", 10, 0, 1)
