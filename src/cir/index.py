"""Sparse indexes over chunks: BM25 (words) and TF-IDF (character n-grams)."""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

from .text import tokenize


class BM25:
    """Okapi BM25 with the weights precomputed into a sparse (terms x docs) matrix."""

    def __init__(self, texts: list[str], k1: float, b: float, stopwords: bool, stem: bool):
        self.k1, self.b, self.stopwords, self.stem = k1, b, stopwords, stem
        self.vec = CountVectorizer(analyzer=lambda t: tokenize(t, stopwords, stem))
        tf = self.vec.fit_transform(texts).tocsr().astype(np.float64)
        self.n = tf.shape[0]
        dl = np.asarray(tf.sum(axis=1)).ravel()
        avgdl = max(dl.mean(), 1e-9)
        df = np.asarray((tf > 0).sum(axis=0)).ravel()
        self.df = df
        self.idf = np.log(1.0 + (self.n - df + 0.5) / (df + 0.5))
        coo = tf.tocoo()
        denom = coo.data + k1 * (1.0 - b + b * dl[coo.row] / avgdl)
        w = self.idf[coo.col] * coo.data * (k1 + 1.0) / denom
        self.W = sp.csr_matrix((w, (coo.col, coo.row)), shape=(tf.shape[1], self.n))  # terms x docs
        self.vocab = self.vec.vocabulary_
        self.oov_idf = float(np.log(1.0 + (self.n + 0.5) / 0.5))  # idf of a term seen in no document

    def score(self, weighted_tokens: dict[str, float]) -> np.ndarray:
        idx, wts = [], []
        for t, w in weighted_tokens.items():
            j = self.vocab.get(t)
            if j is not None:
                idx.append(j)
                wts.append(w)
        if not idx:
            return np.zeros(self.n)
        return np.asarray(sp.csr_matrix(np.array(wts)).dot(self.W[idx]).todense()).ravel()

    def upper_bound(self, weighted_tokens: dict[str, float]) -> float:
        """Largest score a document could get from these terms (tf -> infinity); OOV terms count fully."""
        total = 0.0
        for t, w in weighted_tokens.items():
            j = self.vocab.get(t)
            idf = self.idf[j] if j is not None else self.oov_idf
            total += w * idf * (self.k1 + 1.0)
        return total


class CharTfidf:
    def __init__(self, texts: list[str], ngram=(3, 5)):
        self.vec = TfidfVectorizer(analyzer="char_wb", ngram_range=ngram, sublinear_tf=True, lowercase=True, min_df=2)
        self.X = self.vec.fit_transform(texts)

    def score(self, query: str) -> np.ndarray:
        q = self.vec.transform([query])
        return np.asarray((self.X @ q.T).todense()).ravel()
