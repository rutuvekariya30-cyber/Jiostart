# Experiment log (train split only)

Primary: **recall@4** (min delta 0.005); guardrails: precision@4 (tol 0.01), abstain_balanced_acc (tol 0.03), doc_hit@4 (tol 0.02)

| iter | proposer | change | decision | recall@4 | precision@4 | doc_hit@4 | abst. bal. acc | reason |
|---|---|---|---|---|---|---|---|---|
| 0 | - | baseline | baseline | 0.033 | 0.009 | 1.000 | 0.794 |  |
| 1 | rules | decompose=True, doc_boost=1.0 | accepted | 0.336 | 0.073 | 1.000 | 0.771 | recall@4 +0.3030, >= incumbent on 3/3 sub-folds, guardrails ok |
| 2 | rules | boilerplate_df=0.1 | rejected | 0.277 | 0.069 | 1.000 | 0.650 | recall@4 -0.0592 < required +0.005 |
| 3 | rules | expansion=legal | rejected | 0.558 | 0.123 | 1.000 | 0.719 | guardrail abstain_balanced_acc dropped -0.0520 (tolerance -0.03) |
| 4 | rules | stem=True | accepted | 0.497 | 0.106 | 1.000 | 0.816 | recall@4 +0.1615, >= incumbent on 3/3 sub-folds, guardrails ok |
| 5 | rules | boilerplate_df=0.1 | rejected | 0.301 | 0.081 | 1.000 | 0.677 | recall@4 -0.1960 < required +0.005 |
| 6 | rules | expansion=legal | rejected | 0.647 | 0.143 | 1.000 | 0.775 | guardrail abstain_balanced_acc dropped -0.0399 (tolerance -0.03) |
| 7 | rules | method=hybrid | rejected | 0.496 | 0.109 | 1.000 | 0.816 | recall@4 -0.0009 < required +0.005 |
| 8 | rules | chunk_strategy=clause | rejected | 0.479 | 0.152 | 1.000 | 0.781 | recall@4 -0.0187 < required +0.005 |
| 9 | rules | chunk_strategy=paragraph | rejected | 0.490 | 0.146 | 1.000 | 0.778 | recall@4 -0.0077 < required +0.005 |
| 10 | rules | chunk_size=300 | rejected | 0.381 | 0.131 | 1.000 | 0.783 | recall@4 -0.1169 < required +0.005 |
| 11 | rules | chunk_overlap=100 | rejected | 0.499 | 0.114 | 1.000 | 0.797 | recall@4 +0.0015 < required +0.005 |
| 12 | random | expansion_weight=0.3 | rejected | 0.497 | 0.106 | 1.000 | 0.816 | recall@4 +0.0000 < required +0.005 |
| 13 | random | abstain_signal=chunk+doc | rejected | 0.497 | 0.106 | 1.000 | 0.982 | recall@4 +0.0000 < required +0.005 |
| 14 | random | w_char=1.5 | rejected | 0.497 | 0.106 | 1.000 | 0.816 | recall@4 +0.0000 < required +0.005 |
| 15 | random | b=0.5 | rejected | 0.497 | 0.106 | 1.000 | 0.816 | recall@4 +0.0000 < required +0.005 |

## Why each change was tried

- **iter 1** (rules, accepted): 90% of failed queries rank a header/signature chunk first: party names from the query's contract descriptor out-score the question words. Split descriptor from question; use the descriptor only to route to the document.  
  failures before: {'success': 2, 'false_abstention': 11, 'wrong_document': 0, 'right_doc_wrong_section': 117, 'partial_span': 10, 'missed_abstention': 9}
- **iter 2** (rules, rejected): Template words shared by many train questions add noise to scoring; drop tokens that occur in >=10% of train questions.  
  failures before: {'success': 34, 'false_abstention': 7, 'wrong_document': 0, 'right_doc_wrong_section': 70, 'partial_span': 29, 'missed_abstention': 11}
- **iter 3** (rules, rejected): Right document, wrong section dominates: question wording rarely matches clause wording ('anti-assignment' vs 'shall not assign'). Expand with a legal synonym lexicon.  
  failures before: {'success': 34, 'false_abstention': 7, 'wrong_document': 0, 'right_doc_wrong_section': 70, 'partial_span': 29, 'missed_abstention': 11}
- **iter 4** (rules, accepted): Vocabulary mismatch (assign/assignment/assigned); stemming merges inflections.  
  failures before: {'success': 34, 'false_abstention': 7, 'wrong_document': 0, 'right_doc_wrong_section': 70, 'partial_span': 29, 'missed_abstention': 11}
- **iter 5** (rules, rejected): Template words shared by many train questions add noise to scoring; drop tokens that occur in >=10% of train questions.  
  failures before: {'success': 47, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 52, 'partial_span': 36, 'missed_abstention': 9}
- **iter 6** (rules, rejected): Right document, wrong section dominates: question wording rarely matches clause wording ('anti-assignment' vs 'shall not assign'). Expand with a legal synonym lexicon.  
  failures before: {'success': 47, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 52, 'partial_span': 36, 'missed_abstention': 9}
- **iter 7** (rules, rejected): Add character n-gram TF-IDF to BM25 to catch morphological variants and phrase fragments.  
  failures before: {'success': 47, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 52, 'partial_span': 36, 'missed_abstention': 9}
- **iter 8** (rules, rejected): Fixed windows cut clauses in half; split on paragraph/clause boundaries so a chunk is one clause.  
  failures before: {'success': 47, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 52, 'partial_span': 36, 'missed_abstention': 9}
- **iter 9** (rules, rejected): Partial coverage: align chunk boundaries with paragraphs.  
  failures before: {'success': 47, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 52, 'partial_span': 36, 'missed_abstention': 9}
- **iter 10** (rules, rejected): Partial coverage: change chunk granularity (precision vs completeness of the retrieved clause).  
  failures before: {'success': 47, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 52, 'partial_span': 36, 'missed_abstention': 9}
- **iter 11** (rules, rejected): Partial coverage: overlap neighbouring chunks so a clause split by a boundary is still retrieved whole.  
  failures before: {'success': 47, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 52, 'partial_span': 36, 'missed_abstention': 9}
- **iter 12** (random, rejected): Random search over the configuration space (no diagnosis-driven rule left to try).  
  failures before: {'success': 47, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 52, 'partial_span': 36, 'missed_abstention': 9}
- **iter 13** (random, rejected): Random search over the configuration space (no diagnosis-driven rule left to try).  
  failures before: {'success': 47, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 52, 'partial_span': 36, 'missed_abstention': 9}
- **iter 14** (random, rejected): Random search over the configuration space (no diagnosis-driven rule left to try).  
  failures before: {'success': 47, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 52, 'partial_span': 36, 'missed_abstention': 9}
- **iter 15** (random, rejected): Random search over the configuration space (no diagnosis-driven rule left to try).  
  failures before: {'success': 47, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 52, 'partial_span': 36, 'missed_abstention': 9}
