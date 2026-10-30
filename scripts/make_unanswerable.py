"""Generate data/unanswerable.jsonl (run ONCE, before the improvement loop; then never edit).

Four kinds of queries that the indexed contracts cannot answer:
  in_corpus_no_clause     names an indexed contract, asks about a topic that contract never mentions
  contract_not_in_corpus  asks a standard question about a contract that is not indexed
  off_topic               nothing to do with contracts
  bare_absent_topic       contract-flavoured question, no contract named, topic absent from every indexed contract

Every topic carries a regex; --check verifies it matches nothing in the (relevant) indexed contracts.
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cir.data import assign_split, load_dataset  # noqa: E402
from cir.text import decompose  # noqa: E402

# (question, regex that must NOT match in the chosen contract)
IN_CORPUS = [
    ("Does this contract require the vendor to hold ISO 27001 certification?", r"27001|\bISO\s?\d{4,5}"),
    ("What data breach notification deadline applies under this contract?", r"breach notification|data breach|security breach"),
    ("Does this contract address the use of artificial intelligence or machine learning?", r"artificial intelligence|machine learning"),
    ("Are there any GDPR data-processing obligations in this contract?", r"GDPR|General Data Protection"),
    ("Is there a pandemic-specific force majeure provision in this contract?", r"pandemic|epidemic|covid"),
    ("Does this contract allow payment in cryptocurrency?", r"bitcoin|crypto"),
    ("What are the sustainability or ESG reporting requirements in this contract?", r"\bESG\b|sustainab|carbon|emission"),
    ("Does this contract require the use of recycled packaging materials?", r"recycl"),
    ("Is there a remote-work or work-from-home policy in this contract?", r"remote work|work from home|telecommut"),
    ("Does this contract include a source code escrow arrangement?", r"escrow"),
    ("What dress code applies to on-site personnel under this contract?", r"dress code|attire"),
    ("Is there a clause requiring arbitration seated in Singapore?", r"singapore"),
    ("What happens to the parties' social media accounts after termination?", r"social media"),
    ("Does this contract regulate the handling of nuclear materials?", r"nuclear|radioactive"),
    ("Does the contract require criminal background checks of employees?", r"background check"),
    ("Does this contract mention blockchain technology?", r"blockchain"),
]

NOT_IN_CORPUS = [
    ("Master Services Agreement between Northwind Traders Ltd and Contoso Pharma Inc.", "What is the governing law for this contract?", r"northwind|contoso"),
    ("Lease Agreement between Harborview Properties LLC and Delta Coffee Roasters Inc.", "What is the expiration date of this contract?", r"harborview|delta coffee"),
    ("Software License Agreement between Quantum Ridge Systems and Fabrikam Logistics GmbH", "Is there an anti-assignment clause in this contract?", r"quantum ridge|fabrikam"),
    ("Distribution Agreement between Sunrise Beverages Pty Ltd and Alpine Retail Group", "Is there a cap on liability under this contract?", r"sunrise beverages|alpine retail"),
    ("Franchise Agreement between Bluebird Burgers Inc. and Marigold Holdings LLC", "What licenses are granted under this contract?", r"bluebird|marigold"),
    ("Joint Venture Agreement between Tallgrass Energy Partners and Ostrava Mining s.r.o.", "What are the audit rights under this contract?", r"tallgrass|ostrava"),
    ("Consulting Agreement between Evergreen Analytics LLC and Zenith Aerospace Corp.", "Can this contract be terminated for convenience, and under what conditions?", r"evergreen analytics|zenith aerospace"),
    ("Sponsorship Agreement between Redwood Racing Ltd and Polar Sportswear Co.", "Does this contract include an exclusivity agreement?", r"redwood racing|polar sportswear"),
    ("Supply Agreement between Kestrel Components Inc. and Lumen Robotics Ltd.", "What are the insurance requirements under this contract?", r"kestrel components|lumen robotics"),
    ("Co-Branding Agreement between Meridian Bank plc and Orchid Travel Ltd.", "What is the renewal term for this contract?", r"meridian bank|orchid travel"),
    ("Reseller Agreement between Cobalt Networks Inc. and Sapphire Telecom S.A.", "Is there a non-compete clause in this contract?", r"cobalt networks|sapphire telecom"),
    ("Employment Agreement between Juniper Biotech Inc. and Dr. Amelia Okafor", "Is there a clause preventing the solicitation of employees in this contract?", r"juniper biotech|okafor"),
    ("Manufacturing Agreement between Saffron Foods Ltd and Granite Packaging Inc.", "How is intellectual property ownership assigned in this contract?", r"saffron foods|granite packaging"),
    ("Content License Agreement between Starlight Studios and Horizon Streaming Inc.", "Are there any third-party beneficiaries designated in this contract?", r"starlight studios|horizon streaming"),
]

OFF_TOPIC = [
    "What is the capital of Australia?",
    "How do I bake sourdough bread at home?",
    "Who won the 2018 FIFA World Cup?",
    "What is the boiling point of water at sea level?",
    "Summarize the plot of Hamlet.",
    "What is the weather forecast for Mumbai tomorrow?",
]

BARE_ABSENT = [
    ("Does the agreement cover drone or unmanned aircraft operations?", r"\bdrones?\b|unmanned aircraft"),
    ("Which party must supply the office furniture for the project team?", r"office furniture"),
    ("Is the stadium naming right transferable to a new owner?", r"naming right|stadium"),
    ("What organic certification must the supplier maintain?", r"organic"),
    ("Does the agreement allow the tenant to sublet the rooftop?", r"rooftop"),
    ("What is the penalty for late delivery of helicopters?", r"helicopter"),
]


def doc_descriptors(ds):
    out = {}
    for t in ds.answerable:
        d, _ = decompose(t["query"])
        out.setdefault(t["snippets"][0]["file_path"], d)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/unanswerable.jsonl")
    ap.add_argument("--check", action="store_true", help="only verify an existing file against the corpus")
    args = ap.parse_args()
    ds = load_dataset(unanswerable_path=Path("/nonexistent"))
    desc = doc_descriptors(ds)
    rng = random.Random(1228)
    rows, problems = [], []

    docs = sorted(desc)
    for q, rx in IN_CORPUS:
        ok = [d for d in docs if not re.search(rx, ds.corpus[d], re.I)]
        if not ok:
            problems.append(("in_corpus: topic present in every doc", q))
            continue
        d = rng.choice(ok)
        rows.append({"query": f"Consider the {desc[d]}; {q}", "kind": "in_corpus_no_clause", "doc": d, "check": rx})
    for name, q, rx in NOT_IN_CORPUS:
        if any(re.search(rx, t, re.I) for t in ds.corpus.values()):
            problems.append(("not_in_corpus: name found in corpus", name))
            continue
        rows.append({"query": f"Consider the {name}; {q}", "kind": "contract_not_in_corpus", "check": rx})
    for q in OFF_TOPIC:
        rows.append({"query": q, "kind": "off_topic"})
    for q, rx in BARE_ABSENT:
        hits = [d for d in docs if re.search(rx, ds.corpus[d], re.I)]
        if hits:
            problems.append((f"bare: topic present in {len(hits)} docs", q))
            continue
        rows.append({"query": q, "kind": "bare_absent_topic", "check": rx})

    for kind, msg in problems:
        print("PROBLEM:", kind, "|", msg)
    if args.check:
        return
    Path(args.out).write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    from collections import Counter
    print(f"wrote {len(rows)} queries -> {args.out}")
    print("by kind :", dict(Counter(r["kind"] for r in rows)))
    print("by split:", dict(Counter(assign_split(r["query"]) for r in rows)))


if __name__ == "__main__":
    main()
