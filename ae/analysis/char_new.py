#!/usr/bin/env python3
"""
process_domain_jsons_updated.py

Adds deduplication: for each path.json, extract cookie_prefix (chars before first digit).
Use (domain, cookie_prefix) as key to deduplicate: if already seen, skip that path + its paired source(s).

Also: categorize immediate subdirectories into "consent" (name contains 'consent', case-insensitive)
and "non-func" (others). Output per-category counts in global summary.

Minimal modification: count how many consent groups are "cdnmanager" groups.
A group is considered cdnmanager if, when reading each path_file's cookie, the substring
before the first digit or before the first '=' (whichever encountered first) equals "__cmpconsentx"
(case-insensitive).
"""
import os
import re
import json
import argparse
from collections import Counter
from typing import Dict, List, Any, Optional

FNAME_RE = re.compile(r"^(.+?)_(\d{4})(?:_path)?\.json$", re.IGNORECASE)
FIRST_DIGIT_RE = re.compile(r"\d")

def find_pairs(dirpath: str) -> Dict[str, Dict[str, List[str]]]:
    pairs: Dict[str, Dict[str, List[str]]] = {}
    for fname in sorted(os.listdir(dirpath)):
        m = FNAME_RE.match(fname)
        if not m:
            continue
        id4 = m.group(1) + '_' + m.group(2)
        is_path = fname.lower().endswith("_path.json")
        entry = pairs.setdefault(id4, {'source': [], 'path': []})
        entry['path' if is_path else 'source'].append(os.path.join(dirpath, fname))
    return pairs

def load_json_safe(path: str) -> Optional[Any]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] failed to read/parse JSON {path}: {e}")
        return None

def parse_stack_trace_entry(entry: str) -> List[str]:
    return [p.strip() for p in entry.split(',')]

def process_source_file(path: str) -> Dict[str, Any]:
    data = load_json_safe(path)
    warn: List[str] = []
    if data is None:
        return {'warnings': [f'failed to load {path}'], 'source_file': os.path.basename(path)}
    if not isinstance(data, list):
        if isinstance(data, dict) and 'items' in data and isinstance(data['items'], list):
            data = data['items']
        else:
            return {'warnings': ['expected list at top-level for source-file'], 'source_file': os.path.basename(path)}

    total = len(data)
    forward_dependent_var_count = 0
    track_depth_sum = 0.0
    track_depth_count = 0
    func_counter: Counter = Counter()

    for i, elem in enumerate(data):
        if not isinstance(elem, dict):
            warn.append(f'element {i} not dict, skipped')
            continue
        is_forward = elem.get('is_forward_tracking', False)
        if isinstance(is_forward, bool):
            if is_forward:
                forward_dependent_var_count += 1
        else:
            if str(is_forward).lower() == 'true':
                forward_dependent_var_count += 1

        td = elem.get('track_depth')
        if isinstance(td, (int, float)):
            track_depth_sum += float(td)
            track_depth_count += 1
        else:
            try:
                ftd = float(td)
                track_depth_sum += ftd
                track_depth_count += 1
            except Exception:
                pass

        fs = elem.get('function_start_position')
        fe = elem.get('function_end_position')
        if fs is None or fe is None:
            continue
        try:
            key = (int(fs), int(fe))
            func_counter[key] += 1
        except Exception:
            warn.append(f'element {i} has non-int function positions: {fs},{fe}')

    avg_td = (track_depth_sum / track_depth_count) if track_depth_count > 0 else None
    functions_map = {f"{fs}_{fe}": cnt for (fs, fe), cnt in func_counter.items()}
    per_function_percent_map = {f"{fs}_{fe}": (cnt / total if total > 0 else 0.0)
                                for (fs, fe), cnt in func_counter.items()}


    if per_function_percent_map:
        main_function_percent = max(per_function_percent_map.values())
    else:
        main_function_percent = 0.0

    return {
        'source_file': os.path.basename(path),
        'total': total,
        'forward_dependent_var_count': forward_dependent_var_count,
        'avg_track_depth': avg_td,
        '__track_depth_sum__': track_depth_sum,
        '__track_depth_count__': track_depth_count,
        'functions': functions_map,
        'per_function_percent': per_function_percent_map,
        'main_function_percent': main_function_percent,
        'warnings': warn
    }

