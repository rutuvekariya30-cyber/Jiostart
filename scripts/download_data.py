"""Download benchmarks/cuad.json and the corpus/cuad folder of LegalBench-RAG into ./data."""
import argparse
from pathlib import Path

from huggingface_hub import snapshot_download

REPO = "awinml/legalbench-rag"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/legalbench-rag")
    args = ap.parse_args()
    out = Path(args.out)
    snapshot_download(
        repo_id=REPO,
        repo_type="dataset",
        local_dir=str(out),
        allow_patterns=["benchmarks/cuad.json", "corpus/cuad/*"],
    )
    n = len(list((out / "corpus" / "cuad").glob("*.txt")))
    print(f"downloaded to {out}: {n} corpus files")


if __name__ == "__main__":
    main()
