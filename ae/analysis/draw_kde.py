#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare source propagation depth and call-stack depth from per-case JSON summaries."""
from __future__ import annotations

import argparse
import json
import os
import re
from typing import List, Tuple, Callable, Optional


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# --- Minimal global font setting: use Times New Roman for all plot text ---
plt.rcParams['font.family'] = 'Times New Roman'

plt.rcParams['font.size'] = 26
# ------------------------------------------------------------------------

FILENAME_RE = re.compile(r'^[A-Za-z0-9\.-]+_\d{4}_summary\.json$')


def read_summary_files(input_dir: str) -> Tuple[np.ndarray, np.ndarray, List[Tuple[float, float]]]:
    """Return propagation depths, stack depths, and raw paired values for per-case comparison."""
    track_depths: List[float] = []
    call_depths: List[float] = []
    paired_vals: List[Tuple[float, float]] = []

    if not os.path.isdir(input_dir):
        raise RuntimeError(f"Input path is not a directory: {input_dir}")

    for fname in sorted(os.listdir(input_dir)):
        if not FILENAME_RE.match(fname):
            continue
        fullpath = os.path.join(input_dir, fname)
        try:
            with open(fullpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Warning: failed to read/parse JSON file {fullpath}: {e}")
            continue

        src = data.get('source')
        pth = data.get('path')
        if src is None or pth is None:

            if src is None:
                print(f"Warning: file {fname} missing top-level 'source' key; skipping.")
            if pth is None:
                print(f"Warning: file {fname} missing top-level 'path' key; skipping.")
            continue

        avg_track_depth = src.get('avg_track_depth')
        stack_total = pth.get('stack_total')


        if avg_track_depth is not None:
            try:
                avg_val = float(avg_track_depth)
                track_depths.append(avg_val)
            except Exception as e:
                print(f"Warning: file {fname} source.avg_track_depth not numeric ({avg_track_depth}): {e}")
        else:
            print(f"Warning: file {fname} missing source.avg_track_depth; skipping that value.")

        if stack_total is not None:
            try:
                stack_val = float(stack_total)
                call_depths.append(stack_val)
            except Exception as e:
                print(f"Warning: file {fname} path.stack_total not numeric ({stack_total}): {e}")
        else:
            print(f"Warning: file {fname} missing path.stack_total; skipping that value.")


        if (avg_track_depth is not None) and (stack_total is not None):
            try:
                paired_vals.append((float(avg_track_depth), float(stack_total)))
            except Exception:
                pass

    if len(track_depths) == 0 and len(call_depths) == 0:
        raise RuntimeError(f"No valid track or call depth values found in directory: {input_dir}")

    return np.array(track_depths, dtype=float), np.array(call_depths, dtype=float), paired_vals


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


def plot_kde_depth(track_depth_data: np.ndarray,
                   call_depth_data: np.ndarray,
                   threshold: float = 30.0,
                   out_png: str = 'kde_comparison_depth.png',
                   bw_method: Optional[str] = None,
                   tight_mode: str = 'safe'):
    """Plot propagation and stack depth densities. Safe layout retains margins for labels; max layout minimizes margins."""
    if track_depth_data.size == 0 and call_depth_data.size == 0:
        raise RuntimeError("Both input datasets are empty; cannot plot KDE.")

    rows = []
    if track_depth_data.size > 0:
        rows.append(pd.DataFrame({'depth': track_depth_data, 'Group': 'Variable Flow Depth'}))
    if call_depth_data.size > 0:
        rows.append(pd.DataFrame({'depth': call_depth_data, 'Group': 'Call Stack Depth'}))
    df = pd.concat(rows, ignore_index=True)


    fig, ax = plt.subplots(figsize=(12, 7))

    sns.kdeplot(
        data=df,
        x='depth',
        hue='Group',
        fill=True,
        alpha=0.3,
        linewidth=2,
        common_norm=False,
        bw_method=bw_method,
        ax=ax
    )


    for data, color, group in [
        (track_depth_data, 'blue', 'Variable Flow Depth'),
        (call_depth_data, 'red',  'Call Stack Depth')
    ]:
        if data.size == 0:
            continue
        mean_val = np.mean(data)
        ax.axvline(
            x=mean_val,
            color=color,
            linestyle='-',
            linewidth=2,
            alpha=0.8,
            label=f'{group}: Mean={mean_val:.2f}'
        )


    try:
        min_val = float(df['depth'].min())
        max_val = float(df['depth'].max())
        if np.isfinite(min_val) and np.isfinite(max_val):
            if max_val == min_val:
                pad = max(1.0, abs(min_val) * 0.05)
            else:
                pad = (max_val - min_val) * 0.05
            ax.set_xlim(min_val - pad, max_val + pad)
    except Exception:
        pass


    ax.set_xlabel('Depth/Length')
    ax.set_ylabel('Density')
    ax.set_title('Density Comparison', fontweight='bold', fontsize=26, pad=12)

    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)


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
    print(f"\nKDE density plot saved to: {out_png} (mode={tight_mode})")



def main():
    p = argparse.ArgumentParser(description="KDE with optional outlier handling")
    p.add_argument('--input', '-i', required=True, help="Directory with *_summary.json files")
    p.add_argument('--out', '-o', default='kde_comparison_depth.png', help="Output PNG")
    p.add_argument('--method', choices=['none', 'trim', 'winsorize', 'mad', 'log'],
                   default='none', help="Outlier handling method (default none)")
    p.add_argument('--trim-pct', type=float, default=0.01,
                   help="Trim/winsorize percentage at each tail (default 0.01)")
    p.add_argument('--mad-mult', type=float, default=5.0,
                   help="MAD multiplier for 'mad' method (default 5)")
    p.add_argument('--bw', type=str, default=None,
                   help="bw_method for seaborn.kdeplot (None uses default; can be 'scott','silverman' or a float)")
    args = p.parse_args()

    track_arr, call_arr, paired_vals = read_summary_files(args.input)
    print(f"Original sample sizes: track={track_arr.size}, call={call_arr.size}, pairs={len(paired_vals)}")


    track_proc = apply_outlier_method(track_arr, method=args.method, trim_pct=args.trim_pct, mad_mult=args.mad_mult)
    call_proc = apply_outlier_method(call_arr, method=args.method, trim_pct=args.trim_pct, mad_mult=args.mad_mult)

    print(f"After '{args.method}' processing: track={track_proc.size}, call={call_proc.size}")


    num_pairs = len(paired_vals)
    num_call_gt_track = 0
    if num_pairs > 0:
        paired_arr = np.array(paired_vals, dtype=float)
        num_call_gt_track = int(np.sum(paired_arr[:, 0] > paired_arr[:, 1]))
        print(f"Pairs where variable flow depth > call stack depth: {num_call_gt_track} / {num_pairs} ({num_call_gt_track/num_pairs:.2%})")
    else:
        print("No paired values to compare (no files that contain both fields).")


    plot_kde_depth(track_proc, call_proc, out_png=args.out, bw_method=args.bw)


if __name__ == '__main__':
    main()
