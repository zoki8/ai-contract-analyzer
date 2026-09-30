"""Evaluate the pipeline on labelled contracts.

    python run_eval.py                       # default model from llm.py
    python run_eval.py --model llama3.1:8b   # any model pulled in Ollama

Every contract in ../eval/contracts (.pdf or .txt) is analyzed and compared
with ../eval/expected/<same name>.json. A summary is also saved to
../eval/results/<model>.json so several models can be compared.
"""
import argparse
import glob
import json
import os
import time

import llm
from cli import analyze_text, appears_in, squash
from pdf_utils import extract_text

MIN_REVERSE = 20  # a model quote this long may match by being inside the expected clause


def alternatives(expected: dict) -> list[str]:
    """quote_contains may be one string or a list of accepted alternatives."""
    q = expected["quote_contains"]
    return q if isinstance(q, list) else [q]


def quotes_match(expected_quote: str, model_quote: str) -> bool:
    """Match when the expected text is inside the model's quote, or when the
    model quoted a meaningful part of a longer labelled clause."""
    e, m = squash(expected_quote), squash(model_quote)
    return e in m or (len(m) >= MIN_REVERSE and appears_in(m, e))


def is_found(expected: dict, findings: list[dict]) -> bool:
    for f in findings:
        if f["category"] == expected["category"]:
            if any(quotes_match(q, f["quote"]) for q in alternatives(expected)):
                return True
    return False


def is_flagged(expected: dict, findings: list[dict]) -> bool:
    for f in findings:
        if any(quotes_match(q, f["quote"]) for q in alternatives(expected)):
            return True
    return False


def load_text(path: str) -> str:
    if path.endswith(".txt"):
        with open(path, encoding="utf-8") as f:
            return f.read()
    with open(path, "rb") as f:
        return extract_text(f.read())


def label(expected: dict) -> str:
    return alternatives(expected)[0][:60]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=llm.MODEL)
    args = parser.parse_args()
    llm.MODEL = args.model  # analyze_chunk reads llm.MODEL on every call

    tp = fn = fp = halluc = 0
    started = time.time()
    paths = sorted(glob.glob("../eval/contracts/*.pdf") + glob.glob("../eval/contracts/*.txt"))

    for path in paths:
        name = os.path.splitext(os.path.basename(path))[0]
        with open(f"../eval/expected/{name}.json", encoding="utf-8") as f:
            expected = json.load(f)

        t0 = time.time()
        findings = analyze_text(load_text(path))
        print(f"\n=== {name} ({time.time() - t0:.0f} s) ===")

        for e in expected["must_find"]:
            if is_found(e, findings):
                tp += 1
                print("  HIT  ", e["category"], "|", label(e))
            else:
                fn += 1
                other = [f["category"] for f in findings
                         if any(quotes_match(q, f["quote"]) for q in alternatives(e))]
                reason = f"model said: {', '.join(other)}" if other else "not reported"
                print("  MISS ", e["category"], "|", label(e), f"  <- {reason}")

        for e in expected["must_not_flag"]:
            if is_flagged(e, findings):
                fp += 1
                print("  FALSE ALARM |", label(e))

        for f in findings:
            if f["hallucinated"]:
                halluc += 1
                print("  HALLUCINATED", f["category"], "|", f["quote"][:80])

    seconds = time.time() - started
    recall = tp / (tp + fn) if tp + fn else 0
    precision = tp / (tp + fp) if tp + fp else 0

    print(f"\nModel:     {args.model}")
    print(f"Recall:    {tp}/{tp + fn} = {recall:.0%}")
    print(f"Precision: {tp}/{tp + fp} = {precision:.0%}")
    print(f"Hallucinated quotes: {halluc}")
    print(f"Time:      {seconds:.0f} s for {len(paths)} contracts")

    os.makedirs("../eval/results", exist_ok=True)
    with open(f"../eval/results/{args.model.replace(':', '_')}.json", "w") as f:
        json.dump(
            {"model": args.model, "tp": tp, "fn": fn, "fp": fp, "recall": recall,
             "precision": precision, "hallucinated": halluc, "seconds": round(seconds),
             "contracts": len(paths)},
            f, indent=2,
        )


if __name__ == "__main__":
    main()
