| config | split | n_ans | n_unans | recall@1 | recall@4 | recall@8 | precision@1 | precision@4 | precision@8 | doc_hit@4 | hit@4 | mrr | answer_rate | correct_abstain_rate | abstain_balanced_acc | e2e_recall@4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | train | 140 | 27 | 0.000 | 0.033 | 0.114 | 0.000 | 0.009 | 0.014 | 1.000 | 0.093 | 0.070 | 0.921 | 0.667 | 0.794 | 0.031 |
| baseline | test | 54 | 13 | 0.000 | 0.032 | 0.102 | 0.000 | 0.013 | 0.016 | 1.000 | 0.111 | 0.069 | 0.907 | 0.692 | 0.800 | 0.030 |
| final | train | 140 | 27 | 0.434 | 0.687 | 0.769 | 0.346 | 0.166 | 0.098 | 1.000 | 0.800 | 0.736 | 0.964 | 0.963 | 0.964 | 0.658 |
| final | test | 54 | 13 | 0.418 | 0.642 | 0.772 | 0.311 | 0.152 | 0.107 | 1.000 | 0.759 | 0.680 | 0.926 | 1.000 | 0.963 | 0.595 |

Correct abstentions by kind (abstained / total):

| config/split | bare_absent_topic | contract_not_in_corpus | in_corpus_no_clause | off_topic |
|---|---|---|---|---|
| baseline/train | 2/2 | 10/10 | 3/11 | 3/4 |
| baseline/test | 2/2 | 4/4 | 1/5 | 2/2 |
| final/train | 2/2 | 10/10 | 10/11 | 4/4 |
| final/test | 2/2 | 4/4 | 5/5 | 2/2 |

Ablation on train (one component removed from the final config; abstention thresholds re-fitted on train):

| variant | recall@4 | precision@4 | doc_hit@4 | abstain bal. acc | e2e recall@4 |
|---|---|---|---|---|---|
| final (all components) | 0.687 | 0.166 | 1.000 | 0.964 | 0.658 |
| - query decomposition & doc routing | 0.128 | 0.033 | 1.000 | 0.848 | 0.116 |
| - legal synonym expansion | 0.493 | 0.119 | 1.000 | 0.964 | 0.472 |
| - stemming | 0.651 | 0.155 | 1.000 | 0.953 | 0.614 |
| - char n-gram retriever (BM25 only) | 0.659 | 0.153 | 1.000 | 0.964 | 0.631 |
| - chunk overlap | 0.663 | 0.151 | 1.000 | 0.982 | 0.632 |
| - contract-match abstention signal | 0.687 | 0.166 | 1.000 | 0.797 | 0.658 |
