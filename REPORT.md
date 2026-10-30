# Evaluation report: contract clause search

## 1. Summary

I built a clause-search system over the CUAD contracts of LegalBench-RAG-mini (194 queries, 29 contracts). For a question it returns ranked passages with document and character offsets, or nothing when no passage is relevant enough. It is lexical only (BM25 + character n-gram TF-IDF, contract routing, calibrated abstention; **no LLM**). A logged, deterministic self-improvement loop (20 iterations on train) took it from a naive baseline to the final configuration.

**Headline test-set numbers** (54 answerable and 13 unanswerable test queries; final config, train-only tuning):

| | recall@4 | precision@4 | recall@8 | MRR | answers benchmark queries | refuses unanswerable queries |
|---|---|---|---|---|---|---|
| Baseline | 0.032 | 0.013 | 0.102 | 0.069 | 90.7% (49/54) | 69.2% (9/13) |
| **Final** | **0.642** (95% CI 0.53–0.76) | 0.152 | 0.772 | 0.680 | 92.6% (50/54) | 100% (13/13; 95% CI 77–100%) |

Train recall@4 is 0.687 vs test 0.642. The 0.045 gap is well inside the test set's sampling noise (CI width ±0.11 with n = 54), so I see no evidence of overfitting to train, but with these sample sizes I also can't rule out a modest one. **Important caveats up front** (details in section 8): every benchmark query names its contract and the test split reuses the train question templates, so the test numbers measure "new contracts, same question types", not unseen question wording; and the 13 unanswerable test queries are few and fairly easy.

The test split was evaluated **3 times** in total: baseline, final, and a repeat of the final config to compute confidence intervals (all logged in `experiments/test_runs.jsonl`). The final config was frozen before any test evaluation, and nothing was changed afterwards.

## 2. System design

```
chunk contracts -> BM25 + char-n-gram TF-IDF -> weighted fusion -> + contract-routing boost -> rank / de-duplicate -> top-k
                                                              abstain if best-chunk confidence or contract match is too low
```

Key decisions and the alternatives considered (all of them are config options; `configs/final.yaml` holds the chosen values):

| Decision | Chosen | Alternatives tried | Why / evidence |
|---|---|---|---|
| Chunking | fixed 500-char windows, 100 overlap, offsets exact by construction | paragraph, clause-aware (splits at headings and inline "(b)" / "12.3" enumerators), 300-char | Overlap +0.012 recall@4 (accepted). Paragraph/clause chunks give **higher precision@4 (0.21–0.22 vs 0.17)** but not higher recall@4, so the loop rejected them; see section 6. 300-char windows lose ≈0.10 recall@4. |
| Query handling | **split "Consider the \<contract\>; \<question\>"** into descriptor and question; use the question for passage scoring and the descriptor only to route to a contract | whole query as one bag of words (baseline) | The single biggest effect (section 5, ablation). The baseline's top hit was a header/signature chunk for 126 of 140 train queries, because party names in the descriptor out-scored the question. |
| Lexical analysis | stopwords, Porter stemming, BM25 (k1 1.5, b 0.75) | no stemming; other k1/b | Stemming +0.09 recall@4 at the time it was added. |
| Query expansion | small **legal synonym lexicon** (e.g. "anti-assignment" -> assign, consent, transfer) at half weight | none; boilerplate-token removal | +0.22 recall@4. Boilerplate removal (dropping question words common to many train questions) was tried 5 times: twice it cut recall@4 (−0.06, −0.04); the other three times it raised it (+0.014 to +0.058) but cost 0.12–0.14 abstention balanced accuracy, so the guardrail blocked it. *Hypothesis:* the template words both blur the ranking and carry the signal the abstention confidence relies on. |
| Retrieval | hybrid: BM25 + char-3..5-gram TF-IDF, weighted-sum fusion | BM25 only; reciprocal-rank fusion | +0.02 recall@4 (accepted on 2 of 3 sub-folds, a marginal call). |
| Abstention | refuse if (best-chunk BM25 / its upper bound) < 0.255 **or** (contract-descriptor match) < 0.316; thresholds fitted on train | chunk-confidence only | Chunk confidence alone cannot detect "question about a contract that isn't indexed"; the contract-match signal fixed that (balanced accuracy 0.80 -> 0.96 on train). |
| Confidence basis | computed from the **original** question words, not the expanded ones | expanded terms | Fixed after run 1 (section 6). |

