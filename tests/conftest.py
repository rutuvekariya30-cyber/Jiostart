import pytest

from cir.config import Config

# A tiny synthetic corpus with two "contracts".
DOC_A = (
    "SERVICES AGREEMENT between Acme Widgets Inc. and Beta Logistics LLC.\n\n"
    "1. TERM. This Agreement shall commence on January 1, 2020 and expire on December 31, 2022.\n\n"
    "2. ASSIGNMENT. Neither party may assign this Agreement without the prior written consent of the other party.\n\n"
    "3. GOVERNING LAW. This Agreement shall be governed by the laws of the State of New York.\n\n"
    "4. LIABILITY. In no event shall either party's aggregate liability exceed the fees paid in the prior twelve months.\n"
)
DOC_B = (
    "LICENSE AGREEMENT between Gamma Media Corp. and Delta Studios Ltd.\n\n"
    "1. GRANT. Gamma grants Delta a non-exclusive, worldwide license to distribute the Content.\n\n"
    "2. GOVERNING LAW. This Agreement is governed by the laws of England and Wales.\n\n"
    "3. AUDIT. Gamma may audit the books and records of Delta once per year on thirty days notice.\n"
)


@pytest.fixture
def corpus():
    return {"cuad/A.txt": DOC_A, "cuad/B.txt": DOC_B}


@pytest.fixture
def cfg():
    return Config(name="t", chunk_strategy="paragraph", chunk_size=300, min_chunk=40, decompose=True, doc_boost=1.0)
