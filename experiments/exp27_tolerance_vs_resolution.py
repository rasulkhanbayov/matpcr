"""
exp27_tolerance_vs_resolution.py
================================
KBS revision R1 (Reviewer 1 M2): ground the oracle tolerances in the measurement properties of
the data they are applied to. For every diffraction pattern and Raman spectrum used in the main
evaluation (exp2) or the precision audit (Half-B), report:
  * sampling step: median spacing of the abscissa (2-theta in degrees; Raman shift in cm^-1)
  * width of the strongest resolved peak: full width at half maximum (scipy.signal.peak_widths
    at rel_height=0.5 on the min-max normalized signal), in abscissa units
and compare them with the oracle tolerance (0.5 deg; 5 cm^-1) and the accuracy criterion of the
accuracy-versus-consistency analysis (0.1 deg; 2 cm^-1).

Run: MATPCR_DATA_ROOT=... python experiments/exp27_tolerance_vs_resolution.py [--families xrd spectrum]
Writes: experiments/exp27_results.json (merged per family)
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
from scipy.signal import find_peaks, peak_widths

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", os.path.join(os.path.dirname(HERE), "data"))
OUT = os.path.join(HERE, "exp27_results.json")
TOL = {"xrd": (0.5, 0.1), "spectrum": (5.0, 2.0)}


def resolve(p):
    if "/opxrd/" in p:
        return os.path.join(DATA_ROOT, "opxrd", p.split("/opxrd/")[-1])
    if "/rruff/" in p:
        return os.path.join(DATA_ROOT, "rruff", p.split("/rruff/")[-1])
    return p


def sources(fam):
    s = set()
    for f in ["exp2_results_panther.jsonl", "exp2_gpt56sol_geometric.jsonl"]:
        for l in open(os.path.join(HERE, f)):
            r = json.loads(l)
            if r["modality"] == fam:
                s.add(r["source_id"])
    for l in open(os.path.join(HERE, "halfB_fired_cases.jsonl")):
        r = json.loads(l)
        if r["modality"] == fam:
            s.add(r["source_file"])
    return sorted(s)


def load_xy(fam, path):
    if fam == "xrd":
        d = json.load(open(path, encoding="utf-8", errors="replace"))
        return np.asarray(d["two_theta_values"], float), np.asarray(d["intensities"], float)
    from halfB_collect import spectrum_signal
    sig = spectrum_signal(path)
    return (None, None) if sig is None else (np.asarray(sig[0], float), np.asarray(sig[1], float))


def rendered_resolution(n=40):
    """x-axis degrees per pixel of the diffractogram plots shown to the models (pilot.build_xrd_items:
    figsize (8, 5) at 120 dpi, ticks every 10 deg), on 40 random CNRS patterns."""
    import glob
    import random
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    files = sorted(glob.glob(os.path.join(DATA_ROOT, "opxrd", "CNRS", "pattern_*.json")))
    random.Random(0).shuffle(files)
    res = []
    for fp in files[:n]:
        x, y = load_xy("xrd", fp)
        fig, ax = plt.subplots(figsize=(8, 5), dpi=120)
        ax.plot(x, y, linewidth=0.8)
        ax.set_xticks(np.arange(0, x.max() + 10, 10))
        fig.canvas.draw()
        lo, hi = ax.get_xlim()
        res.append((hi - lo) / ax.get_window_extent().width)
        plt.close(fig)
    return [float(np.median(res)), float(min(res)), float(max(res))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--families", nargs="+", default=["xrd", "spectrum"])
    args = ap.parse_args()
    out = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for fam in args.families:
        steps, fwhm, skipped = [], [], 0
        for sp in sources(fam):
            p = resolve(sp)
            if not os.path.exists(p):
                skipped += 1
                continue
            x, y = load_xy(fam, p)
            if x is None or len(x) < 10:
                skipped += 1
                continue
            order = np.argsort(x)
            x, y = x[order], y[order]
            steps.append(float(np.median(np.diff(x))))
            yn = (y - y.min()) / (y.max() - y.min() + 1e-12)
            pk, prop = find_peaks(yn, prominence=0.05)
            if len(pk) == 0:
                continue
            top = pk[np.argmax(yn[pk])]
            w = peak_widths(yn, [top], rel_height=0.5)[0][0]
            fwhm.append(float(w * np.median(np.diff(x))))
        tol, acc = TOL[fam]
        q = lambda a: [float(np.percentile(a, v)) for v in (10, 25, 50, 75, 90)]
        res = {"n_files": len(steps), "skipped": skipped,
               "step_percentiles_10_25_50_75_90": q(steps), "fwhm_percentiles_10_25_50_75_90": q(fwhm),
               "oracle_tolerance": tol, "accuracy_tolerance": acc,
               "share_fwhm_below_2x_tol": float(np.mean(np.asarray(fwhm) < 2 * tol)),
               "share_fwhm_below_2x_acc": float(np.mean(np.asarray(fwhm) < 2 * acc)),
               "median_tol_in_steps": float(tol / np.median(steps)), "median_acc_in_steps": float(acc / np.median(steps))}
        if fam == "xrd":
            res["rendered_deg_per_pixel_median_min_max"] = rendered_resolution()
        out[fam] = res
        print(fam, json.dumps(res, indent=1))
    json.dump(out, open(OUT, "w"), indent=1)


if __name__ == "__main__":
    main()
