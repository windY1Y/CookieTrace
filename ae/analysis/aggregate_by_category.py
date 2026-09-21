#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aggregate_by_category.py

Read a scripts JSON (structure: top-level keys like "consent", each a list of items containing
fields "normalized", "count", "categories" (list of strings), ...), then:

1) For each item and for each category in item["categories"]:
     - increment num_items for that category by 1
     - add item["count"] to total_count for that category
2) Sort categories by num_items (desc)
3) Write output JSON with sorted list of category summaries.

Output format (JSON):
{
  "categories_summary": [
    {
      "category": "consent",
      "num_items": 42,
      "total_count": 12345
    },
    ...
  ]
}
"""

from __future__ import annotations
import argparse
import json
from collections import defaultdict
from typing import Dict, Any, List

def normalize_category(cat: str) -> str:
    if cat is None:
        return "unknown"
    return str(cat).strip().lower()

def aggregate(input_path: str) -> List[Dict[str, Any]]:
    # counters
    num_items = defaultdict(int)    # category -> number of items (each item counts once per category)
    total_count = defaultdict(int)  # category -> sum of item['count']

    # load input json
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Input JSON must be an object with top-level categories mapping to lists.")

    # iterate all top-level lists
    for top_key, items in data.items():
        if not isinstance(items, list):
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            cats = it.get("categories") or []
            # treat missing categories as ['unknown']
            if not cats:
                cats = ["unknown"]
                print(f"item {it.get('normalized')} missing categories, assigning 'unknown'.")
            # get item's count (int); fallback 0
            if len(cats) > 1:
                print(f"item {it.get('normalized')} with multiple categories {cats}, counting for each.")
            try:
                item_count = int(it.get("count") or 0)
            except Exception:
                item_count = 0
            # increment per category
            for raw_cat in cats:
                cat = normalize_category(raw_cat)
                num_items[cat] += 1
                total_count[cat] += item_count

    # build list of summaries, sorted by num_items desc
    summary_list = []
    for cat in num_items:
        summary_list.append({
            "category": cat,
            "num_items": num_items[cat],
            "total_count": total_count.get(cat, 0)
        })

    summary_list.sort(key=lambda x: (-x["num_items"], -x["total_count"], x["category"]))
    return summary_list

def main():
    parser = argparse.ArgumentParser(description="Aggregate script items by categories and sum counts.")
    parser.add_argument('--in', '-i', dest='input', required=True, help='Input JSON file (scripts_with_types.json)')
    parser.add_argument('--out', '-o', dest='output', default='categories_summary.json', help='Output JSON file (default: categories_summary.json)')
    args = parser.parse_args()

    summary_list = aggregate(args.input)

    out_obj = {"categories_summary": summary_list}
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(out_obj, f, indent=2, ensure_ascii=False)

    # Print brief table to stdout
    print(f"Wrote {len(summary_list)} categories to {args.output}\n")
    print(f"{'category':30} {'num_items':>10} {'total_count':>12}")
    print("-" * 56)
    for s in summary_list:
        print(f"{s['category']:30} {s['num_items']:10d} {s['total_count']:12d}")

if __name__ == "__main__":
    main()
