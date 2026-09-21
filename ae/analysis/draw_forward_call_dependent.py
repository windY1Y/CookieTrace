#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plot the fraction of sources that depend on forward tracking. Histogram frequencies use observation counts by default; optional preprocessing is controlled by --method."""
from __future__ import annotations

import argparse
import json
import os
import re
from typing import List, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt

FILENAME_RE = re.compile(r'^[A-Za-z0-9\.-]+_\d{4}_summary\.json$')
FIRST_DIGIT_RE = re.compile(r"\d")

plt.rcParams['font.family'] = 'Times New Roman'

plt.rcParams['font.size'] = 22


def read_forward_counts(input_dir: str) -> np.ndarray:
    """Read numeric source statistics from matching per-case JSON summaries."""
    vals: List[float] = []

    if not os.path.isdir(input_dir):
        raise RuntimeError(f"Input path is not a directory: {input_dir}")

    for fname in sorted(os.listdir(input_dir)):
        if not FILENAME_RE.match(fname):
            continue
        full = os.path.join(input_dir, fname)
        try:
            with open(full, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"[WARN] failed to read/parse JSON {full}: {e}")
            continue

        src = data.get('source')
        if src is None:
            print(f"[WARN] file {fname} missing top-level 'source'; skipping.")
            continue

        val_forward = src.get('forward_dependent_var_count')
        val_sum = src.get('total')
        if val_sum==0:
            continue
        val = val_forward / val_sum
        if val is None:
            print(f"[WARN] file {fname} missing source.forward_dependent_var_count; skipping.")
            continue

        try:
            fval = float(val)
            vals.append(fval)
        except Exception:
            print(f"[WARN] file {fname} source.forward_dependent_var_count not numeric ({val}); skipping.")

    return np.array(vals, dtype=float)


def apply_outlier_method(data: np.ndarray,
                         method: str = 'none',
                         trim_pct: float = 0.01,
                         mad_mult: float = 5.0,
                         eps: float = 1e-6) -> np.ndarray:
    """Return a transformed copy: none, quantile trimming, winsorization, MAD filtering, or a shifted natural logarithm."""
    if method == 'none':
        return data.copy()

    if data.size == 0:
        return data.copy()

    if method == 'trim':
        if not (0.0 <= trim_pct < 0.5):
            raise ValueError("trim_pct must be in [0, 0.5)")
        low_q = np.quantile(data, trim_pct)
        high_q = np.quantile(data, 1.0 - trim_pct)
        mask = (data >= low_q) & (data <= high_q)
        return data[mask].copy()

    if method == 'winsorize':
        if not (0.0 <= trim_pct < 0.5):
            raise ValueError("trim_pct must be in [0, 0.5)")
        low_q = np.quantile(data, trim_pct)
        high_q = np.quantile(data, 1.0 - trim_pct)
        clipped = np.clip(data, low_q, high_q)
        return clipped

    if method == 'mad':
        med = np.median(data)
        mad = np.median(np.abs(data - med))
        if mad == 0:

            return data.copy()
        sigma_est = 1.4826 * mad
        z = (data - med) / sigma_est
        mask = np.abs(z) <= mad_mult
        return data[mask].copy()

    if method == 'log':
        min_val = np.min(data)
        shifted = data - min_val + eps

        return np.log(shifted)

    raise ValueError(f"Unknown outlier method: {method}")


