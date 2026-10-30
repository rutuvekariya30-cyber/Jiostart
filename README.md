# Contract clause search

## Overview

Given a natural-language question about a contract ("Who owns the IP in derivative works?", "When does the exclusivity period end?"), the system returns a **ranked list of passages** from the indexed contracts, each with its **source document and character offsets** (`document[start:end]` is exactly the passage). When no passage is relevant enough, or the question is about a contract that isn't indexed, it **returns nothing and says so**.

It is a purely lexical pipeline (BM25 + character n-gram TF-IDF, a contract-routing step and a calibrated abstention rule). **No LLM is used** (see `REPORT.md`). It has a Streamlit web app and a CLI, and it is evaluated on the CUAD portion of LegalBench-RAG-mini with a train/test split, a hand-written set of unanswerable queries, and a logged self-improvement loop.

Results and analysis are in [`REPORT.md`](REPORT.md); the iteration log is in [`experiments/LOG.md`](experiments/LOG.md).

## Setup

Python 3.10+ (developed on 3.13).

```bash
pip install -e ".[app,dev]"        # or: pip install -r requirements.txt && pip install -e .
python scripts/download_data.py    # ~33 MB: benchmarks/cuad.json + corpus/cuad -> data/legalbench-rag/
cir verify                         # sanity check: document[start:end] == answer for every snippet (expect 0 mismatches)
```

No API keys are needed: the pipeline is LLM-free. `huggingface_hub` downloads the data anonymously (set `HF_TOKEN` only if you hit rate limits).

## How to run

```bash
streamlit run src/cir/app.py                                   # web app
cir search "Consider the Service Agreement between BicycleTX Ltd and Nigel Crockett for Chief Business Officer Position; What is the governing law for this contract?" -k 3
cir search "What is the capital of Australia?"                 # -> "No relevant passage found"
cir eval --config configs/final.yaml --split train             # evaluation (use --split test only for final reporting)
cir loop --iters 20                                            # the self-improvement loop (train only)
python -m pytest                                               # tests
```

`cir search` / the app index the 29 contracts referenced by the 194 mini queries by default (`--all-docs` / a checkbox indexes all 462 CUAD contracts). Free-form questions work; the "Consider the \<contract\>; \<question\>" form additionally lets the system route to the named contract.

Other scripts: `scripts/make_unanswerable.py` (generated the unanswerable set once, before the loop), `scripts/error_analysis.py`, `scripts/make_results.py` (all tables in the report), `scripts/confidence_intervals.py`.

## Architecture

```
question ──► decompose ("Consider the <contract>; <question>") ──► descriptor, question
                                                                       │            │
                                              contract routing ◄───────┘            ├─► query terms (+ legal synonym expansion, stemming)
                                        (BM25 over title + header of each contract)  │
                                                      │                              ▼
chunks (fixed / paragraph / clause windows,  ──► BM25 + char-n-gram TF-IDF ──► weighted fusion ──► + doc boost ──► rank, de-duplicate ──► top-k passages
 exact [start:end] offsets)                                                                                          │
                                                                                                                      ▼
                                         abstain if best-chunk BM25 confidence < t_chunk  OR  contract match < t_doc  ──► "no relevant passage"
```

| Module (`src/cir/`) | Role |
|---|---|
| `config.py` | `Config` dataclass: **every pipeline choice** (chunking, analysers, BM25 params, query processing, retrieval method/fusion, routing, abstention). YAML in `configs/`. |
| `data.py` | Loads `cuad.json`, the authors' `mini()` selection, `assign_split`, the unanswerable set; `verify_offsets`. |
| `chunking.py` | `fixed`, `paragraph`, `clause` chunkers; chunks are `(start, end)` into the original text. |
| `text.py` | Tokeniser, stopwords, Porter stemming, query decomposition, legal synonym lexicon. |
| `index.py` | BM25 (precomputed sparse weight matrix) and char-n-gram TF-IDF. |
| `pipeline.py` | `Pipeline.search()` -> ranked `Hit`s + abstention decision. |
| `metrics.py` / `evaluate.py` | Character-level precision/recall, abstention metrics, failure diagnosis, threshold fitting. |
| `loop.py` | Self-improvement loop: diagnose -> propose -> accept/reject -> log. |
| `cli.py`, `app.py` | CLI and Streamlit app. |

Data flow for evaluation: `data.load_dataset` -> `evaluate.build_pipeline` (fits query-boilerplate statistics on **train** questions only) -> `run_queries` -> `aggregate` / `diagnose`. Abstention thresholds are fitted on train by `evaluate.fit_abstention` and stored in the YAML config.

