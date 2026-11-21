"""
exp1_halfA_sem_injection.py
============================
Experiment 1, Half-A (positive control) for the SEM scale-bar oracle
(sem_feature_size_consistent), on REAL NFFA-EUROPE data.

sem_feature_size_consistent(claimed_feature_nm, scale_bar_nm, scale_bar_px,
image_px_long_edge) is a simple physical bound: a claimed feature size is
INCONSISTENT iff it exceeds the field of view (FOV) implied by the scale bar
(FOV = (scale_bar_nm / scale_bar_px) * image_px_long_edge). Half-A here means:
for each real extracted scale bar (from experiments/sem_scalebar_results.jsonl,
already built and verified at 97.7% success on a 300-image sample), generate
either a CLEAN claim (some plausible fraction of the FOV) or an INJECTED
VIOLATION claim (a size that exceeds the FOV by a known margin), then check
whether the oracle correctly flags each.

This uses the extractor's OWN measured scale_nm/marker_px as ground truth for
the FOV -- it is NOT re-validating the extractor itself (that's the 97.7%
number, already reported), it is validating that xrd_peak_consistent's sibling
oracle, sem_feature_size_consistent, correctly distinguishes physically
possible from impossible claims given a correct scale bar reading.

Run: python3 experiments/exp1_halfA_sem_injection.py
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import sem_feature_size_consistent, bootstrap_ci  # noqa: E402

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sem_scalebar_results.jsonl")
PLANTED_RATES = [0.1, 0.3, 0.5]
SEED = 0


def load_usable_bars():
    """Load (scale_bar_nm, scale_bar_px, image_px_long_edge) tuples from the
    already-verified extractor output -- only rows with status == 'ok'."""
    bars = []
    with open(RESULTS_PATH) as f:
        for line in f:
            r = json.loads(line)
            if r["status"] != "ok":
                continue
            long_edge = max(r["image_w"], r["image_h"])
            bars.append(
                {
                    "scale_bar_nm": r["scale_nm"],
                    "scale_bar_px": r["marker_px"],
                    "image_px_long_edge": long_edge,
                    "path": r["path"],
                }
            )
    return bars


def run_positive_control(bars, planted_rate: float, seed: int):
    rng = np.random.default_rng(seed)
    truth_labels = []  # 1 = violation planted, 0 = clean
    oracle_flags = []  # 1 = oracle says inconsistent, 0 = oracle says consistent

    for bar in bars:
        nm_per_px = bar["scale_bar_nm"] / bar["scale_bar_px"]
        fov_nm = nm_per_px * bar["image_px_long_edge"]

        is_violation = rng.random() < planted_rate
        if is_violation:
            # A claim safely, unambiguously OUTSIDE the FOV: 1.2x-3x over.
            claim_nm = fov_nm * rng.uniform(1.2, 3.0)
        else:
            # A claim safely, unambiguously WITHIN the FOV: 1%-90% of it.
            claim_nm = fov_nm * rng.uniform(0.01, 0.90)

        consistent = sem_feature_size_consistent(
            claim_nm, bar["scale_bar_nm"], bar["scale_bar_px"], bar["image_px_long_edge"]
        )
        truth_labels.append(1 if is_violation else 0)
        oracle_flags.append(0 if consistent else 1)

    truth = np.asarray(truth_labels)
    flags = np.asarray(oracle_flags)
    n = truth.size
    recovered_rate, ci_lo, ci_hi = bootstrap_ci(flags.astype(float), n_boot=5000, seed=seed)

    planted_idx = truth == 1
    clean_idx = truth == 0
    false_negative_rate = float(np.mean(flags[planted_idx] == 0)) if planted_idx.any() else float("nan")
    false_positive_rate = float(np.mean(flags[clean_idx] == 1)) if clean_idx.any() else float("nan")

    return {
        "planted_rate": planted_rate,
        "n_checks": int(n),
        "recovered_rate": recovered_rate,
        "recovered_ci95": (ci_lo, ci_hi),
        "false_negative_rate": false_negative_rate,
        "false_positive_rate": false_positive_rate,
    }


def main():
    print("=" * 78)
    print("Experiment 1, Half-A (positive control) — SEM oracle on REAL NFFA-EUROPE data")
    print("=" * 78)

    bars = load_usable_bars()
    print(f"\nUsable extracted scale bars (status=='ok'): {len(bars)}")
    if not bars:
        print("No usable bars found — aborting.")
        return

    print("\n" + "-" * 78)
    print(f"{'planted':>8} | {'n_checks':>8} | {'recovered':>10} | {'95% CI':>18} | {'FN rate':>8} | {'FP rate':>8}")
    print("-" * 78)

    for i, p in enumerate(PLANTED_RATES):
        r = run_positive_control(bars, p, seed=SEED + i)
        ci = r["recovered_ci95"]
        print(
            f"{r['planted_rate']:>8.2f} | {r['n_checks']:>8d} | {r['recovered_rate']:>10.4f} | "
            f"[{ci[0]:.4f}, {ci[1]:.4f}] | {r['false_negative_rate']:>8.4f} | {r['false_positive_rate']:>8.4f}"
        )

    print("-" * 78)
    print("\nInterpretation:")
    print("  Claims injected at 1.2x-3x the FOV should ALWAYS be flagged inconsistent (FN~0).")
    print("  Claims at 1%-90% of the FOV should ALWAYS be flagged consistent (FP~0).")
    print("  This is a wide safety margin (not testing near the 1.0x boundary) -- it validates")
    print("  the oracle's core logic, not edge-case tolerance. NOTE: this is Half-A only; Half-B")
    print("  (manual precision audit of real model claims) is separate, human work.")


if __name__ == "__main__":
    main()
