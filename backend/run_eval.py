import json
import glob
import os
from pdf_utils import extract_text
from cli import analyze_text, squash

def is_found(expected: dict, findings: list[dict]) -> bool:
    for f in findings:
        if f["category"]==expected["category"]  and squash(expected["quote_contains"]) in squash(f["quote"]):
            return True
    return False

def is_flagged(expected: dict, findings: list[dict]) -> bool:
    for f in findings:
        if squash(expected["quote_contains"]) in squash(f["quote"]):
            return True
    return False



if __name__ == "__main__":
    tp = fn = fp = halluc = 0

    for pdf_path in sorted(glob.glob("../eval/contracts/*.pdf")):
        name = os.path.basename(pdf_path).replace(".pdf", "")
        with open(f"../eval/expected/{name}.json") as f:
            expected = json.load(f)
        with open(pdf_path, "rb") as f:
            findings = analyze_text(extract_text(f.read()))

        print(f"\n=== {name} ===")

        for e in expected["must_find"]:
            if is_found(e, findings):
                tp += 1
                print("  HIT  ", e["category"], "|", e["quote_contains"])
            else:
                fn+=1
                print("  MISS ", e["category"], "|", e["quote_contains"])

        for e in expected["must_not_flag"]:
            if is_flagged(e, findings):
                fp += 1
                print("  FALSE ALARM |", e["quote_contains"])

        for f in findings:
            if f["hallucinated"]:
                halluc+=1

    recall = tp / (tp + fn) if tp + fn else 0
    precision = tp / (tp + fp) if tp + fp else 0
    print(f"\nRecall:    {tp}/{tp + fn} = {recall:.0%}")
    print(f"Precision: {tp}/{tp + fp} = {precision:.0%}")
    print(f"Hallucinated quotes: {halluc}")                    