def process_path_file(path: str) -> Dict[str, Any]:
    data = load_json_safe(path)
    warn: List[str] = []
    if data is None or not isinstance(data, dict):
        return {'warnings': [f'failed to load or expected dict for path-file {path}'], 'path_file': os.path.basename(path)}
    forward_call_num = data.get('forward_call_num')
    try:
        forward_call_num = int(forward_call_num) if forward_call_num is not None else None
    except Exception:
        warn.append(f'non-int forward_call_num: {forward_call_num}')
        forward_call_num = None

    stack = data.get('stack_trace', [])
    if not isinstance(stack, list):
        warn.append('stack_trace not a list')
        stack = []

    true_count = 0
    for entry in stack:
        if not isinstance(entry, str):
            continue
        parts = parse_stack_trace_entry(entry)
        if len(parts) >= 2 and parts[1].lower() == 'true':
            true_count += 1

    return {
        'path_file': os.path.basename(path),
        'cookie': data.get('cookie',''),
        'forward_call_num': forward_call_num,
        'stack_async_count': true_count,
        'stack_total': len(stack),
        'warnings': warn
    }

def aggregate_results(source_results: Dict[str, Dict[str, Any]], path_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    total_source_elements = 0
    total_source_forward = 0
    total_td_sum = 0.0
    total_td_cnt = 0
    s_warnings: List[str] = []

    # track processed (valid) source-file count for averages
    processed_source_files = 0

    # per-source-file distinct function counts
    distinct_functions_per_file: Dict[str, int] = {}
    sum_distinct_functions = 0


    sum_main_function_percent = 0.0


    num_source_files_with_single_function = 0

    for key, res in source_results.items():
        # skip entries that didn't parse properly (same behavior as before)
        if 'total' not in res:
            s_warnings.extend(res.get('warnings', []))
            continue

        processed_source_files += 1
        total_source_elements += res['total']
        total_source_forward += res['forward_dependent_var_count']

        td_sum = res.get('__track_depth_sum__', 0.0)
        td_cnt = res.get('__track_depth_count__', 0)
        total_td_sum += float(td_sum)
        total_td_cnt += int(td_cnt)

        funcs = res.get('functions', {})  # mapping "fs_fe" -> count

        # distinct function count for this source file
        distinct_count = len(funcs)
        distinct_functions_per_file[res.get('source_file', key)] = distinct_count
        sum_distinct_functions += distinct_count


        if distinct_count == 1:
            num_source_files_with_single_function += 1

        # collect main_function_percent if present
        sum_main_function_percent += float(res.get('main_function_percent', 0.0))

        s_warnings.extend(res.get('warnings', []))

    # compute mean distinct functions per processed source file
    mean_distinct_functions = (sum_distinct_functions / processed_source_files) if processed_source_files > 0 else None

    # compute average main_function_percent across processed source files
    mean_main_function_percent = (sum_main_function_percent / processed_source_files) if processed_source_files > 0 else None

    # compute global average track depth (same as before)
    global_avg_track_depth = (total_td_sum / total_td_cnt) if total_td_cnt > 0 else None

    # path-level aggregates (unchanged)
    total_path_files = 0
    sum_forward_call_num = 0
    sum_async_stack_count = 0
    sum_paths_with_async = 0
    for res in path_results.values():
        if 'forward_call_num' not in res:
            continue
        total_path_files += 1
        if res['forward_call_num'] is not None:
            sum_forward_call_num += int(res['forward_call_num'])
        sum_async_stack_count += int(res.get('stack_async_count', 0))
        if int(res.get('stack_async_count', 0)) > 0:
            sum_paths_with_async += 1

    mean_async_stack_count = (sum_async_stack_count / total_path_files) if total_path_files > 0 else None
    mean_forward_call_num = (sum_forward_call_num / total_path_files) if total_path_files > 0 else None

    return {
        'source_global': {
            'total_source_files': processed_source_files,
            'total_source_elements': total_source_elements,
            'total_source_forward_dependent': total_source_forward,
            'distinct_functions_per_source_file': distinct_functions_per_file,
            'mean_distinct_functions_per_source_file': mean_distinct_functions,
            'global_avg_track_depth': global_avg_track_depth,

            'mean_main_function_percent': mean_main_function_percent,

            'num_source_files_with_single_function': num_source_files_with_single_function
        },
        'path_global': {
            'total_path_files': total_path_files,
            'mean_forward_call_num': mean_forward_call_num,
            'sum_paths_with_async': sum_paths_with_async,
            'mean_async_stack_count': mean_async_stack_count
        }
    }

def extract_cookie_prefix(cookie_value: str) -> Optional[str]:
    """
    Return substring of cookie_value up to (but not including) the first digit.
    If no digit found, attempt fallback by taking part before '=' or return None.
    """
    if not isinstance(cookie_value, str):
        return None
    s = cookie_value.strip().lstrip('"').lstrip("'")
    m = FIRST_DIGIT_RE.search(s)
    if m:
        prefix = s[:m.start()].strip()
        if prefix == '':
            if '=' in s:
                return s.split('=', 1)[0].strip()
            return None
        return prefix
    if '=' in s:
        return s.split('=', 1)[0].strip()
    return None

def is_consent_dirname(name: str) -> bool:
    return 'consent' in name.lower()

def process_all(dirpath: str, out_dir: str) -> Dict[str, Any]:
    """
    dirpath may contain multiple subdirectories. We categorize each immediate subdirectory
    as 'consent' if its name contains 'consent' (case-insensitive), otherwise 'non-func'.
    Root-level files are classified as 'non-func'.
    """
    # collect a mapping key -> {'lists': {...}, 'category': 'consent'|'non-func'}
    pairs: Dict[str, Dict[str, Any]] = {}

    # root-level pairs (classify as non-func)
    root_pairs = find_pairs(dirpath)
    for id4, lists in root_pairs.items():
        pairs[f"__root__{id4}"] = {'lists': lists, 'category': 'non-func'}

    # collect from immediate subdirectories
    for entry in os.listdir(dirpath):
        full = os.path.join(dirpath, entry)
        if not os.path.isdir(full):
            continue
        local_pairs = find_pairs(full)
        category = 'consent' if is_consent_dirname(entry) else 'non-func'
        for id4, lists in local_pairs.items():
            key = f"{entry}__{id4}"
            pairs[key] = {'lists': lists, 'category': category}

    if not pairs:
        print(f"[WARN] no matching files found in {dirpath}")
    source_results: Dict[str, Dict[str, Any]] = {}
    path_results: Dict[str, Dict[str, Any]] = {}

    os.makedirs(out_dir, exist_ok=True)

    seen_keys = set()  # set of (domain, cookie_prefix) we've processed

    # First pass: dedup based on path cookie prefixes.
    groups_to_process: List[Any] = []  # list of tuples (id_key, lists, category)
    group_is_cdn: Dict[str, bool] = {}  # record whether a group contains a cdnmanager cookie prefix

    for id_key, rec in pairs.items():
        lists = rec['lists']
        category = rec.get('category', 'non-func')
        skip_group = False
        for p_path in lists.get('path', []):
            fname = os.path.basename(p_path)
            m = FNAME_RE.match(fname)
            domain = m.group(1) if m else fname.split('_')[0]
            data = load_json_safe(p_path)
            if not data or not isinstance(data, dict):
                continue
            cookie_val = data.get('cookie')
            prefix = extract_cookie_prefix(cookie_val) if cookie_val is not None else None
            if prefix is None:
                continue
            key = (domain, prefix)
            if key in seen_keys:
                skip_group = True
                break
        if skip_group:
            continue
        # not skipped -> add all path prefixes to seen_keys; also detect cdnmanager presence
        found_cdn = False
        for p_path in lists.get('path', []):
            fname = os.path.basename(p_path)
            m = FNAME_RE.match(fname)
            domain = m.group(1) if m else fname.split('_')[0]
            data = load_json_safe(p_path)
            if not data or not isinstance(data, dict):
                continue
            cookie_val = data.get('cookie')
            prefix = extract_cookie_prefix(cookie_val) if cookie_val is not None else None
            if prefix is None:
                continue
            key = (domain, prefix)
            seen_keys.add(key)

            try:
                if isinstance(prefix, str) and prefix.lower() == '__cmpconsentx':
                    found_cdn = True
            except Exception:
                pass
        group_is_cdn[id_key] = found_cdn
        groups_to_process.append((id_key, lists, category))

    # Now process only the groups that passed dedup
    for id_key, lists, category in groups_to_process:
        for s_path in lists.get('source', []):
            key = os.path.basename(s_path)
            source_results[key] = process_source_file(s_path)
        for p_path in lists.get('path', []):
            key = os.path.basename(p_path)
            path_results[key] = process_path_file(p_path)

    # Global aggregates (path/source)
    global_summary = aggregate_results(source_results, path_results)

    # Compute per-category counts based on groups_to_process
    cat_counts = {
        'consent': {'groups': 0, 'path_files': 0, 'cdnmanager_groups': 0, 'cdnmanager_ratio': None},
        'non-func': {'groups': 0, 'path_files': 0}
    }
    for _id, lists, category in groups_to_process:
        if category not in cat_counts:
            category = 'non-func'
        cat_counts[category]['groups'] += 1
        cat_counts[category]['path_files'] += len(lists.get('path', []))

        if category == 'consent':
            if group_is_cdn.get(_id, False):
                cat_counts['consent']['cdnmanager_groups'] += 1


    consent_groups = cat_counts['consent']['groups']
    if consent_groups > 0:
        cat_counts['consent']['cdnmanager_ratio'] = (cat_counts['consent']['cdnmanager_groups'] / consent_groups)
    else:
        cat_counts['consent']['cdnmanager_ratio'] = None

    # attach category counts into global_summary
    global_summary['category_counts'] = cat_counts

    # Write global summary
    global_out_path = os.path.join(out_dir, '_global_summary.json')
    try:
        with open(global_out_path, 'w', encoding='utf-8') as f:
            json.dump(global_summary, f, ensure_ascii=False, indent=2)
        print(f"Saved global summary to {global_out_path}")
    except Exception as e:
        print(f"[ERROR] failed to save global summary to {global_out_path}: {e}")

    # Write combined per-domain summaries (one file per base name)
    for id_key, lists, category in groups_to_process:
        for s_path in lists.get('source', []):
            s_basename = os.path.basename(s_path)
            base_no_ext = s_basename[:-5] if s_basename.lower().endswith('.json') else s_basename
            out_name = f"{base_no_ext}_summary.json"
            combined: Dict[str, Any] = {}
            if s_basename in source_results:
                combined['source'] = source_results[s_basename]
            expected_path_basename = f"{base_no_ext}_path.json"
            if expected_path_basename in path_results:
                combined['path'] = path_results[expected_path_basename]
            try:
                with open(os.path.join(out_dir, out_name), 'w', encoding='utf-8') as f:
                    json.dump(combined, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[ERROR] failed to write combined summary {out_name}: {e}")

    return global_summary

def main():
    p = argparse.ArgumentParser(description="Process source (domain_xxxx.json) and path (domain_xxxx_path.json) files.")
    p.add_argument('--dir', type=str, default='.', help='input directory containing json files')
    p.add_argument('--out', type=str, default='.', help='output directory for summaries')
    args = p.parse_args()

    summary = process_all(args.dir, args.out)

    # print concise aggregates
    s_global = summary.get('source_global', {})
    p_global = summary.get('path_global', {})
    cat_counts = summary.get('category_counts', {})
    print("=== Source-files Summary ===")
    print(f"Total source-files processed: {s_global.get('total_source_files')}")
    print(f"Total elements across source-files: {s_global.get('total_source_elements')}")
    print(f"Total elements with is_forward_tracking==true: {s_global.get('total_source_forward_dependent')}")
    print(f"Global average track_depth: {s_global.get('global_avg_track_depth') or 'N/A'}")

    print(f"Mean main_function_percent across source-files: {s_global.get('mean_main_function_percent') or 'N/A'}")
    print(f"Number of source-files with exactly 1 function: {s_global.get('num_source_files_with_single_function', 0)}")

    print("\n=== Path-files Summary ===")
    print(f"Total path-files processed: {p_global.get('total_path_files')}")
    print(f"Mean forward_call_num across path-files: {p_global.get('mean_forward_call_num')}")

    print("\n=== Category Counts (processed after dedup) ===")
    print(f"Consent groups: {cat_counts.get('consent', {}).get('groups', 0)}, "
          f"consent path-files: {cat_counts.get('consent', {}).get('path_files', 0)}")
    # print cdnmanager info if available
    cdn_groups = cat_counts.get('consent', {}).get('cdnmanager_groups', 0)
    cdn_ratio = cat_counts.get('consent', {}).get('cdnmanager_ratio')
    if cdn_ratio is not None:
        print(f"Consent cdnmanager groups: {cdn_groups} ({cdn_ratio:.2%})")
    else:
        print(f"Consent cdnmanager groups: {cdn_groups} (N/A)")

    print(f"Non-func groups: {cat_counts.get('non-func', {}).get('groups', 0)}, "
          f"non-func path-files: {cat_counts.get('non-func', {}).get('path_files', 0)}")

if __name__ == '__main__':
    main()
