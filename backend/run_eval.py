import json
import sys
from pathlib import Path

from pdf_utils import extract_text, chunk_text, normalize
from llm import analyze_chunk
from cli import dedupe, squash

CONTRACTS_DIR = Path("../eval/contracts")
EXPECTED_DIR = Path("../eval/expected")


def analyze_pdf(path: Path):
    text = extract_text(path.read_bytes())
    source = squash(text)
    findings = []
    for chunk in chunk_text(text):
        findings.extend(analyze_chunk(chunk).findings)
    out = []
    for f in dedupe(findings):
        d = f.model_dump()
        d["hallucinated"] = squash(f.quote) not in source
        out.append(d)
    return out


def matches(expected, findings):
    for f in findings:
        if f["category"] == expected["category"] and \
           expected["quote_contains"].lower() in f["quote"].lower():
            return True
    return False


def run():
    pdfs = sorted(CONTRACTS_DIR.glob("*.pdf"))
    if not pdfs:
        print("No contracts found in eval/contracts/", file=sys.stderr)
        return

    total_expected = 0
    total_found = 0
    total_findings = 0
    total_hallucinated = 0

    for pdf in pdfs:
        expected_file = EXPECTED_DIR / f"{pdf.stem}.json"
        if not expected_file.exists():
            print(f"skip {pdf.name}: no expected file", file=sys.stderr)
            continue

        expected = json.loads(expected_file.read_text())
        print(f"\n=== {pdf.name} ===", file=sys.stderr)
        findings = analyze_pdf(pdf)

        found = sum(1 for e in expected if matches(e, findings))
        hallucinated = sum(1 for f in findings if f["hallucinated"])

        total_expected += len(expected)
        total_found += found
        total_findings += len(findings)
        total_hallucinated += hallucinated

        print(f"  expected: {len(expected)}  found: {found}  "
              f"model findings: {len(findings)}  hallucinated: {hallucinated}")
        for e in expected:
            ok = matches(e, findings)
            print(f"    [{'OK' if ok else 'MISS'}] {e['category']}: {e['quote_contains']}")

    recall = total_found / total_expected if total_expected else 0
    print(f"\n=== Summary ===")
    print(f"Recall: {total_found}/{total_expected} ({recall:.0%})")
    print(f"Total model findings: {total_findings}")
    print(f"Hallucinated quotes: {total_hallucinated}/{total_findings}")


if __name__ == "__main__":
    run()