No dense retriever or cross-encoder was built. That is an untested option, not a ruled-out one.

## 3. LLM use

**I did not use an LLM in the system.** Reasons: (1) the task is retrieval and the lexical pipeline already reaches recall@8 of 0.77; (2) contracts are confidential, so a hosted model would need a data-processing agreement that I can't assume, and a local model would be the only choice I'd make on real company agreements; (3) with limited time I preferred to measure a simple system rigorously. **I have not measured whether an LLM (query rewriting, reranking the top-16, or adding context to chunks) would beat this pipeline**, so I make no claim either way. It is the first stretch item I would test, with a local model, cached outputs, and the same train/test protocol. The remaining errors (section 7, causes A and B) are the kind a reranker might fix, but that is a hypothesis.

## 4. Evaluation setup

- **Data.** The 194 CUAD queries selected with the authors' `mini()` function; 29 contracts indexed. I verified `document[start:end] == answer` for all 272 snippets (0 mismatches). Split with the prescribed `assign_split`: **140 train / 54 test** answerable.
- **Unanswerable set.** 40 queries written and committed *before* the loop (first commit; unchanged since): 16 on an indexed contract about a topic it never mentions, 14 on contracts that are not indexed, 6 off-topic, 4 bare questions on absent topics. Topics were verified absent by regex against the contracts. Split with `assign_split`: **27 train / 13 test**. Test: 5 in-corpus, 4 not-in-corpus, 2 off-topic, 2 bare.
- **Retrieval metrics** (answerable queries): character-level precision and recall of the union of the top-k passages vs the union of ground-truth spans, averaged over queries, at k in {1, 2, 4, 8, 16}; also doc-hit@k, hit@k (any character overlap) and MRR. They are computed on the ranking *before* abstention; `e2e_recall` zeroes wrongly abstained queries.
- **Abstention metrics, both directions:** share of benchmark queries answered (1 − wrongly refused) and share of unanswerable queries refused (1 − wrongly answered); balanced accuracy is their mean.
- **Discipline.** All development and tuning on train; the loop sees train only (plus 3 hash-based sub-folds inside train). Ground-truth spans are used for scoring and diagnosis, never as pipeline input. Query-boilerplate statistics (an option the loop tried) are fitted on train questions only. Abstention thresholds are fitted on train.

## 5. Results

Baseline vs final, with the number of queries behind each figure (n_ans / n_unans):

| config | split | n_ans | n_unans | recall@1 | recall@4 | recall@8 | prec@1 | prec@4 | prec@8 | hit@4 | MRR | answered | refused | bal. acc | e2e recall@4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | train | 140 | 27 | 0.000 | 0.033 | 0.114 | 0.000 | 0.009 | 0.014 | 0.093 | 0.070 | 0.921 | 0.667 | 0.794 | 0.031 |
| baseline | test | 54 | 13 | 0.000 | 0.032 | 0.102 | 0.000 | 0.013 | 0.016 | 0.111 | 0.069 | 0.907 | 0.692 | 0.800 | 0.030 |
| **final** | train | 140 | 27 | 0.434 | 0.687 | 0.769 | 0.346 | 0.166 | 0.098 | 0.800 | 0.736 | 0.964 | 0.963 | 0.964 | 0.658 |
| **final** | test | 54 | 13 | 0.418 | 0.642 | 0.772 | 0.311 | 0.152 | 0.107 | 0.759 | 0.680 | 0.926 | 1.000 | 0.963 | 0.595 |

doc-hit@4 is 1.000 for every row: with 29 contracts and the contract named in every query, finding the document is trivial, so the benchmark does not test routing at scale.

