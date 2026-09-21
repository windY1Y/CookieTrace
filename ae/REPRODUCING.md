# Experiments and supplied scripts

All commands below are run from the CookieTrace repository root. Paths in uppercase are input parameters: replace them with the location of the records you select for analysis. Each experiment states what its scripts compute; running an aggregation script and collecting a fresh browser trace are separate operations.

## Script map

| Entry | Responsibility | Paper experiment |
|---|---|---|
| `measure/single_site.sh` | Launch CookieTrace for a website and target cookie | Single-site data collection |
| `ae/run.sh` | Build the runtime image; check the browser; run the local demo or one target in an isolated container | E1; portable single-site collection |
| `ae/check_effectiveness.py` | Recompute TP/FP/FN-based metrics from the two effectiveness CSVs | E2; CookieTrace source-accuracy entries in Tables II-III |
| `data_processing/summarize_overhead.py` | Join browser timestamps, instrumented load-time records, and vanilla measurements; compute stage intervals and slowdown | E3; Figure 4 analysis |
| `data_processing/compute_avg_time.py` | Average numeric fields in the per-site overhead JSON | E3; overall performance summaries |
| `ae/analysis/char_new.py` | Summarize paired source/path records, forward dependence, depths, functions, and dataset categories | E4; underlying source-characterization statistics |
| `ae/analysis/draw_cdf_forward_call_num.py` | Plot the forward-call-count distribution | E4; Figure 2 |
| `ae/analysis/draw_forward_call_dependent.py` | Plot the distribution of forward-dependent source fractions | E4; Figure 3 |
| `ae/analysis/draw_kde.py` | Compare propagation-depth and stack-depth distributions | E4; Figure 5 |
| `ae/analysis/collect_source_scripts.py` | Normalize source-script URLs and aggregate their counts and examples | E4; Table IV source-script analysis |
| `ae/analysis/aggregate_by_category.py` | Aggregate classified script entries by category | E4; Figure 6 category analysis |
| `ae/analysis/collboration.py` | Classify single-/multi-script participation and first-/third-party combinations using `total_participated_scripts` | E4; collaboration analysis associated with Table V |
| `data_processing/characterization/` | Source-domain, party, category, and cookie-decoding analyses | Additional characterization statistics |

`collboration.py` retains its original filename spelling. Its participation input is distinct from the `source_scripts` field consumed by source-script analysis.

## E1: run CookieTrace

Preparation and execution:

```bash
bash ae/run.sh --build
bash ae/run.sh --check
bash ae/run.sh --demo
```

`--build` builds the Debian runtime, not Chromium. A successful demo returns 0 and writes `status: success`, the target cookie `ct_demo_cookie=ct_demo_value`, and validated source/path JSON. Each run has a unique directory under `ae/results/`; keep its logs and raw files with the results.

For one live target:

```bash
bash ae/run.sh --url https://YOUR-SITE --cookie-name YOUR_COOKIE --timeout 600
```

The original entry is `bash measure/single_site.sh DOMAIN SCRIPT_PLACEHOLDER COOKIE_PREFIX`. Its browser/profile/proxy paths are configured inside the script. The portable launcher offers explicit path/proxy options and manages the engine's output-path mount. See `README.md` for cookie-prefix semantics, profiles, and completion checks.

## E2: source effectiveness — Tables II-III

Input: `statistics/effectiveness_original.csv` and `statistics/effectiveness_deduplicated.csv`.

```bash
python3 ae/check_effectiveness.py .
```

The checker excludes the final `Total` row, verifies its counts, and reports source-level micro and macro precision/recall.

| Quantity | Original set | Deduplicated set |
|---|---:|---:|
| Cookie samples | 160 | 85 |
| TP | 10,005 | 3,453 |
| FP | 128 | 58 |
| FN | 0 | 0 |
| Micro precision | 98.7368% | 98.3480% |
| Macro precision | 99.3242% | 99.4001% |
| Recall | 100% | 100% |

Micro precision is sum(TP)/(sum(TP)+sum(FP)); macro precision averages the per-cookie ratios. The paper's rounded 98.7% and 98.3% correspond to the micro-precision values above. This script checks the supplied count records. Single-site execution produces source/path traces for inspecting the contributing literals and script identities of an individual target.

