#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simplified_participation_stats.py

Usage:
  python simplified_participation_stats.py -d /path/to/root_dir --out participation_summary.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
from typing import Dict, Any, List
from urllib.parse import urlparse

FILENAME_RE = re.compile(r'^(?P<domain>[^_]+)_.+_path\.json$')

def get_registrable_domain(host: str) -> str:
    host = (host.split(':')[0] if host else '').lower()
    if not host:
        return ''
    if host == 'localhost' or re.match(r'^\d+\.\d+\.\d+\.\d+$', host):
        return host
    try:
        import tldextract
        ext = tldextract.extract(host)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}"
        return host
    except Exception:
        parts = host.split('.')
        if len(parts) <= 2:
            return host
        common_second_level = {'com', 'net', 'org', 'gov', 'edu', 'co', 'ac'}
        if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in common_second_level:
            return '.'.join(parts[-3:])
        return '.'.join(parts[-2:])

def script_is_first_party(script_url: str, site_domain: str) -> bool:
    if not isinstance(script_url, str) or not script_url.strip():
        return False
    raw = script_url.strip()
    # relative path -> first-party
    if raw.startswith('/') or not re.search(r'https?://|//', raw):
        return True
    try:
        # handle //foo style
        p = urlparse(raw if raw.startswith('http') else ('https:' + raw if raw.startswith('//') else raw))
    except Exception:
        return False
    script_host = p.netloc.split(':')[0]
    return get_registrable_domain(script_host) == get_registrable_domain(site_domain)

def _init_category() -> Dict[str, int]:
    return {
        'total_files': 0,
        'files_missing_participation': 0,
        'files_failed_to_parse': 0,
        'single_script': 0,
        'single_first': 0,
        'single_third': 0,
        'single_unknown_party': 0,   # when total_participated_scripts is int but no URLs
        'multi_script': 0,
        'multi_first_first': 0,
        'multi_first_third': 0,
        'multi_third_third': 0,
        'multi_unknown_party': 0     # when total_participated_scripts is int but no URLs
    }

def _pct(x: int, denom: int) -> float:
    return round((x / denom * 100) if denom else 0.0, 2)

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