95% intervals for the final config: recall@4 train [0.616, 0.755], test [0.528, 0.755] (bootstrap over queries); test answered 50/54 [0.82, 0.97]; test refused 13/13 [0.77, 1.00]; train refused 26/27 [0.82, 0.99] (Wilson).

**Correct refusals by kind** (refused / total):

| config / split | in-corpus, absent topic | contract not indexed | off-topic | bare absent topic |
|---|---|---|---|---|
| baseline train | 3/11 | 10/10 | 3/4 | 2/2 |
| baseline test | 1/5 | 4/4 | 2/2 | 2/2 |
| final train | 10/11 | 10/10 | 4/4 | 2/2 |
| final test | 5/5 | 4/4 | 2/2 | 2/2 |

The hard kind is "right contract, topic absent" (baseline refuses only 1 of 5 on test); the contract-match signal handles "contract not indexed" and the fitted chunk threshold handles most of the rest.

**Ablation on train** (one component removed from the final config, abstention thresholds re-fitted each time; these are in-sample comparisons, not independent evidence):

| variant | recall@4 | precision@4 | abstention bal. acc | e2e recall@4 |
|---|---|---|---|---|
| final (all components) | 0.687 | 0.166 | 0.964 | 0.658 |
| − query decomposition & contract routing | **0.128** | 0.033 | 0.848 | 0.116 |
| − legal synonym expansion | 0.493 | 0.119 | 0.964 | 0.472 |
| − stemming | 0.651 | 0.155 | 0.953 | 0.614 |
| − char n-gram retriever | 0.659 | 0.153 | 0.964 | 0.631 |
| − chunk overlap | 0.663 | 0.151 | 0.982 | 0.632 |
| − contract-match abstention signal | 0.687 | 0.166 | **0.797** | 0.658 |

Decomposition (≈0.56) and expansion (≈0.19) account for nearly all of the gain; stemming, the char retriever and overlap each add 0.02–0.04. Both big wins exploit the benchmark's query format and its limited set of question templates (section 8).

## 6. Iteration history

**Objective.** Primary: **character recall@4 on answerable train queries**. A reader sees a handful of passages, so "is the clause inside the first few results" is the question that matters; recall@1 is too harsh for multi-snippet queries and recall@16 hides ranking quality. **Guardrails** (must not worsen by more than the tolerance): precision@4 (−0.01), abstention balanced accuracy (−0.03), doc-hit@4 (−0.02): the three ways to "win" recall dishonestly are returning more text, answering everything, or losing the right contract.

**Loop** (`cir loop`, one command). Each iteration: (1) evaluate the incumbent on train and **diagnose** each query into success / false abstention / wrong document / right document-wrong section / partial span / missed abstention; (2) **propose one change**, either from rules keyed to the dominant failure cause (e.g. "most failed queries rank a header chunk first -> separate descriptor from question"; "right document, wrong section -> synonym expansion, stemming, hybrid"; "partial coverage -> chunking changes"), or, when the rules have nothing untried, by seeded random search over the config space; (3) re-fit abstention thresholds on train and evaluate; (4) **accept** iff recall@4 improves ≥ 0.005, the candidate is ≥ the incumbent on at least 2 of 3 train sub-folds, and no guardrail breaks; or, via a second path, recall@4 is unchanged (within 0.002) and abstention balanced accuracy improves ≥ 0.02 with the other guardrails intact; (5) log everything to `experiments/log.jsonl` / `LOG.md`.

**Two corrections to my own design, made after run 1 (both visible in the files).** Run 1 (`experiments/run1_LOG.md`) ended at train recall@4 0.497 and showed two problems:

1. It **rejected the legal-synonym expansion**, which on its own raises recall@4 to 0.647 (vs 0.497), because it dropped abstention balanced accuracy by 0.04–0.05. Cause: the confidence score divided by an upper bound that included the *added* synonym words, diluting it. Fix: compute confidence from the user's original words (`abstain_basis: original`). Proposed by me (assistant), not by the loop.
2. Its accept rule **could never accept abstention-only changes** (the `chunk+doc` candidate changed no retrieval result, so recall@4 stayed flat). Fix: the second acceptance path above. Also proposed by me.