## E3: performance — Figure 4

Inputs: a measurement root containing `results_consent_partN/` or `results_non-functional_partN/`, each with line-delimited `overhead.json` records; matching `DOMAIN_NNNN_path.json` files with timestamps; and a line-delimited vanilla-browser timing file.

```bash
mkdir -p ae/results/analysis
python3 data_processing/summarize_overhead.py \
  --json_dir MEASUREMENT_ROOT --mode consent \
  --clean_file VANILLA_TIMINGS.jsonl --output ae/results/analysis/overhead_consent.json
python3 data_processing/compute_avg_time.py < ae/results/analysis/overhead_consent.json
```

Repeat with `--mode non-functional` for that measurement group. The summarizer joins records by domain/instance, retains its `c1` class (both trace and load-time records), applies its load-time filters, and emits per-site `stage1_overhead`, `stage2_overhead`, `stage3_overhead`, `loadtime`, `clean_loadtime`, and `increase`. `increase` is the per-site instrumented/vanilla ratio; the averaging script reports the arithmetic mean of each numeric field. Preserve the resulting sample count with the averages.

The paper's reference values are 79.34 seconds mean instrumented load time and 2.71x slowdown, with approximately 95% of overhead in S1. Fresh timings should use matched browser versions, identical profile policies and network conditions, three repeats, and a 600-second timeout. The page-load endpoint is `document.readyState == complete`. The portable launcher's `elapsed_seconds` is its own trace-run duration, so use the supplied load-time records for this analysis. Hardware and live content affect fresh timing values.

## E4: source characteristics — Figures 2-3, 5-6 and Tables IV-V

Input records use the original `DOMAIN_NNNN.json` / `DOMAIN_NNNN_path.json` paired filenames. `RAW_ROOT` contains measurement subdirectories; directory names containing `consent` identify that category, while the other category is `non-func`. The summarizer deduplicates by domain and cookie prefix. Its outputs contain source and path summaries per case plus `_global_summary.json`.

```bash
mkdir -p ae/results/analysis/summary
python3 ae/analysis/char_new.py --dir RAW_ROOT --out ae/results/analysis/summary
python3 ae/analysis/draw_cdf_forward_call_num.py \
  --input ae/results/analysis/summary --out ae/results/analysis/figure2.png --method none
python3 ae/analysis/draw_forward_call_dependent.py \
  --input ae/results/analysis/summary --out ae/results/analysis/figure3.png \
  --method none --scale-factor 1
python3 ae/analysis/draw_kde.py \
  --input ae/results/analysis/summary --out ae/results/analysis/figure5.png --method none
python3 ae/analysis/collect_source_scripts.py \
  --dir RAW_ROOT --out ae/results/analysis/source_scripts.json
python3 ae/analysis/aggregate_by_category.py \
  --in CLASSIFIED_SCRIPTS.json --out ae/results/analysis/script_categories.json
python3 ae/analysis/collboration.py \
  --dir RAW_ROOT --out ae/results/analysis/collaboration.json
```

`CLASSIFIED_SCRIPTS.json` has category lists of script entries with `normalized`, `count`, and `categories` fields. It is the classified input to category aggregation; the unclassified `source_scripts.json` is not a replacement for it. The category script outputs category counts, not a rendered Figure 6 image. It can count an entry in more than one category. `--scale-factor 1` keeps histogram frequencies in actual observation units; `--method none` preserves the untrimmed observations. These commands make the analysis choices explicit.

Compare summary statistics and integer counts rather than plot styling. Paper reference points include 18.02 mean forward calls, mean propagation/stack depths 17.55/10.63, and 45/522 distinct consent/unnecessary-cookie source scripts. Table V lists consent counts `0, 7, 1, 12, 1267` and unnecessary-cookie counts `499, 6202, 23, 499, 1273`, in published row order. Use the same dataset, participation definition, URL normalization, and deduplication policy when comparing counts. The full study contains 9,783 cookies on 6,995 sites.

The original JavaScript analyses in `data_processing/characterization/` supply additional source-domain and cookie-category summaries. `decode_consent/` handles consent-string decoding and vendor/purpose statistics; `decode_non-functional/` handles the unnecessary-cookie classification workflow. Their input/output filenames are configured in the respective scripts.
