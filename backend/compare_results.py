import glob
import json

rows = [json.load(open(p)) for p in sorted(glob.glob("../eval/results/*.json"))]
print("| Model | Recall | Precision | Hallucinated | Time |")
print("|---|---|---|---|---|")
for r in rows:
    print(f"| {r['model']} | {r['tp']}/{r['tp'] + r['fn']} ({r['recall']:.0%}) "
          f"| {r['precision']:.0%} | {r['hallucinated']} | {r['seconds']} s |")