Both were made after looking at *train* results only. Run 2 (the committed `LOG.md`) is the final run. Because I tuned the loop's own rules by reading train results, there is a mild researcher-degrees-of-freedom effect on train; test was untouched.

**Run 2 log** (train; recall@4 / precision@4 / abstention bal. acc; full table with reasons in `experiments/LOG.md`):

| iter | proposed by | change | outcome | recall@4 | prec@4 | bal. acc |
|---|---|---|---|---|---|---|
| 0 | | baseline | | 0.033 | 0.009 | 0.794 |
| 1 | rules | decompose + route to contract (boost 1.0) | **accepted** | 0.336 | 0.073 | 0.771 |
| 2 | rules | drop question tokens in ≥10% of train questions | rejected (−0.059) | 0.277 | 0.069 | 0.650 |
| 3 | rules | legal synonym expansion | **accepted** | 0.558 | 0.123 | 0.771 |
| 4 | rules | boilerplate removal (retry) | rejected (guardrail: bal. acc −0.12) | 0.616 | 0.135 | 0.650 |
| 5 | rules | stemming | **accepted** | 0.647 | 0.143 | 0.816 |
| 6 | rules | paragraph chunking | rejected (−0.013) | 0.634 | 0.189 | 0.778 |
| 7 | rules | 300-char chunks | rejected (−0.105) | 0.542 | 0.185 | 0.783 |
| 8 | rules | overlap 100 | **accepted** | 0.659 | 0.153 | 0.797 |
| 9 | rules | paragraph chunking (retry) | rejected (−0.020) | 0.639 | 0.194 | 0.782 |
| 10 | rules | 300-char chunks (retry) | rejected (−0.106) | 0.553 | 0.211 | 0.800 |
| 11 | random | expansion weight 0.3 | rejected (−0.026) | 0.633 | 0.143 | 0.797 |
| 12 | random | abstain on chunk **and** contract match | **accepted** (abstention-only, bal. acc +0.167) | 0.659 | 0.153 | 0.964 |
| 13 | rules | boilerplate removal (retry) | rejected (−0.038) | 0.621 | 0.147 | 0.825 |
| 14 | rules | hybrid BM25 + char n-grams | **accepted** (2 of 3 folds) | 0.681 | 0.163 | 0.964 |
| 15 | rules | boilerplate removal (retry) | rejected (guardrail: bal. acc −0.14) | 0.696 | 0.166 | 0.825 |
| 16 | rules | clause-aware chunking | rejected (+0.004 < 0.005) | 0.685 | 0.219 | 0.949 |
| 17 | rules | paragraph chunking (retry) | rejected (1 of 3 folds) | 0.687 | 0.214 | 0.949 |
| 18 | rules | 300-char chunks (retry) | rejected (−0.098) | 0.583 | 0.235 | 0.967 |
| 19 | random | char-retriever weight 1.5 | **accepted** (+0.006, 3 of 3 folds) | 0.687 | 0.166 | 0.964 |
| 20 | rules | boilerplate removal (retry) | rejected (guardrail: bal. acc −0.14) | 0.701 | 0.167 | 0.825 |

Observations: 7 of 20 changes were accepted, 13 rejected, and the rejected ones are informative. (a) Rules re-propose a rejected idea after the incumbent changes; boilerplate removal was retried five times: iterations 2 and 13 lowered recall; iterations 4, 15 and 20 raised it (+0.058, +0.015, +0.014) but broke abstention by −0.12 to −0.14, which the guardrail blocked. Whether that trade is right depends on how costly a missed abstention is; I did not revisit the guardrail after seeing it. (b) Iteration 12 came from the *random* proposer: my rule threshold for "abstention errors matter" (>25% of failures) never fired, so the loop found the largest abstention gain by luck. A better rule would have proposed it at iteration 1. (c) **Paragraph/clause chunking raise precision@4 by ≈0.05 at equal recall** (iterations 16–17) but were rejected because the primary metric is recall only. If users prefer reading less text, a different objective (e.g. an F-score at k = 4) would choose them; I kept the pre-declared objective rather than revise it after seeing results. (d) The accepted gains in iterations 14 and 19 (+0.021, +0.006) are small relative to the noise of a 140-query set. The 2-of-3 and 3-of-3 fold checks limit but do not remove the risk that they are noise.

