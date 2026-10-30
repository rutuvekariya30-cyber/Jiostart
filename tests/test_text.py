from cir.text import decompose, expand_query, tokenize


def test_tokenize_stopwords_and_stemming():
    assert tokenize("The Assignments of the contracts") == ["assignments", "contracts"]
    assert tokenize("The Assignments of the contracts", stem=True) == ["assign", "contract"]
    assert "the" in tokenize("the", stopwords=False)


def test_decompose_benchmark_format():
    d, q = decompose("Consider the Service Agreement between A Ltd and B Inc.; What is the governing law for this contract?")
    assert d == "Service Agreement between A Ltd and B Inc."
    assert q == "What is the governing law for this contract?"


def test_decompose_free_text_falls_back():
    assert decompose("What is the governing law?") == ("", "What is the governing law?")


def test_expand_query_matches_lexicon_keys():
    assert "assign" in expand_query("Is there an anti-assignment clause in this contract?").split() or \
        "assignment" in expand_query("Is there an anti-assignment clause in this contract?").split()
    assert expand_query("What is the weather in Paris?") == ""
