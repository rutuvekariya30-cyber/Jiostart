# Experiment log (train split only)

Primary: **recall@4** (min delta 0.005); guardrails: precision@4 (tol 0.01), abstain_balanced_acc (tol 0.03), doc_hit@4 (tol 0.02)

| iter | proposer | change | decision | recall@4 | precision@4 | doc_hit@4 | abst. bal. acc | reason |
|---|---|---|---|---|---|---|---|---|
| 0 | - | baseline | baseline | 0.033 | 0.009 | 1.000 | 0.794 |  |
| 1 | rules | decompose=True, doc_boost=1.0 | accepted | 0.336 | 0.073 | 1.000 | 0.771 | recall@4 +0.3030, >= incumbent on 3/3 sub-folds, guardrails ok |
| 2 | rules | boilerplate_df=0.1 | rejected | 0.277 | 0.069 | 1.000 | 0.650 | recall@4 -0.0592 < required +0.005 |
| 3 | rules | expansion=legal | accepted | 0.558 | 0.123 | 1.000 | 0.771 | recall@4 +0.2220, >= incumbent on 3/3 sub-folds, guardrails ok |
| 4 | rules | boilerplate_df=0.1 | rejected | 0.616 | 0.135 | 1.000 | 0.650 | guardrail abstain_balanced_acc dropped -0.1217 (tolerance -0.03) |
| 5 | rules | stem=True | accepted | 0.647 | 0.143 | 1.000 | 0.816 | recall@4 +0.0892, >= incumbent on 3/3 sub-folds, guardrails ok |
| 6 | rules | chunk_strategy=paragraph | rejected | 0.634 | 0.189 | 1.000 | 0.778 | recall@4 -0.0132 < required +0.005 |
| 7 | rules | chunk_size=300 | rejected | 0.542 | 0.185 | 1.000 | 0.783 | recall@4 -0.1054 < required +0.005 |
| 8 | rules | chunk_overlap=100 | accepted | 0.659 | 0.153 | 1.000 | 0.797 | recall@4 +0.0122, >= incumbent on 3/3 sub-folds, guardrails ok |
| 9 | rules | chunk_strategy=paragraph | rejected | 0.639 | 0.194 | 1.000 | 0.782 | recall@4 -0.0200 < required +0.005 |
| 10 | rules | chunk_size=300 | rejected | 0.553 | 0.211 | 1.000 | 0.800 | recall@4 -0.1062 < required +0.005 |
| 11 | random | expansion_weight=0.3 | rejected | 0.633 | 0.143 | 1.000 | 0.797 | recall@4 -0.0263 < required +0.005 |
| 12 | random | abstain_signal=chunk+doc | accepted | 0.659 | 0.153 | 1.000 | 0.964 | abstention-only gain: balanced acc +0.1667, recall@4 +0.0000 within slack |
| 13 | rules | boilerplate_df=0.1 | rejected | 0.621 | 0.147 | 1.000 | 0.825 | recall@4 -0.0380 < required +0.005 |
| 14 | rules | method=hybrid | accepted | 0.681 | 0.163 | 1.000 | 0.964 | recall@4 +0.0215, >= incumbent on 2/3 sub-folds, guardrails ok |
| 15 | rules | boilerplate_df=0.1 | rejected | 0.696 | 0.166 | 1.000 | 0.825 | guardrail abstain_balanced_acc dropped -0.1386 (tolerance -0.03) |
| 16 | rules | chunk_strategy=clause | rejected | 0.685 | 0.219 | 1.000 | 0.949 | recall@4 +0.0043 < required +0.005 |
| 17 | rules | chunk_strategy=paragraph | rejected | 0.687 | 0.214 | 1.000 | 0.949 | improved on only 1/3 sub-folds |
| 18 | rules | chunk_size=300 | rejected | 0.583 | 0.235 | 1.000 | 0.967 | recall@4 -0.0975 < required +0.005 |
| 19 | random | w_char=1.5 | accepted | 0.687 | 0.166 | 1.000 | 0.964 | recall@4 +0.0062, >= incumbent on 3/3 sub-folds, guardrails ok |
| 20 | rules | boilerplate_df=0.1 | rejected | 0.701 | 0.167 | 1.000 | 0.825 | guardrail abstain_balanced_acc dropped -0.1386 (tolerance -0.03) |

## Why each change was tried

- **iter 1** (rules, accepted): 90% of failed queries rank a header/signature chunk first: party names from the query's contract descriptor out-score the question words. Split descriptor from question; use the descriptor only to route to the document.  
  failures before: {'success': 2, 'false_abstention': 11, 'wrong_document': 0, 'right_doc_wrong_section': 117, 'partial_span': 10, 'missed_abstention': 9}
