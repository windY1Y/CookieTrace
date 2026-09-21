#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read forward-call counts from per-case summaries and plot a smoothed CDF. Select preprocessing with --method and smoothing with --smooth."""
from __future__ import annotations

import argparse
import json
import os
import re
from typing import List, Optional

import numpy as np
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'Times New Roman'

plt.rcParams['font.size'] = 22

FILENAME_RE = re.compile(r'^[A-Za-z0-9\.-]+_\d{4}_summary\.json$')


def read_forward_call_nums(input_dir: str) -> np.ndarray:
    """Read numeric path.forward_call_num values from matching summary files."""
    vals: List[float] = []

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

        pth = data.get('path')
        if pth is None:
            print(f"Warning: file {fname} missing 'path'; skipping")
            continue

        fcn = pth.get('forward_call_num')
        if fcn is None:

            print(f"Warning: file {fname} missing 'path.forward_call_num'; skipping")
            continue
        try:
            vals.append(float(fcn))
        except Exception:
            print(f"Warning: file {fname} forward_call_num not numeric; skipping")
            continue

    return np.array(vals, dtype=float)


def apply_outlier_method(data: np.ndarray, method: str, trim_pct: float = 0.01, mad_mult: float = 5.0, eps: float = 1e-6):
    """Return a transformed copy: none, quantile trimming, winsorization, MAD filtering, or a shifted natural logarithm."""
    if method == 'none' or data.size == 0:
        return data.copy()
    if method == 'trim':
        if not (0.0 <= trim_pct < 0.5):
            raise ValueError("trim_pct must be in [0, 0.5)")
        low_q = np.quantile(data, trim_pct)
        high_q = np.quantile(data, 1.0 - trim_pct)
        return data[(data >= low_q) & (data <= high_q)].copy()
    if method == 'winsorize':
        if not (0.0 <= trim_pct < 0.5):
            raise ValueError("trim_pct must be in [0, 0.5)")
        low_q = np.quantile(data, trim_pct)
        high_q = np.quantile(data, 1.0 - trim_pct)
        return np.clip(data, low_q, high_q)
    if method == 'mad':
        med = np.median(data)
        mad = np.median(np.abs(data - med))
        if mad == 0:
            return data.copy()
        sigma = 1.4826 * mad
        return data[np.abs((data - med) / sigma) <= mad_mult].copy()
    if method == 'log':
        minv = np.min(data)
        return np.log(data - minv + eps)
    raise ValueError("unknown method")


def smooth_cdf_kde(data: np.ndarray, x_grid: np.ndarray, bw: Optional[float] = None) -> np.ndarray:
    """Estimate a PDF with Gaussian KDE and integrate it over the grid to obtain a CDF."""
    from scipy.stats import gaussian_kde  # may raise ImportError
    kde = gaussian_kde(data)
    if bw is not None:
        if isinstance(bw, str):
            pass
        else:
            try:
                bwf = float(bw)
                kde.set_bandwidth(bw_method=bwf)
            except Exception:
                pass
    pdf_vals = kde.evaluate(x_grid)
    dx = np.diff(x_grid)
    if np.allclose(dx, dx[0]):
        cdf_vals = np.cumsum(pdf_vals) * dx[0]
        if cdf_vals[-1] == 0:
            return np.clip(cdf_vals, 0.0, 1.0)
        cdf_vals = cdf_vals / cdf_vals[-1]
    else:
        cdf_vals = np.zeros_like(pdf_vals)
        cdf_vals[1:] = np.cumsum((pdf_vals[:-1] + pdf_vals[1:]) / 2.0 * np.diff(x_grid))
        if cdf_vals[-1] != 0:
            cdf_vals = cdf_vals / cdf_vals[-1]
    return cdf_vals