## 7. Error analysis

Diagnosis of the final config on **train** at k = 4 (140 answerable + 27 unanswerable): 73 successes (recall ≥ 0.9), 5 false abstentions, 0 wrong document, 28 right document / wrong section, 34 partial span, and 1 missed abstention (the baseline had 2, 11, 0, 117, 10 and 9). I deliberately analysed train only; the complete listing is `experiments/error_analysis_train.md`. Causes below are my diagnosis from reading the text; items marked *hypothesis* are not tested.

| # | Query (contract type) | What happened | Cause |
|---|---|---|---|
| **A. Question words never appear in the answering clause (vocabulary gap)** | | | |
| 1 | Covenant not to sue (UK employment agreement) | Truth = clause on termination after group reconstruction; top-1 = a third-party-rights clause; first overlapping chunk at rank 13 | The truth passage shares no words with the question; the lexicon entry matches "sue"/"claim" but the clause says neither. *Hypothesis:* the annotation is a loose reading of the category. |
| 2 | Right of first refusal/offer/negotiation (same agreement) | Truth = a share-option grant; top-1 = confidentiality clause; no overlap in the top 16 | Same; this label does not read like an ROFR. *Hypothesis:* annotation noise. |
| 3 | Change of control (telecom agreement) | Truth = the term clause; top-1 = bankruptcy termination; overlap at rank 3; also falsely refused (conf 0.25) | The truth passage doesn't concern change of control on my reading. *Hypothesis:* annotation noise, in which case no retriever could fix this. |
| 4 | IP ownership assignment (UK employment agreement) | Truth = "you hereby assign ... all IPRs"; top-1 = litigation-assistance clause; first overlap rank 8 | *Likely:* the lexicon words (ownership, title, assign) also occur in neighbouring boilerplate and definitions that out-score the operative clause (not verified). |
| **B. Many similar sections in a long contract (distractors)** | | | |
| 5 | Terminable for convenience (executive agreement) | Truth = company may terminate "at any time ... immediately"; top-1 = garden leave; rank 8 | Garden leave, notice and termination sections all share "terminate/notice"; the operative sentence is short and uses "immediate effect", not "convenience". |
| 6 | Exceptions to competitive restrictions (UK service agreement) | Truth = "nothing in this paragraph shall prevent you from holding (shares)"; top-1 = the covenant itself; no overlap in the top 16 | Lexical match prefers the restriction over its carve-out; the carve-out's vocabulary is "shall not prevent", "holding". |
| 7 | Exceptions to competitive restrictions (software distribution) | Truth = "notify Rubicon ... software development work"; top-1 = adjacent non-solicit sentence; rank 9 | The neighbouring non-compete paragraph out-scores the exception. |
| 8 | Expiration date (Excite agreement) | Truth = "term ... will begin on the Launch Date and will not end until ..."; top-1 = payment-after-termination; rank 6 | The term is defined by an event, not a date; words like "expire/expiration" occur more densely in termination mechanics. |
| **C. Chunk boundary / partial coverage** | | | |
| 9 | Governing law (Nevada, 250 chars) | Rank-1 chunk covers 205 of the 250 truth characters (recall 0.82) plus an unrelated arbitration paragraph (precision ≈0.41) | A fixed 500-char window straddles the clause. |
| 10 | Cap on liability (indemnification agreement) | Rank-1 chunk starts 49 characters into the 203-character truth | Window starts mid-clause; the lead of the sentence is cut off. |
| 11 | Expiration date (software agreement) | Rank-1 chunk starts 93 characters before the term sentence but ends ≈87 characters short of its end | Same: the window cuts the end of the clause. |
| 12 | Licenses granted / exclusivity / non-transferable (3 queries, one shared clause) | Truth = the grant sentence; top-1 = next paragraph "This license is granted to ISA for ..."; first overlap at rank 2–4 | The following sentence repeats "license/granted" more densely than the grant sentence, and the grant is split across windows. |
| **D. False abstention** | | | |
| 13 | Non-solicitation of employees (2 queries, different contracts) | Top-1 is the right clause (rank 1 both times), but confidence 0.25 < threshold 0.2555 | The confidence is the best BM25 score divided by an upper bound over *all* question words; generic words ("clause", "preventing") dilute it. A correct answer scores just under a threshold fitted on 27 negatives. |
| 14 | Most-favoured-nation; uncapped liability | Same: right clause at rank 1–2, confidence 0.19 and 0.26 | Same dilution. The MFN clause says "terms more favorable", which the question words match only through the lexicon, which the confidence ignores by design. |
| **E. Missed abstention** | | | |
| 15 | "What happens to the parties' social media accounts after termination?" (indexed contract) | Answered, confidence 0.31, contract match 0.66 | BM25 sums matches of individual words ("social", "media", "accounts", "termination") that occur separately; there is no requirement that rare terms co-occur. |

