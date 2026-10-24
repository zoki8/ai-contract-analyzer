"""Run the stress contracts from make_stress.py.

    python run_stress.py --chunks-only      # no model: is every planted clause whole in some chunk?
    python run_stress.py                    # full run with the model (slow: long contracts!)
    python run_stress.py --model qwen2.5:3b --only stress_giant

--chunks-only answers "can the model even see this clause in one piece?". A clause that is
whole in 0 chunks cannot be found; one that is whole in 2+ chunks will be reported twice
and must be merged by dedupe().
"""
import argparse
import json
import time
from pathlib import Path

import cli
import llm
from pdf_utils import chunk
from run_eval import alternatives, is_flagged, is_found, load_text

STRESS = Path(__file__).parent.parent / "eval" / "stress"


def chunk_report(text: str, expected: dict):
    parts = chunk(text)
    squashed = [cli.squash(p) for p in parts]
    print(f"  {len(text)} chars -> {len(parts)} chunks")
    for e in expected["must_find"]:
        q = cli.squash(alternatives(e)[0])
        whole = [i + 1 for i, p in enumerate(squashed) if q in p]
        status = "LOST " if not whole else ("TWICE" if len(whole) > 1 else "ok   ")
        print(f"  {status} {e.get('id', e['category']):18} whole in chunk(s): {whole or '-'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks-only", action="store_true")
    ap.add_argument("--model", default=llm.MODEL)
    ap.add_argument("--only", help="run one contract, e.g. stress_giant")
    ap.add_argument("--txt", action="store_true", help="use the .txt instead of the .pdf")
    args = ap.parse_args()
    llm.MODEL = args.model

    # count findings before dedupe, to see how many duplicates it removed
    raw_counts = []
    original_dedupe = cli.dedupe
    cli.dedupe = lambda fs, *rest: (raw_counts.append(len(fs)), original_dedupe(fs, *rest))[1]
    ext = ".txt" if args.txt else ".pdf"
    summary = []
    for exp_path in sorted((STRESS / "expected").glob("*.json")):
        name = exp_path.stem
        if args.only and name != args.only:
            continue
        expected = json.loads(exp_path.read_text(encoding="utf-8"))
        text = load_text(str(STRESS / "contracts" / f"{name}{ext}"))
        print(f"\n=== {name}{ext} ===")
        chunk_report(text, expected)
        if args.chunks_only:
            continue

        failed = []
        t0 = time.time()
        findings = cli.analyze_text(text, lambda i, n: print(f"  chunk {i}/{n}", end="\r"), failed)
        secs = time.time() - t0
        hits = [e for e in expected["must_find"] if is_found(e, findings)]
        for e in expected["must_find"]:
            print("  HIT " if e in hits else "  MISS", e.get("id", e["category"]))
        alarms = [e for e in expected["must_not_flag"] if is_flagged(e, findings)]
        for e in alarms:
            print("  FALSE ALARM", e.get("id"))
        halluc = sum(f["hallucinated"] for f in findings)
        row = {"contract": name, "chars": len(text), "chunks": len(chunk(text)),
               "found": f"{len(hits)}/{len(expected['must_find'])}", "false_alarms": len(alarms),
               "hallucinated": halluc, "before_dedupe": raw_counts[-1], "after_dedupe": len(findings),
               "failed_chunks": failed, "seconds": round(secs)}
        print("  ", row)
        summary.append(row)

    if summary:
        out = STRESS / "results"
        out.mkdir(exist_ok=True)
        (out / f"{args.model.replace(':', '_')}.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
