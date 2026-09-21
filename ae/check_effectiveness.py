"""Recompute reported CSV counts; this does not rerun CookieTrace.

Usage: python3 check_effectiveness.py /path/to/CookieTrace
No third-party dependencies. Writes JSON to stdout only.
"""
import csv
import json
import statistics
import sys
from pathlib import Path


def summarize(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        all_rows = list(csv.DictReader(f))
    totals = [r for r in all_rows if r["Website"].strip().lower() == "total"]
    rows = [r for r in all_rows if r["Website"].strip().lower() != "total"]
    gt_col = next(k for k in rows[0] if "Ground Truth" in k)
    gt = [int(r[gt_col]) for r in rows]
    tp = [int(r["TP"]) for r in rows]
    fp = [int(r["FP"]) for r in rows]
    if any(g <= 0 or t < 0 or f < 0 or t > g or t + f == 0
           for g, t, f in zip(gt, tp, fp)):
        raise ValueError("Invalid counts or undefined precision/recall")
    result = {
        "samples": len(rows),
        "websites": len({r["Website"] for r in rows}),
        "ground_truth_sources": sum(gt), "TP": sum(tp), "FP": sum(fp),
        "FN": sum(gt) - sum(tp),
        "macro_precision_percent": 100 * statistics.mean(t / (t + f) for t, f in zip(tp, fp)),
        "micro_precision_percent": 100 * sum(tp) / (sum(tp) + sum(fp)),
        "macro_recall_percent": 100 * statistics.mean(t / g for t, g in zip(tp, gt)),
        "micro_recall_percent": 100 * sum(tp) / sum(gt),
        "excluded_total_rows": len(totals),
    }
    for r in totals:
        if (int(r[gt_col]), int(r["TP"]), int(r["FP"])) != (sum(gt), sum(tp), sum(fp)):
            raise ValueError("Total row disagrees with sample sums")
    return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 check_effectiveness.py /path/to/CookieTrace")
    root = Path(sys.argv[1]) / "statistics"
    print(json.dumps({name: summarize(root / name) for name in
                     ("effectiveness_original.csv", "effectiveness_deduplicated.csv")}, indent=2))