- **iter 2** (rules, rejected): Template words shared by many train questions add noise to scoring; drop tokens that occur in >=10% of train questions.  
  failures before: {'success': 34, 'false_abstention': 7, 'wrong_document': 0, 'right_doc_wrong_section': 70, 'partial_span': 29, 'missed_abstention': 11}
- **iter 3** (rules, accepted): Right document, wrong section dominates: question wording rarely matches clause wording ('anti-assignment' vs 'shall not assign'). Expand with a legal synonym lexicon.  
  failures before: {'success': 34, 'false_abstention': 7, 'wrong_document': 0, 'right_doc_wrong_section': 70, 'partial_span': 29, 'missed_abstention': 11}
- **iter 4** (rules, rejected): Template words shared by many train questions add noise to scoring; drop tokens that occur in >=10% of train questions.  
  failures before: {'success': 53, 'false_abstention': 7, 'wrong_document': 0, 'right_doc_wrong_section': 39, 'partial_span': 41, 'missed_abstention': 11}
- **iter 5** (rules, accepted): Vocabulary mismatch (assign/assignment/assigned); stemming merges inflections.  
  failures before: {'success': 53, 'false_abstention': 7, 'wrong_document': 0, 'right_doc_wrong_section': 39, 'partial_span': 41, 'missed_abstention': 11}
- **iter 6** (rules, rejected): Partial coverage: align chunk boundaries with paragraphs.  
  failures before: {'success': 62, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 28, 'partial_span': 45, 'missed_abstention': 9}
- **iter 7** (rules, rejected): Partial coverage: change chunk granularity (precision vs completeness of the retrieved clause).  
  failures before: {'success': 62, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 28, 'partial_span': 45, 'missed_abstention': 9}
- **iter 8** (rules, accepted): Partial coverage: overlap neighbouring chunks so a clause split by a boundary is still retrieved whole.  
  failures before: {'success': 62, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 28, 'partial_span': 45, 'missed_abstention': 9}
- **iter 9** (rules, rejected): Partial coverage: align chunk boundaries with paragraphs.  
  failures before: {'success': 70, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 28, 'partial_span': 37, 'missed_abstention': 10}
- **iter 10** (rules, rejected): Partial coverage: change chunk granularity (precision vs completeness of the retrieved clause).  
  failures before: {'success': 70, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 28, 'partial_span': 37, 'missed_abstention': 10}
- **iter 11** (random, rejected): Random search over the configuration space (no diagnosis-driven rule left to try).  
  failures before: {'success': 70, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 28, 'partial_span': 37, 'missed_abstention': 10}
- **iter 12** (random, accepted): Random search over the configuration space (no diagnosis-driven rule left to try).  
  failures before: {'success': 70, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 28, 'partial_span': 37, 'missed_abstention': 10}
- **iter 13** (rules, rejected): Template words shared by many train questions add noise to scoring; drop tokens that occur in >=10% of train questions.  
  failures before: {'success': 70, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 28, 'partial_span': 37, 'missed_abstention': 1}
- **iter 14** (rules, accepted): Add character n-gram TF-IDF to BM25 to catch morphological variants and phrase fragments.  
  failures before: {'success': 70, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 28, 'partial_span': 37, 'missed_abstention': 1}
- **iter 15** (rules, rejected): Template words shared by many train questions add noise to scoring; drop tokens that occur in >=10% of train questions.  
  failures before: {'success': 71, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 29, 'partial_span': 35, 'missed_abstention': 1}
- **iter 16** (rules, rejected): Fixed windows cut clauses in half; split on paragraph/clause boundaries so a chunk is one clause.  
  failures before: {'success': 71, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 29, 'partial_span': 35, 'missed_abstention': 1}
- **iter 17** (rules, rejected): Partial coverage: align chunk boundaries with paragraphs.  
  failures before: {'success': 71, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 29, 'partial_span': 35, 'missed_abstention': 1}
- **iter 18** (rules, rejected): Partial coverage: change chunk granularity (precision vs completeness of the retrieved clause).  
  failures before: {'success': 71, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 29, 'partial_span': 35, 'missed_abstention': 1}
- **iter 19** (random, accepted): Random search over the configuration space (no diagnosis-driven rule left to try).  
  failures before: {'success': 71, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 29, 'partial_span': 35, 'missed_abstention': 1}
- **iter 20** (rules, rejected): Template words shared by many train questions add noise to scoring; drop tokens that occur in >=10% of train questions.  
  failures before: {'success': 73, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 28, 'partial_span': 34, 'missed_abstention': 1}
