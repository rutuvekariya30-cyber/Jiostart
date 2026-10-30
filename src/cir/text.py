"""Tokenisation, stopwords, stemming, query decomposition and a small legal-synonym lexicon."""
from __future__ import annotations

import re
from functools import lru_cache

from nltk.stem import PorterStemmer

_STEM = PorterStemmer()
_TOKEN = re.compile(r"[a-z0-9]+")

STOPWORDS = frozenset(
    """a an and are as at be been but by can could did do does for from had has have how if in into is it its
    may of on or shall should such that the their there these this those to under was were what when where which
    who whom will with would any there""".split()
)


@lru_cache(maxsize=200_000)
def _stem(tok: str) -> str:
    return _STEM.stem(tok)


def tokenize(text: str, stopwords: bool = True, stem: bool = False) -> list[str]:
    toks = _TOKEN.findall(text.lower())
    if stopwords:
        toks = [t for t in toks if t not in STOPWORDS]
    if stem:
        toks = [_stem(t) for t in toks]
    return toks


_DECOMPOSE = re.compile(r"^\s*Consider\s+(?:the\s+)?(?P<desc>.+?)\s*;\s*(?P<question>.+?)\s*$", re.S | re.I)


def decompose(query: str) -> tuple[str, str]:
    """Split "Consider the <contract descriptor>; <question>" into (descriptor, question).

    Falls back to ("", query) for free-form questions, so the web app still works for them.
    """
    m = _DECOMPOSE.match(query)
    if not m:
        return "", query.strip()
    return m.group("desc"), m.group("question")


# Domain lexicon: question wording -> words that tend to occur in the clause that answers it.
# Written from general contract-law knowledge; it contains no benchmark answers.
LEGAL_LEXICON: dict[str, str] = {
    "governing law": "governed construed laws state jurisdiction courts",
    "expiration date": "term expire expires expiration effective commence terminate years",
    "renewal term": "renew renewal successive additional period automatically",
    "anti assignment": "assign assignment transfer consent delegate successors",
    "non transferable": "transfer sublicense assign nontransferable",
    "cap on liability": "liability limited aggregate exceed damages indirect consequential",
    "uncapped liability": "unlimited liability indemnify damages",
    "audit rights": "audit inspect records books examine access",
    "terminated for convenience": "terminate convenience notice days without cause",
    "termination of this contract": "terminate termination expiration after survive",
    "services to be provided after": "post termination transition wind assistance continue",
    "competitive restrictions": "compete competing competitive exclusive restriction",
    "non compete": "compete competing competitive business restriction",
    "intellectual property ownership": "ownership owns title rights intellectual property assigns invention",
    "joint intellectual property": "jointly owned joint ownership intellectual property",
    "exclusivity": "exclusive exclusively sole only",
    "covenant not to sue": "covenant sue claim infringement action bring",
    "right of first refusal": "first refusal first offer first negotiation matching",
    "minimum commitment": "minimum purchase commitment quantity volume required",
    "revenue or profit sharing": "revenue profit share royalty percent net sales split",
    "volume restrictions": "volume maximum cap limit quantity not exceed",
    "insurance requirements": "insurance coverage policy insured maintain certificate liability",
    "licenses granted": "license grants grant licensed nonexclusive exclusive right",
    "affiliates": "affiliate affiliates subsidiaries controlled",
    "notice period": "notice days prior written terminate renewal",
    "third party beneficiaries": "third party beneficiary beneficiaries rights enforce",
    "solicitation of employees": "solicit employees hire personnel recruit",
    "solicitation of customers": "solicit customers clients accounts",
    "change of control": "change control merger acquisition acquire assets successor",
    "warranties": "warrant warranty warranties period months defects",
    "non disparagement": "disparage disparagement negative statements",
    "most favored nation": "most favored favoured customer pricing no less favorable lowest",
    "irrevocable": "irrevocable perpetual perpetuity revoke",
}


def expand_query(question: str) -> str:
    """Return extra words for every lexicon entry whose key words all occur in the question."""
    toks = set(tokenize(question, stopwords=False, stem=False))
    stems = {_stem(t) for t in toks}
    extra: list[str] = []
    for key, words in LEGAL_LEXICON.items():
        parts = key.split()
        if all(p in toks or _stem(p) in stems for p in parts):
            extra.append(words)
    return " ".join(extra)