def plot_hist_forward(values: np.ndarray,
                      out_png: str = 'hist_forward_dependent.png',
                      threshold: Optional[float] = None,
                      threshold_color: str = 'tab:orange',
                      threshold_linestyle: str = '--',
                      mean_color: str = 'tab:blue',
                      bins: int = 30,
                      figsize: Tuple[int, int] = (10, 6),
                      alpha: float = 0.8,
                      scale_factor: float = 1.0,
                      tight_mode: str = 'safe') -> dict:
    """Plot the input distribution with labeled axes, summary statistics, and configurable layout margins."""
    if values.size == 0:
        raise RuntimeError("No data to plot (no valid forward_dependent_var_count values found).")

    arr = values.astype(float)
    mean_val = float(np.mean(arr))
    med_val = float(np.median(arr))
    n = arr.size


    fig, ax = plt.subplots(figsize=figsize)


    weights = np.ones_like(arr) * float(scale_factor)
    counts, bins_out, patches = ax.hist(
        arr,
        bins=bins,
        edgecolor='black',
        alpha=alpha,
        weights=weights
    )

    ax.set_xlabel('Forward Call Dependent Sources (%)')
    ax.set_ylabel('#Websites')
    # ax.set_title(
    #     'Distribution of Forward Call Dependent\nCookie Sources Across Websites',
    #     fontweight='bold',
    #     fontsize=22,
    #     pad=12
    # )


    ax.axvline(
        x=mean_val,
        color=mean_color,
        linestyle='-',
        linewidth=2,
        label=f'Mean = {mean_val:.2f}'
    )


    above_cnt = None
    above_pct = None
    if threshold is not None:
        ax.axvline(
            x=threshold,
            color=threshold_color,
            linestyle=threshold_linestyle,
            linewidth=2,
            label=f'Threshold = {threshold:g}'
        )
        above_cnt = round(int(np.sum(arr > threshold)) * scale_factor)
        sum_n = round(n * scale_factor)
        above_pct = (above_cnt / sum_n) * 100.0

        txt = f'>{threshold:g}: {above_cnt}/{sum_n} ({above_pct:.2f}%)'
        ax.text(
            0.99, 0.88, txt,
            transform=ax.transAxes,
            ha='right', va='top',
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.8),
            fontsize=9
        )

    ax.legend(loc='upper right')
    ax.grid(axis='y', alpha=0.25)


    if tight_mode == 'max':

        fig.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)
        bbox_inches = 'tight'
        pad_inches = 0.0
    else:

        fig.subplots_adjust(left=0.07, right=0.99, bottom=0.10, top=0.92)
        bbox_inches = 'tight'
        pad_inches = 0.01

    fig.savefig(out_png, dpi=300, bbox_inches=bbox_inches, pad_inches=pad_inches)
    plt.close(fig)
    print(f"Saved histogram to {out_png} (mode={tight_mode})")

    return {
        'n': n,
        'mean': mean_val,
        'median': med_val,
        'threshold': threshold,
        'above_count': above_cnt,
        'above_pct': above_pct,
        'scale_factor': scale_factor
    }



def main():
    p = argparse.ArgumentParser(description="Histogram of source.forward_dependent_var_count with outlier handling")
    p.add_argument('--input', '-i', required=True, help='Directory containing *_summary.json files')
    p.add_argument('--out', '-o', default='hist_forward_dependent.png', help='Output PNG path')
    p.add_argument('--threshold', '-t', type=float, default=None, help='Threshold to mark with a dashed line')
    p.add_argument('--threshold-color', type=str, default='tab:orange', help='Color for threshold dashed line')
    p.add_argument('--threshold-linestyle', type=str, default='--', help='Linestyle for threshold (default: --)')
    p.add_argument('--bins', type=int, default=30, help='Number of histogram bins (default 30)')
    p.add_argument('--mean-color', type=str, default='tab:blue', help='Color for mean solid line')

    p.add_argument('--method', choices=['none', 'trim', 'winsorize', 'mad', 'log'],
                   default='none', help="Outlier handling method (default none)")
    p.add_argument('--trim-pct', type=float, default=0.01,
                   help="Trim/winsorize percentage at each tail (default 0.01)")
    p.add_argument('--mad-mult', type=float, default=5.0,
                   help="MAD multiplier for 'mad' method (default 5)")
    p.add_argument('--eps', type=float, default=1e-6,
                   help="EPS for log transform (default 1e-6)")

    p.add_argument('--scale-factor', type=float, default=1.0,
                   help='Vertical scale factor for histogram counts (default 1.0)')

    args = p.parse_args()


    arr_raw = read_forward_counts(args.input)
    print(f"Original sample size: {arr_raw.size}")


    arr_proc = apply_outlier_method(arr_raw, method=args.method, trim_pct=args.trim_pct, mad_mult=args.mad_mult, eps=args.eps)
    print(f"After method='{args.method}': sample size = {arr_proc.size}")


    if args.method == 'log':
        print("Note: method='log' transforms data by log(x - min + eps); x-axis units are on log scale.")


    stats = plot_hist_forward(arr_proc,
                              out_png=args.out,
                              threshold=args.threshold,
                              threshold_color=args.threshold_color,
                              threshold_linestyle=args.threshold_linestyle,
                              mean_color=args.mean_color,
                              bins=args.bins,
                              scale_factor=args.scale_factor)


    print("Summary statistics (after processing):")
    print(f"  N = {stats['n']}")
    print(f"  Mean = {stats['mean']:.4f}")
    print(f"  Median = {stats['median']:.4f}")
    if stats['threshold'] is not None:
        print(f"  Threshold = {stats['threshold']}")
        print(f"  Above threshold: {stats['above_count']} ({stats['above_pct']:.2f}%)")
    print(f"  Histogram vertical scale factor = {stats.get('scale_factor', 1.0):g}")


if __name__ == '__main__':
    main()