Takeaways: A (4 cases) is dominated by the vocabulary gap and some label noise, B (4) is where a semantic reranker is most likely to help, C (4 cases but 34 train partial-span queries in total) is a chunking problem: boundary-aligned chunks help precision but didn't win under the recall objective, and D/E show the abstention rule is a single global threshold on a diluted confidence, which is fragile.

## 8. Limitations and next steps

What doesn't work or isn't established:
- **Benchmark-specific gains.** Decomposition exploits the "Consider the …; …" format, and the synonym lexicon was written after I had seen the 32 question templates. They account for most of the improvement (section 5), and the test split uses the same templates. A free-form question without a contract name gets no routing and (without a contract descriptor) no contract-match refusal. I have not measured performance on paraphrased questions.
- **Routing is untested at scale.** doc-hit@4 = 1.0 everywhere. With all 462 CUAD contracts, or thousands of agreements with similar titles and parties, routing by title and the first 1,500 characters may fail; I did not measure it.
- **Small samples.** 54 answerable and 13 unanswerable test queries. The test recall@4 interval is ±0.11 and the abstention intervals are wide (13/13 means ≥ 77% at 95%). The iteration-14 and iteration-19 gains are within noise.
- **Abstention is in-sample on train and fragile.** The threshold sits within 0.005 of confidence values of correct answers (error D), was fitted on 27 negatives, and train-set abstention numbers are optimistic. The unanswerable set is synthetic, checked by keyword, not by lawyers, and it is easier than real traffic (e.g. no near-miss questions such as "non-compete" when only "non-solicit" exists).
- **Low precision.** precision@4 is 0.15 because the median ground-truth span is ≈320 characters and chunks are 500; users read about 2,000 characters to find a clause.
- **Annotation noise.** Several failures (A1–A3) look like loose labels; I did not quantify it.
- **Not handled:** cross-references ("as defined in Section 4.2"), defined terms that change a word's meaning, amendments that override earlier text, tables, scanned layout. I implemented none of the stretch goals (LLM rewriting/reranking, dense retrieval, definition resolution), so nothing is claimed about them.
- Run-1 → run-2 loop-rule edits were informed by train results (section 6).

Before legal users rely on it:
1. Build a larger test set with **unseen phrasings** and an **expert-labelled unanswerable set that includes near misses**; evaluate on all CUAD contracts and on actual (redacted) agreements.
2. Replace the global confidence threshold with a calibrated abstention model (e.g. a local cross-encoder or small LLM judging "does this passage answer the question?"), evaluated with its own train/test split.
3. Test a local reranker on the top-16 (the remaining failures in B), and clause-aligned chunk boundaries with a precision-aware objective.
4. Resolve defined terms and cross-references at indexing time.
5. Show the passage in its surrounding context in the UI and make "no passage found" an explicit, auditable outcome; a lawyer should verify any clause before relying on it. This system finds candidate passages; it does not interpret contracts.
