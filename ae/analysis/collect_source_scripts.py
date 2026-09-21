#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect_source_scripts_ignore_query.py

Usage:
    python collect_source_scripts_ignore_query.py -d /path/to/root_dir

Notes:
 - --collapse-subdomains: collapse subdomains to registrable domain (eTLD+1).
 - Output JSON now contains per-category lists sorted by count (desc). Each item:
   { "normalized": "...", "count": N, "examples": [...] }
 - count is the number of times the normalized key was encountered (duplicates counted).
"""

import argparse
import os
import json
import re
from urllib.parse import urlparse

FILENAME_RE = re.compile(r'^(?P<domain>[^_]+)_.+_path\.json$')

def get_registrable_domain(netloc: str) -> str:
    host = netloc.split(':')[0].lower()
    if host.isdigit() or host == 'localhost' or re.match(r'^\d+\.\d+\.\d+\.\d+$', host):
        return netloc
    try:
        import tldextract
        ext = tldextract.extract(host)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}"
        else:
            return host
    except Exception:
        parts = host.split('.')
        if len(parts) <= 2:
            return host
        common_second_level = {'com', 'net', 'org', 'gov', 'edu', 'co', 'ac'}
        if len(parts) >= 3 and parts[-1] and len(parts[-1]) == 2 and parts[-2] in common_second_level:
            return '.'.join(parts[-3:])
        else:
            return '.'.join(parts[-2:])

def normalize_script_url(url: str, collapse_subdomains: bool = False) -> str | None:
    if not url or not url.strip():
        return None
    raw = url.strip()
    if raw.startswith("//"):
        raw = "https:" + raw
    try:
        p = urlparse(raw)
    except Exception:
        return None
    scheme = p.scheme or "https"
    netloc = (p.netloc or "").lower()
    path = p.path or ""
    if not netloc:
        parts = path.split('/', 1)
        if parts and '.' in parts[0]:
            netloc = parts[0].lower()
            path = '/' + parts[1] if len(parts) > 1 else ''
        else:
            return raw
    netloc_no_port = netloc.split(':')[0]
    if collapse_subdomains:
        base = get_registrable_domain(netloc_no_port)
        if ':' in netloc:
            port = netloc.split(':', 1)[1]
            netloc = f"{base}:{port}"
        else:
            netloc = base
    else:
        netloc = netloc_no_port
    if path != '/':
        path = path.rstrip('/')
    normalized = f"{scheme}://{netloc}{path}"
    return normalized

def extract_cookie_prefix(cookie_str: str) -> str:
    if cookie_str is None:
        return ""
    s = cookie_str.strip()
    idx_eq = s.find('=')
    m = re.search(r'\d', s)
    idx_digit = m.start() if m else -1
    indices = [i for i in (idx_eq, idx_digit) if i != -1]
    if indices:
        i = min(indices)
        return s[:i].strip()
    else:
        return s

def process_root_dir(root_dir: str, collapse_subdomains: bool = False):
    results = {
        'consent': {},
        'non-func': {}
    }
    seen_pairs = set()
    for entry in sorted(os.listdir(root_dir)):
        dpath = os.path.join(root_dir, entry)
        if not os.path.isdir(dpath):
            continue
        name_lower = entry.lower()
        if 'consent' in name_lower:
            cat = 'consent'
        elif 'non-func' in name_lower:
            cat = 'non-func'
        else:
            continue
        for fname in sorted(os.listdir(dpath)):
            m = FILENAME_RE.match(fname)
            if not m:
                continue
            domain = m.group('domain')
            fpath = os.path.join(dpath, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                print(f"Warning: failed to read/parse {fpath}: {e}")
                continue
            cookie = data.get('cookie', "")
            cookie_prefix = extract_cookie_prefix(cookie)
            pair = (domain, cookie_prefix)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            srcs = data.get('source_scripts', [])
            if not isinstance(srcs, list):
                continue
            for raw in srcs:
                if not raw or not raw.strip():
                    continue
                norm = normalize_script_url(raw, collapse_subdomains=collapse_subdomains)
                if norm is None:
                    continue
                if norm not in results[cat]:
                    results[cat][norm] = {'count': 0, 'examples': set()}
                results[cat][norm]['count'] += 1
                results[cat][norm]['examples'].add(raw)
    return results

def print_results(results: dict):
    for cat in ('consent', 'non-func'):
        scripts = results.get(cat, {})
        total_norm = len(scripts)
        total_occurrences = sum(info.get('count', 0) for info in scripts.values())
        total_examples = sum(len(info.get('examples', [])) for info in scripts.values())
        print(f"\nCategory: {cat}")
        print(f"Unique normalized source scripts: {total_norm}")
        print(f"Total occurrences (counted with duplicates): {total_occurrences}")
        print(f"Total distinct example URLs collected: {total_examples}\n")

def save_outputs(results: dict, out_path: str):
    """
    Build summary with counts and examples, and sort each category by count desc.
    Output format (per category) is a list of items:
      [ { "normalized": "...", "count": N, "examples": [...] }, ... ]
    """
    summary = {}
    for cat, scripts in results.items():
        # prepare list of tuples (norm, count, examples_list)
        items = []
        for norm, info in scripts.items():
            ex_list = sorted(list(info.get('examples', [])))
            cnt = int(info.get('count', 0))
            items.append((norm, cnt, ex_list))
        # sort by count desc, then norm asc for stability
        items.sort(key=lambda x: (-x[1], x[0]))
        # convert to list of dicts maintaining order
        summary[cat] = [
            {"normalized": norm, "count": cnt, "examples": ex_list}
            for norm, cnt, ex_list in items
        ]
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Saved summary to {out_path}")

def main():
    parser = argparse.ArgumentParser(description="Collect unique source scripts (ignoring query parameters).")
    parser.add_argument('-d', '--dir', required=True, help='Root directory containing subdirectories (consent / non-func).')
    parser.add_argument('--out', help='Optional JSON output path (default: ./scripts_summary.json).', default='scripts_summary.json')
    parser.add_argument('-c', '--collapse-subdomains', action='store_true',
                        help='If set, treat all subdomains of the same registrable domain as one (e.g. a.example.com and b.example.com -> example.com). Default: off.')
    args = parser.parse_args()

    root = args.dir
    if not os.path.isdir(root):
        print(f"Error: {root} is not a directory")
        return

    results = process_root_dir(root, collapse_subdomains=args.collapse_subdomains)
    print_results(results)
    save_outputs(results, args.out)

if __name__ == '__main__':
    main()
