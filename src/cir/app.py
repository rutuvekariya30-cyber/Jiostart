"""Streamlit demo:  streamlit run src/cir/app.py"""
from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

from cir.config import load_config
from cir.data import load_dataset
from cir.evaluate import build_pipeline

st.set_page_config(page_title="Contract clause search", layout="wide")
st.title("Contract clause search")
st.caption("Finds the passages of a contract that answer a question, with exact character offsets, "
           "and says so when no passage is relevant enough.")

configs = sorted(Path("configs").glob("*.yaml"))
names = [p.name for p in configs]
default = names.index("final.yaml") if "final.yaml" in names else 0


@st.cache_resource(show_spinner="Indexing contracts...")
def get_pipeline(config_name: str, all_docs: bool):
    cfg = load_config(Path("configs") / config_name)
    ds = load_dataset(all_docs=all_docs)
    return build_pipeline(cfg, ds), ds, cfg


with st.sidebar:
    config_name = st.selectbox("Pipeline configuration", names, index=default)
    all_docs = st.checkbox("Index all 462 CUAD contracts", value=False)
    k = st.slider("Passages to show", 1, 10, 4)
    show_candidates = st.checkbox("Show ranked candidates even when the system abstains", value=False)

pipe, ds, cfg = get_pipeline(config_name, all_docs)
st.sidebar.write(f"{len(ds.corpus)} contracts, {len(pipe.chunks)} chunks")

examples = [
    "Consider the Service Agreement between BicycleTX Ltd and Nigel Crockett for Chief Business Officer Position; What is the governing law for this contract?",
    "What licenses are granted under this contract?",
    "Does this contract address the use of artificial intelligence?",
]
ex = st.selectbox("Example questions", [""] + examples)
query = st.text_area("Question", value=ex, height=80,
                     placeholder='e.g. "Consider the <contract>; Is there an anti-assignment clause in this contract?"')

if st.button("Search", type="primary") and query.strip():
    res = pipe.search(query, k=k)
    cols = st.columns(2)
    cols[0].metric("Best-passage confidence", f"{res.chunk_conf:.2f}", help=f"abstains below {cfg.abstain_chunk:.2f}")
    if res.doc_conf is not None:
        cols[1].metric("Contract match", f"{res.doc_conf:.2f}", help=f"abstains below {cfg.abstain_doc:.2f}")
    if res.abstained:
        st.warning("No passage in the indexed contracts is relevant enough to answer this question.")
    if not res.abstained or show_candidates:
        if res.abstained:
            st.caption("Ranked candidates (below the abstention threshold):")
        for h in res.hits[:k]:
            with st.expander(f"#{h.rank} · {h.doc.split('/')[-1]} · chars {h.start}-{h.end} · score {h.score:.3f}", expanded=h.rank <= 2):
                st.markdown(f"<div style='white-space:pre-wrap'>{html.escape(h.text)}</div>", unsafe_allow_html=True)
