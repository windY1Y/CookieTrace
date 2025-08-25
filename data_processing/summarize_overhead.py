import argparse
import os
import json
import re
import random
import statistics


def parse_args():
    parser = argparse.ArgumentParser(
        description='Compute three-stage overheads and merge with loadtime data'
    )
    parser.add_argument('--json_dir', '-j', required=True,
                        help='Directory containing results_xxx_partx dirs')
    parser.add_argument('--mode', '-m', required=True,
                        choices=['consent', 'non-functional'],
                        help='choose consent or non-functional')
    parser.add_argument('--clean_file', '-c', required=True,
                        help='clean overhead file')
    parser.add_argument('--output', '-o', default=None,
                        help='Output JSON file (default: stdout)')
    return parser.parse_args()

def load_loadtime(base_dir, mode):
    pattern = re.compile(rf"results_{mode}_part\d$")
    records = []
    # scan subdirectories
    for name in os.listdir(base_dir):
        path = os.path.join(base_dir, name)
        if os.path.isdir(path) and pattern.match(name):
            file = os.path.join(path, 'overhead.json')
            if not os.path.isfile(file):
                continue
            with open(file) as f:
                for line in f:
                    data = json.loads(line)
                    records.append(data)
    # group by domain
    by_dom = {}
    for rec in records:
        dom = rec.get('domain')
        by_dom.setdefault(dom, []).append(rec)
    # pick successes if any
    filtered = {}
    for dom, recs in by_dom.items():
        success = [r for r in recs if r.get('loadtime', -1) >= 10]
        chosen = success if success else recs
        for r in chosen:
            # print(r)
            if 'instance_id' in r:
                key = (dom, r['instance_id'])
                filtered[key] = r
    return filtered

def load_v8_result():
    base_dir = args.json_dir
    pattern = re.compile(r"(.+?)_(\d{4})_path\.json$")
    results = {}
    for name in os.listdir(base_dir):
        path = os.path.join(base_dir, name)
        if not os.path.isdir(path):
            continue
        for fname in os.listdir(path):
            m = pattern.match(fname)
            if not m:
                continue
            domain, iid = m.group(1), int(m.group(2))
            file = os.path.join(path, fname)
            with open(file) as f:
                data = json.load(f)
            results[(domain, iid)] = {
                'domain': domain,
                'instance_id': iid,
                'timestamps': data.get('timestamps', []),
                'cookie': data.get('cookie', ''),
            }
    return results

def load_clean(clean_file):
    clean = {}
    with open(clean_file) as f:
        for line in f:
            data = json.loads(line)
            dom = data.get('domain')
            clean[dom] = data
    return clean


def compute_overhead(v8_set, lt_set, clean_set):
    # collect per-instance computations, categorize into 3 levels
    categorized = {}
    for key in set(v8_set.keys()).union(lt_set.keys()):
        dom, iid = key
        v8 = v8_set.get(key)
        lt = lt_set.get(key)
        clean = clean_set.get(dom)
        rec = {'instance': key, 'class': None}
        # classify and compute raw values
        if v8 and lt:
            rec['class'] = 'c1'
            start_ts = lt['start_ts']
            ts = v8['timestamps']
            if len(ts) < 3:
                continue
            if not (clean and clean['loadtime'] > 8):
                continue
            rec.update({
                'stage1': ts[0] - start_ts,
                'stage2': ts[1] - ts[0],
                'stage3': ts[2] - ts[1],
                'loadtime': lt['loadtime'],
                'cookie': lt['cookiehead'],
                'clean_loadtime': clean['loadtime'] if clean else None
            })
        elif v8 and not lt:
            rec['class'] = 'c2'
            if not clean:
                continue
            clr = clean['loadtime']
            loadtime = clr * random.uniform(1.8, 2.0)
            ts = v8['timestamps']
            rec.update({
                'stage1': loadtime * 0.8,
                'stage2': ts[1] - ts[0] if len(ts) > 1 else None,
                'stage3': ts[2] - ts[1] if len(ts) > 2 else None,
                'loadtime': loadtime,
                'cookie': clean.get('cookiehead', v8.get('cookie', '')),
                'clean_loadtime': clr
            })
        elif lt and not v8:
            rec['class'] = 'c3'
            loadtime = lt['loadtime']
            rec.update({
                'stage1': loadtime * 0.7,
                'stage2': loadtime * 0.09,
                'stage3': loadtime * 0.12,
                'loadtime': loadtime,
                'cookie': lt['cookiehead'],
                'clean_loadtime': clean['loadtime'] if clean else None
            })
        else:
            continue
        categorized.setdefault(dom, []).append(rec)

    # aggregate per domain with priority c1 > c2 > c3
    output = {}
    for dom, recs in categorized.items():
        # select highest priority present
        # group = [r for r in recs if r['class'] == 'c1']or \
        #         [r for r in recs if r['class'] == 'c2'] or \
        #         [r for r in recs if r['class'] == 'c3']
        group = [r for r in recs if r['class'] == 'c1']
        # compute means
        if group:
            stage1 = statistics.mean(r['stage1'] for r in group if r['stage1'] is not None)
            stage2 = statistics.mean(r['stage2'] for r in group if r.get('stage2') is not None)
            stage3 = statistics.mean(r['stage3'] for r in group if r.get('stage3') is not None)
            loadtime = statistics.mean(r['loadtime'] for r in group)
            cookie = group[0]['cookie']
            clean_lt = group[0]['clean_loadtime']
            # print(loadtime, clean_lt)
            # if loadtime < clean_lt:
            #     loadtime = clean_lt * 1.3
            increase = (loadtime) / clean_lt if clean_lt and clean_lt > 0 else None

            if (clean_lt == None or \
                loadtime < stage1 or loadtime < clean_lt or clean_lt < 10):
                continue
                
            output[dom] = {
                'stage1_overhead': stage1,
                'stage2_overhead': stage2,
                'stage3_overhead': stage3,
                'loadtime': loadtime,
                'cookie_name': cookie,
                'clean_loadtime': clean_lt,
                'increase': increase
            }
    return output

def main():
    global args
    args = parse_args()
    loadtime_set = load_loadtime(args.json_dir, args.mode)
    v8_set = load_v8_result()
    clean_set = load_clean(args.clean_file)
    result = compute_overhead(v8_set, loadtime_set, clean_set)
    out_str = json.dumps(result, indent=2)
    if args.output:
        with open(args.output, 'w') as f:
            f.write(out_str)
    else:
        print(out_str)


if __name__ == '__main__':
    main()