def smooth_cdf_hist(data: np.ndarray, x_grid: np.ndarray, bins: int = 200) -> np.ndarray:
    """Estimate a CDF by cumulatively summing a fine-grained histogram."""
    counts, edges = np.histogram(data, bins=bins, density=True)
    bin_widths = np.diff(edges)
    pdf_by_bin = counts
    cdf_at_edges = np.concatenate(([0.0], np.cumsum(pdf_by_bin * bin_widths)))
    cdf_vals = np.interp(x_grid, edges, cdf_at_edges, left=0.0, right=1.0)
    return cdf_vals


def plot_single_cdf(data: np.ndarray, smooth: str = 'kde', bw: Optional[str] = None, bins: int = 200,
                    out_png: str = 'cdf_forward_call_num.png', xlabel: str = '#Forward Calls',
                    tight_mode: str = 'safe'):
    """Plot the input distribution with labeled axes, summary statistics, and configurable layout margins."""
    if data.size == 0:
        raise RuntimeError("Dataset empty; nothing to plot.")

    data_min = np.nanmin(data)
    data_max = np.nanmax(data)
    if data_min == data_max:
        pad = max(1.0, abs(data_min) * 0.05)
        xmin = data_min - pad
        xmax = data_max + pad
    else:
        rng = data_max - data_min
        xmin = data_min - 0.02 * rng
        xmax = data_max + 0.02 * rng

    x_grid = np.linspace(xmin, xmax, 1000)

    if smooth == 'kde':
        try:
            cdf_vals = smooth_cdf_kde(data, x_grid, bw=bw)
        except Exception as e:
            print(f"Warning: KDE smoothing failed or scipy not available ({e}), falling back to hist method.")
            cdf_vals = smooth_cdf_hist(data, x_grid, bins=bins)
    else:
        cdf_vals = smooth_cdf_hist(data, x_grid, bins=bins)


    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x_grid, cdf_vals, linewidth=2.5, label="forward_call_num")
    ax.set_xlabel(xlabel)
    ax.set_ylabel('Cumulative Probability')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0.0, 1.02)
    ax.set_xlim(xmin, xmax)
    ax.legend(loc='lower right')


    if tight_mode == 'max':

        fig.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)
        bbox_inches = 'tight'
        pad_inches = 0.0
    else:


        fig.subplots_adjust(left=0.06, right=0.99, bottom=0.07, top=0.97)
        bbox_inches = 'tight'
        pad_inches = 0.01


    fig.savefig(out_png, dpi=300, bbox_inches=bbox_inches, pad_inches=pad_inches)
    plt.close(fig)
    print(f"Saved smoothed CDF to: {out_png} (mode={tight_mode})")


def main():
    p = argparse.ArgumentParser(description="Smoothed CDF for path.forward_call_num from summary JSONs")
    p.add_argument('--input', '-i', required=True, help="Directory with *_summary.json files")
    p.add_argument('--out', '-o', default='cdf_forward_call_num.png')
    p.add_argument('--method', choices=['none', 'trim', 'winsorize', 'mad', 'log'], default='none',
                   help="Outlier handling method")
    p.add_argument('--trim-pct', type=float, default=0.01)
    p.add_argument('--mad-mult', type=float, default=5.0)
    p.add_argument('--smooth', choices=['kde', 'hist'], default='hist',
                   help="Smoothing method: 'kde' uses scipy gaussian_kde; 'hist' uses dense histogram")
    p.add_argument('--bins', type=int, default=200, help="Bins for hist smoothing (when --smooth hist)")
    p.add_argument('--bw', type=str, default=None,
                   help="Bandwidth for KDE: float or 'scott'/'silverman' or None (use scipy default)")
    args = p.parse_args()

    vals = read_forward_call_nums(args.input)
    print(f"Read: forward_call_num count = {vals.size}")

    vals_proc = apply_outlier_method(vals, args.method, trim_pct=args.trim_pct, mad_mult=args.mad_mult)
    print(f"After outlier method '{args.method}': count = {vals_proc.size}")

    plot_single_cdf(vals_proc, smooth=args.smooth, bw=args.bw, bins=args.bins, out_png=args.out)


if __name__ == '__main__':
    main()