def analyze_dir(root_dir: str) -> (Dict[str, Any], Dict[str, Any]):
    stats = {
        'consent': _init_category(),
        'non-func': _init_category()
    }
    # details: collect domain-level examples for each bucket
    details = {
        'consent': {
            'single_first': [],       # list of {domain, cookie_prefix, script}
            'single_third': [],
            'single_unknown': [],     # when tp is int but <=1, store domain+count
            'multi_first_first': [],  # list of {domain, cookie_prefix, scripts}
            'multi_first_third': [],
            'multi_third_third': [],
            'multi_unknown': []       # when tp is int but >1
        },
        'non-func': {
            'single_first': [],
            'single_third': [],
            'single_unknown': [],
            'multi_first_first': [],
            'multi_first_third': [],
            'multi_third_third': [],
            'multi_unknown': []
        }
    }

    seen_pairs = set()
    for entry in sorted(os.listdir(root_dir)):
        dpath = os.path.join(root_dir, entry)
        if not os.path.isdir(dpath):
            continue
        lname = entry.lower()
        if 'consent' in lname:
            cat = 'consent'
        elif 'non-func' in lname:
            cat = 'non-func'
        else:
            continue

        for fname in sorted(os.listdir(dpath)):
            m = FILENAME_RE.match(fname)
            if not m:
                continue
            site_domain = m.group('domain')
            fpath = os.path.join(dpath, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                stats[cat]['files_failed_to_parse'] += 1
                continue
            cookie = data.get('cookie', "")
            cookie_prefix = extract_cookie_prefix(cookie)
            pair = (site_domain, cookie_prefix)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            stats[cat]['total_files'] += 1
            tp = data.get('total_participated_scripts', None)

            if tp is None:
                stats[cat]['files_missing_participation'] += 1
                continue

            if isinstance(tp, list):
                scripts = [s for s in tp if isinstance(s, str) and s.strip()]
                n = len(scripts)
                if n <= 1:
                    stats[cat]['single_script'] += 1
                    if n == 1:
                        script = scripts[0]
                        if script_is_first_party(script, site_domain):
                            stats[cat]['single_first'] += 1
                            details[cat]['single_first'].append({
                                'domain': site_domain,
                                'cookie_prefix': cookie_prefix,
                                'script': script
                            })
                        else:
                            stats[cat]['single_third'] += 1
                            details[cat]['single_third'].append({
                                'domain': site_domain,
                                'cookie_prefix': cookie_prefix,
                                'script': script
                            })
                    else:
                        # zero scripts - still count as single but put into unknown bucket
                        details[cat]['single_unknown'].append({
                            'domain': site_domain,
                            'cookie_prefix': cookie_prefix,
                            'scripts': []
                        })
                else:
                    stats[cat]['multi_script'] += 1
                    parties = ['first' if script_is_first_party(s, site_domain) else 'third' for s in scripts]
                    uniq = set(parties)
                    if uniq == {'first'}:
                        stats[cat]['multi_first_first'] += 1
                        details[cat]['multi_first_first'].append({
                            'domain': site_domain,
                            'cookie_prefix': cookie_prefix,
                            'scripts': scripts
                        })
                    elif uniq == {'third'}:
                        stats[cat]['multi_third_third'] += 1
                        details[cat]['multi_third_third'].append({
                            'domain': site_domain,
                            'cookie_prefix': cookie_prefix,
                            'scripts': scripts
                        })
                    else:
                        stats[cat]['multi_first_third'] += 1
                        details[cat]['multi_first_third'].append({
                            'domain': site_domain,
                            'cookie_prefix': cookie_prefix,
                            'scripts': scripts
                        })

            elif isinstance(tp, int):
                if tp <= 1:
                    stats[cat]['single_script'] += 1
                    stats[cat]['single_unknown_party'] += 1
                    details[cat]['single_unknown'].append({
                        'domain': site_domain,
                        'cookie_prefix': cookie_prefix,
                        'count': int(tp)
                    })
                else:
                    stats[cat]['multi_script'] += 1
                    stats[cat]['multi_unknown_party'] += 1
                    details[cat]['multi_unknown'].append({
                        'domain': site_domain,
                        'cookie_prefix': cookie_prefix,
                        'count': int(tp)
                    })
            else:
                stats[cat]['files_missing_participation'] += 1

    # add percentages
    for cat in ('consent', 'non-func'):
        c = stats[cat]
        c['single_first_pct'] = _pct(c['single_first'], c['single_script'])
        c['single_third_pct'] = _pct(c['single_third'], c['single_script'])
        c['multi_first_first_pct'] = _pct(c['multi_first_first'], c['multi_script'])
        c['multi_first_third_pct'] = _pct(c['multi_first_third'], c['multi_script'])
        c['multi_third_third_pct'] = _pct(c['multi_third_third'], c['multi_script'])

    return stats, details

def print_report(stats: Dict[str, Any]) -> None:
    for cat in ('consent', 'non-func'):
        c = stats[cat]
        print(f"\nCategory: {cat}")
        print(f"  Total files scanned: {c['total_files']}")
        print(f"  Files missing participation: {c['files_missing_participation']}")
        print(f"  Files failed to parse: {c['files_failed_to_parse']}")
        print(f"  Single-script files: {c['single_script']}")
        print(f"    first-party: {c['single_first']} ({c['single_first_pct']}%)")
        print(f"    third-party: {c['single_third']} ({c['single_third_pct']}%)")
        print(f"  Multi-script files: {c['multi_script']}")
        print(f"    first+first: {c['multi_first_first']} ({c['multi_first_first_pct']}%)")
        print(f"    first+third: {c['multi_first_third']} ({c['multi_first_third_pct']}%)")
        print(f"    third+third: {c['multi_third_third']} ({c['multi_third_third_pct']}%)")

def main():
    parser = argparse.ArgumentParser(description='Simplified participation statistics by category.')
    parser.add_argument('-d', '--dir', required=True, help='Root directory containing subdirectories (consent / non-func).')
    parser.add_argument('--out', default='collaboration_summary.json', help='Output JSON summary path.')
    args = parser.parse_args()

    root = args.dir
    if not os.path.isdir(root):
        print(f"Error: {root} is not a directory")
        return

    stats, details = analyze_dir(root)
    out_obj = {
        'stats': stats,
        'details': details
    }
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(out_obj, f, indent=2, ensure_ascii=False)

    print(f"Saved summary to {args.out}")
    print_report(stats)

if __name__ == '__main__':
    main()