Configuration lives in `configs/*.yaml`: `baseline.yaml` (simplest pipeline), `final.yaml` (output of the loop), `run1_final.yaml` (output of the first, flawed loop run, kept for the record).

## Reproducing results

From a fresh clone (timings measured on a 4-core container):

| Step | Command | Time |
|---|---|---|
| Install + download data | see Setup | ~1 min + ~12 s |
| Train metrics, baseline and final | `cir eval --config configs/baseline.yaml --split train` / `... final.yaml ...` | ~6 s each |
| Re-run the improvement loop (deterministic; reproduces `experiments/log.jsonl` and `configs/final.yaml`) | `cir loop --iters 20` | ~35 s |
| All tables in the report (train; add `--test` for test) | `python scripts/make_results.py [--test]` | ~30 s |
| Confidence intervals | `python scripts/confidence_intervals.py` | ~10 s |
| Error analysis (train) | `python scripts/error_analysis.py` | ~6 s |
| Tests | `python -m pytest` | ~2 s |

The loop is deterministic (fixed seed, no sampling); a re-run gives identical decisions and metrics. **Every evaluation of the test split is appended to `experiments/test_runs.jsonl`**, including the ones made by the scripts above, so running `--test` will add lines to it (the committed file records the 3 evaluations behind the report).

Note: `cir loop` overwrites `experiments/log.jsonl`, `experiments/LOG.md` and `configs/final.yaml`. `experiments/run1_*` and `configs/run1_final.yaml` are the first run, kept separately (see the report).

## Assumptions

1. **Mini subset and split** are computed exactly with the provided functions; I checked all 272 snippets of the 194 queries: `document[start:end] == answer` for every one (0 mismatches). That gives 140 train / 54 test answerable queries.
2. **Indexed corpus** = the 29 contracts referenced by the 194 queries (as the benchmark authors did), not all 462. Consequence: finding the right *document* is easy here (doc_hit@4 is 1.0 even for the baseline), so these numbers say little about routing among thousands of contracts.
3. **"k"** is the number of returned *passages* (chunks); precision/recall are character-level on the union of the top-k passages (overlapping passages are not double counted), averaged over queries, as in the LegalBench-RAG paper. Queries with several ground-truth snippets use their union.
4. **Abstention counts as an empty result.** Retrieval metrics (precision/recall@k) are computed on the ranked list *before* the abstention decision, so they measure ranking quality; `e2e_recall@k` additionally zeroes the recall of wrongly abstained queries. Abstention is reported separately in both directions.
5. **Query format.** Every benchmark query has the form "Consider the \<contract\>; \<question\>". `decompose()` exploits this (a regex) to route to the named contract. It falls back to treating the whole input as the question, so free-form questions still work, but the benefit is benchmark-specific, which the report states.
6. **Unanswerable queries** (40; 27 train / 13 test) were written before the loop and committed in the first commit, in four kinds: in-corpus contract + absent topic, contract not in the corpus, off-topic, and bare question on an absent topic. Topics were checked by regex to be absent from the relevant contracts (`scripts/make_unanswerable.py`); I dropped two bare queries whose topic *does* occur in the corpus. "Absent" means absent by keyword check, not by a legal expert's reading.
7. **Legal synonym lexicon** (`text.py`) was written from general contract knowledge after seeing the 32 question templates (inputs, not answers). Test questions use the same templates, so the test split does *not* measure generalisation to unseen question wording.
8. **Abstention thresholds** are fitted on train (including the 27 train unanswerable queries) with balanced accuracy as the objective, ties broken towards answering. The train abstention numbers are therefore in-sample.
9. **Sub-folds** inside train (3, hash-based) are used by the loop as a robustness check; the train/test split is untouched.
10. Character offsets assume Python's default text-mode UTF-8 reading (universal newlines); documents are read with `Path.read_text(encoding="utf-8")`.

## AI tool usage

This project was built with an **AI coding assistant** (an LLM-based command-line agent). It was used to: read the task brief and plan the work; write the code, tests and documentation; run the experiments; and draft the report from the measured numbers. The design decisions (lexical-only pipeline, abstention signals, loop accept rule, objective and guardrails) and the two corrections to my own first loop run (see the report) came out of that collaboration.

The pipeline itself does not call any AI model at inference or evaluation time. The legal synonym lexicon was written by the assistant from general legal knowledge, not learned from or tuned on the benchmark's answers.

Where a claim in the report is a hypothesis rather than something measured, it is labelled as such.
