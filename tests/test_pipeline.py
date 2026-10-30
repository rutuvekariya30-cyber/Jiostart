from cir.config import Config
from cir.evaluate import QueryRecord, diagnose, fit_abstention
from cir.pipeline import Pipeline, should_abstain


def test_finds_the_right_clause_with_exact_offsets(corpus, cfg):
    pipe = Pipeline(cfg, corpus)
    q = "Consider the Services Agreement between Acme Widgets Inc. and Beta Logistics LLC; Which state's law governs?"
    res = pipe.search(q)
    top = res.hits[0]
    assert top.doc == "cuad/A.txt"
    assert "State of New York" in corpus[top.doc][top.start:top.end]
    assert corpus[top.doc][top.start:top.end] == top.text


def test_document_routing_prefers_the_named_contract(corpus, cfg):
    pipe = Pipeline(cfg, corpus)
    res = pipe.search("Consider the License Agreement between Gamma Media Corp. and Delta Studios Ltd.; What is the governing law?")
    assert res.hits[0].doc == "cuad/B.txt"
    assert "England" in res.hits[0].text


def test_abstains_on_unrelated_question(corpus):
    cfg = Config(chunk_strategy="paragraph", chunk_size=300, min_chunk=40, abstain_chunk=0.3)
    pipe = Pipeline(cfg, corpus)
    assert pipe.search("What is the capital of Australia?").abstained
    assert not pipe.search("governing law of the agreement").abstained


def test_abstains_when_contract_is_not_indexed(corpus):
    cfg = Config(chunk_strategy="paragraph", chunk_size=300, min_chunk=40, decompose=True,
                 abstain_signal="chunk+doc", abstain_chunk=0.0, abstain_doc=0.2)
    pipe = Pipeline(cfg, corpus)
    assert not pipe.search("Consider the Services Agreement between Acme Widgets Inc. and Beta Logistics LLC; governing law?").abstained
    assert pipe.search("Consider the Lease between Zebra Holdings and Yak Foods; governing law?").abstained


def test_results_are_ranked_and_deduplicated(corpus):
    cfg = Config(chunk_strategy="fixed", chunk_size=150, chunk_overlap=100, dedupe_overlap=0.5)
    hits = Pipeline(cfg, corpus).search("governing law agreement", k=8).hits
    assert [h.rank for h in hits] == list(range(1, len(hits) + 1))
    assert all(hits[i].score >= hits[i + 1].score for i in range(len(hits) - 1))
    for i, a in enumerate(hits):
        for b in hits[i + 1:]:
            if a.doc == b.doc:
                inter = min(a.end, b.end) - max(a.start, b.start)
                assert inter <= 0 or inter / (b.end - b.start) < 0.5


def test_all_retrievers_run(corpus):
    for method in ("bm25", "char", "hybrid"):
        for fusion in ("wsum", "rrf"):
            cfg = Config(chunk_strategy="paragraph", chunk_size=300, min_chunk=40, method=method, fusion=fusion,
                         expansion="legal", stem=True)
            assert Pipeline(cfg, corpus).search("audit rights books records").hits


def test_expansion_does_not_change_abstention_confidence(corpus):
    base = Config(chunk_strategy="paragraph", chunk_size=300, min_chunk=40)
    exp = base.replace(expansion="legal")
    q = "Is there a cap on liability under this contract?"
    assert abs(Pipeline(base, corpus).search(q).chunk_conf - Pipeline(exp, corpus).search(q).chunk_conf) < 1e-9


def test_fit_abstention_separates_scores():
    cfg = Config()
    recs = [QueryRecord(f"a{i}", True, "answerable", 0.6 + 0.01 * i, None, []) for i in range(10)]
    recs += [QueryRecord(f"u{i}", False, "u", 0.1 + 0.01 * i, None, []) for i in range(10)]
    fitted = fit_abstention(cfg, recs)
    assert not should_abstain(fitted, 0.6, None) and should_abstain(fitted, 0.19, None)
    assert 0.19 < fitted.abstain_chunk <= 0.6


def test_diagnosis_categories():
    cfg = Config(abstain_chunk=0.5)

    def rec(conf, doc_hit, hit, recall):
        r = QueryRecord("q", True, "answerable", conf, None, [])
        r.doc_hit = {4: doc_hit}; r.hit = {4: hit}; r.R = {4: recall}
        return r

    d = diagnose(cfg, [rec(0.1, True, True, 1.0), rec(0.9, False, False, 0.0), rec(0.9, True, False, 0.0),
                       rec(0.9, True, True, 0.4), rec(0.9, True, True, 1.0)], k=4)
    assert [len(d[c]) for c in ("false_abstention", "wrong_document", "right_doc_wrong_section", "partial_span", "success")] == [1, 1, 1, 1, 1]
    u = QueryRecord("u", False, "off_topic", 0.9, None, [])
    assert len(diagnose(cfg, [u])["missed_abstention"]) == 1


def test_config_roundtrip_and_unknown_key(tmp_path):
    import pytest
    from cir.config import load_config, save_config
    c = Config(name="x", chunk_size=321)
    save_config(c, tmp_path / "c.yaml")
    assert load_config(tmp_path / "c.yaml") == c
    with pytest.raises(ValueError):
        Config.from_dict({"nope": 1})
