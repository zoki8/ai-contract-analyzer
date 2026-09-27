"""Build evaluation cases from CUAD (Contract Understanding Atticus Dataset).

CUAD: 510 real commercial contracts (SEC EDGAR filings) with clause spans
labelled by lawyers. License: CC BY 4.0, The Atticus Project.
https://www.atticusprojectai.org/cuad

Usage (from the backend folder):
    python import_cuad.py path/to/data.zip          # 8 shortest matching contracts
    python import_cuad.py path/to/data.zip --n 5

data.zip comes from https://github.com/TheAtticusProject/cuad
For every picked contract this writes
    ../eval/contracts/cuad_XX.txt   the full contract text
    ../eval/expected/cuad_XX.json   must_find / must_not_flag built from the lawyers' labels
"""
import argparse
import json
import zipfile
from pathlib import Path

# CUAD category -> our category
CATEGORY_MAP = {
    "Renewal Term": "auto_renewal",
    "Termination For Convenience": "termination",
    "Cap On Liability": "liability",
    "Liquidated Damages": "penalty",
}
# a standard clause every contract has; flagging it as risky is a false alarm
NOT_RISKY = "Governing Law"

MAX_CHARS = 20_000  # keep contracts short so one evaluation run stays in minutes
MIN_HITS = 3        # at least this many of our categories must be labelled

ROOT = Path(__file__).parent.parent
CONTRACTS = ROOT / "eval" / "contracts"
EXPECTED = ROOT / "eval" / "expected"


def labelled_spans(paragraph: dict) -> dict[str, list[str]]:
    """CUAD category name -> list of clause texts the lawyers highlighted."""
    spans = {}
    for qa in paragraph["qas"]:
        if qa["answers"]:
            category = qa["id"].split("__", 1)[1]
            spans[category] = [a["text"].strip() for a in qa["answers"]]
    return spans


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_zip")
    parser.add_argument("--n", type=int, default=8)
    args = parser.parse_args()

    with zipfile.ZipFile(args.data_zip) as z:
        cuad = json.load(z.open("CUADv1.json"))

    candidates = []
    for contract in cuad["data"]:
        paragraph = contract["paragraphs"][0]
        text = paragraph["context"]
        spans = labelled_spans(paragraph)
        hits = [c for c in CATEGORY_MAP if c in spans]
        if len(text) <= MAX_CHARS and len(hits) >= MIN_HITS and NOT_RISKY in spans:
            candidates.append((len(text), contract["title"], text, spans))

    candidates.sort()  # shortest first
    CONTRACTS.mkdir(parents=True, exist_ok=True)
    EXPECTED.mkdir(parents=True, exist_ok=True)

    for i, (_, title, text, spans) in enumerate(candidates[: args.n], 1):
        name = f"cuad_{i:02d}"
        expected = {
            "source": f"CUAD v1 (CC BY 4.0): {title}",
            "must_find": [
                {"category": ours, "quote_contains": spans[cuad_name]}
                for cuad_name, ours in CATEGORY_MAP.items()
                if cuad_name in spans
            ],
            "must_not_flag": [{"quote_contains": spans[NOT_RISKY]}],
        }
        (CONTRACTS / f"{name}.txt").write_text(text, encoding="utf-8")
        (EXPECTED / f"{name}.json").write_text(
            json.dumps(expected, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        cats = ", ".join(item["category"] for item in expected["must_find"])
        print(f"{name}  {len(text):>6} chars  {cats}  <- {title}")


if __name__ == "__main__":
    main()
