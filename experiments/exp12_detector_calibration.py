"""
exp12_detector_calibration.py
================================
REVISION_PLAN.md Phase 2, item 22 (audit EX11): reliability diagrams (binned
calibration curves) for the released verifier, plus a recommended operating
point (probability threshold) per split -- goes beyond Experiment 5/6's
single-number ECE/AUC to show WHERE the verifier's probability estimates are
over- or under-confident, and gives a concrete threshold recommendation
instead of leaving "how would someone actually use this score" unanswered.

Reuses Experiment 5's real per-item verifier probs/labels directly from
exp5_results.jsonl (same source Experiment 6 used) -- no new training, no
new model calls. Per CLAUDE.md SS16, "modality" and "constraint" held-out
splits are confirmed to be the SAME 6-way partition in this benchmark (each
oracle family is its own constraint type), so only the "modality" variant is
reported here, matching Experiment 6's own reporting choice -- not
duplicated.

For each split (in-distribution random + 6 held-out-modality):
  - RELIABILITY DIAGRAM: bin predicted P(violation) into 10 equal-width bins,
    report (n, mean predicted prob, empirical violation rate) per bin -- the
    same binning ECE (matpcr_metrics.expected_calibration_error) already
    uses internally, just exposed per-bin instead of collapsed to one
    number, so a reader can see WHERE calibration breaks down (e.g. is the
    verifier overconfident only in the high-probability bins?).
  - RECOMMENDED OPERATING POINT: the probability threshold in [0.05, 0.95]
    (0.05 step) that maximizes F1 on this split's own data. Reported
    alongside the DEFAULT 0.5 threshold's F1 for comparison -- if the
    optimal threshold is far from 0.5, that itself is a finding (the
    verifier's probabilities are systematically shifted, not just noisy).
    NOTE: this is an in-sample-optimal threshold (chosen and evaluated on
    the same held-out set), so it should be read as "here is where this
    split's own precision/recall tradeoff curve peaks," not as a threshold
    validated to generalize to a THIRD, unseen sample.

Run: python3 experiments/exp12_detector_calibration.py
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import precision_recall_f1  # noqa: E402

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp5_results.jsonl")

MODALITY_ORDER = ["xrd", "sem", "spectrum", "stability", "metallicity", "magnetism"]


def reliability_diagram(probs, labels, n_bins=10):
    probs = np.asarray(probs, float)
    labels = np.asarray(labels, int)
    edges = np.linspace(0, 1, n_bins + 1)
    bins = []
    for i in range(n_bins):
        m = (probs > edges[i]) & (probs <= edges[i + 1]) if i > 0 else (probs >= edges[i]) & (probs <= edges[i + 1])
        n = int(m.sum())
        if n == 0:
            bins.append({"bin_lo": float(edges[i]), "bin_hi": float(edges[i + 1]), "n": 0,
                         "mean_pred": None, "empirical_rate": None})
            continue
        bins.append({
            "bin_lo": float(edges[i]), "bin_hi": float(edges[i + 1]), "n": n,
            "mean_pred": float(probs[m].mean()), "empirical_rate": float(labels[m].mean()),
        })
    return bins


def best_operating_point(probs, labels):
    probs = np.asarray(probs, float)
    labels = np.asarray(labels, int)
    thresholds = np.arange(0.05, 1.0, 0.05)
    best = {"threshold": None, "f1": -1.0, "precision": None, "recall": None}
    for t in thresholds:
        pred = (probs >= t).astype(int)
        prf = precision_recall_f1(pred, labels)
        f1 = prf["f1"]
        if isinstance(f1, float) and not np.isnan(f1) and f1 > best["f1"]:
            best = {"threshold": float(t), "f1": float(f1), "precision": prf["precision"], "recall": prf["recall"]}
    pred_default = (probs >= 0.5).astype(int)
    prf_default = precision_recall_f1(pred_default, labels)
    return best, prf_default


def main():
    with open(RESULTS_PATH) as f:
        runs = {r["run_name"]: r for r in (json.loads(line) for line in f)}

    splits = [("random", "In-distribution (random split)")]
    for m in MODALITY_ORDER:
        splits.append((f"modality_heldout_{m}", f"Held-out {m}"))

    results = {}
    for run_name, label in splits:
        if run_name not in runs:
            print(f"WARNING: {run_name} not found in {RESULTS_PATH}, skipping.")
            continue
        r = runs[run_name]
        probs, labels = r["probs"], r["labels"]
        bins = reliability_diagram(probs, labels)
        best, default = best_operating_point(probs, labels)
        results[run_name] = {
            "label": label, "n": len(probs), "reliability_bins": bins,
            "best_operating_point": best, "default_threshold_0.5": default,
        }
        print(f"\n[{label}] n={len(probs)}")
        print("  Reliability diagram (bin: n, mean_pred, empirical_rate):")
        for b in bins:
            if b["n"] == 0:
                continue
            gap = abs(b["mean_pred"] - b["empirical_rate"])
            flag = "  <-- gap>0.2" if gap > 0.2 else ""
            print(f"    [{b['bin_lo']:.1f},{b['bin_hi']:.1f}]: n={b['n']:4d} "
                  f"pred={b['mean_pred']:.3f} actual={b['empirical_rate']:.3f}{flag}")
        print(f"  Best operating point: threshold={best['threshold']:.2f} F1={best['f1']:.3f} "
              f"(P={best['precision']:.3f} R={best['recall']:.3f})")
        print(f"  Default threshold=0.50: F1={default['f1']:.3f} "
              f"(P={default['precision']:.3f} R={default['recall']:.3f})")

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp12_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWritten to: {out_path}")
    print("\nNOTE: recommended operating points are chosen AND evaluated on the same held-out")
    print("set per split (in-sample-optimal) -- read as where this split's own precision/recall")
    print("tradeoff peaks, not as a threshold independently validated on a third unseen sample.")
    print("modality/constraint splits are the same 6-way partition in this benchmark (CLAUDE.md")
    print("SS16) -- only 'modality' is reported here, matching Experiment 6's own choice.")


if __name__ == "__main__":
    main()
