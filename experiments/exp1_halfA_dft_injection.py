"""
exp1_halfA_dft_injection.py
=============================
Experiment 1, Half-A (positive control) for the 3 DFT-grounded oracles, on
REAL Materials Project reference data (3000 real materials,
experiments/mp_fetch_reference_data.py).

SCOPE NOTE (per CLAUDE.md SS8 rule 1 and the 2026-07-09 decision): this is
Half-A ONLY -- it tests whether stability_claim_consistent /
metallicity_claim_consistent / property_sign_magnitude_consistent correctly
recover a KNOWN planted violation rate against REAL reference values. That is
software correctness, not a DFT-protocol trust decision, so it does not
require Mustafa's sign-off. Half-B (manually judging whether real model
claims against these values are genuinely right/wrong, i.e. treating MP's
computed values as ground truth for a precision number) is explicitly HELD
pending his review of the DFT protocol -- do not run or report Half-B numbers
for these 3 oracles before that review happens.

Method per oracle family, mirroring the XRD/SEM/spectrum harnesses:
  - Stability:    real materials' is_stable (from energy_above_hull) is the
                  clean claim; injected violation = the OPPOSITE claimed_stable
                  boolean.
  - Metallicity:  real materials' is_metal (from band_gap) is the clean claim;
                  injected violation = the opposite claimed_metallic boolean.
  - Sign/magnitude: real materials' total_magnetization is the reference;
                  clean claim = the true value (or a small perturbation within
                  the oracle's own order-of-magnitude tolerance); injected
                  violation = a value with FLIPPED SIGN (for nonzero refs) or
                  a value clearly outside the order-of-magnitude band.

Run: python3 experiments/exp1_halfA_dft_injection.py
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import (  # noqa: E402
    stability_claim_consistent,
    metallicity_claim_consistent,
    property_sign_magnitude_consistent,
    bootstrap_ci,
)

MP_DATA_PATH = "/ephemeral/matpcr/mp_data/mp_reference_batch.jsonl"
PLANTED_RATES = [0.1, 0.3, 0.5]
SEED = 0


def load_materials():
    with open(MP_DATA_PATH) as f:
        return [json.loads(line) for line in f]


def run_stability_positive_control(materials, planted_rate, seed):
    rng = np.random.default_rng(seed)
    truth, flags = [], []
    for m in materials:
        e_hull = m["energy_above_hull"]
        true_stable = e_hull <= 0.05  # matches the oracle's own default tol_eV_atom
        is_violation = rng.random() < planted_rate
        claimed_stable = (not true_stable) if is_violation else true_stable
        consistent = stability_claim_consistent(claimed_stable, e_hull, tol_eV_atom=0.05)
        truth.append(1 if is_violation else 0)
        flags.append(0 if consistent else 1)
    return _summarize(truth, flags, planted_rate, seed)


def run_metallicity_positive_control(materials, planted_rate, seed):
    rng = np.random.default_rng(seed)
    truth, flags = [], []
    for m in materials:
        gap = m["band_gap"]
        true_metallic = gap <= 0.05  # matches the oracle's own default gap_tol_eV
        is_violation = rng.random() < planted_rate
        claimed_metallic = (not true_metallic) if is_violation else true_metallic
        consistent = metallicity_claim_consistent(claimed_metallic, gap, gap_tol_eV=0.05)
        truth.append(1 if is_violation else 0)
        flags.append(0 if consistent else 1)
    return _summarize(truth, flags, planted_rate, seed)


def run_magnetization_positive_control(materials, planted_rate, seed):
    rng = np.random.default_rng(seed)
    truth, flags = [], []
    n_skipped = 0
    for m in materials:
        ref = m["total_magnetization"]
        is_violation = rng.random() < planted_rate
        if is_violation:
            if abs(ref) <= 1e-6:
                # zero reference: any claim with |value| > 10x the oracle's own
                # zero-threshold (10**-1.0 = 0.1) is a guaranteed violation.
                claim = rng.choice([-1, 1]) * rng.uniform(1.0, 5.0)
            else:
                # nonzero reference: flip the sign -- guaranteed violation
                # under property_sign_magnitude_consistent's own sign check,
                # independent of magnitude tolerance.
                claim = -ref * rng.uniform(0.5, 2.0)
        else:
            if abs(ref) <= 1e-6:
                claim = rng.uniform(-0.05, 0.05)  # within the zero-band
            else:
                # same sign, within the oracle's own order-of-magnitude band
                claim = ref * rng.uniform(0.2, 3.0)
        consistent = property_sign_magnitude_consistent(claim, ref, rel_tol=1.0)
        truth.append(1 if is_violation else 0)
        flags.append(0 if consistent else 1)
    return _summarize(truth, flags, planted_rate, seed, n_skipped)


def _summarize(truth, flags, planted_rate, seed, n_skipped=0):
    truth = np.asarray(truth)
    flags = np.asarray(flags)
    n = truth.size
    recovered_rate, ci_lo, ci_hi = bootstrap_ci(flags.astype(float), n_boot=5000, seed=seed)
    planted_idx = truth == 1
    clean_idx = truth == 0
    fn_rate = float(np.mean(flags[planted_idx] == 0)) if planted_idx.any() else float("nan")
    fp_rate = float(np.mean(flags[clean_idx] == 1)) if clean_idx.any() else float("nan")
    return {
        "planted_rate": planted_rate,
        "n_checks": int(n),
        "n_skipped": n_skipped,
        "recovered_rate": recovered_rate,
        "recovered_ci95": (ci_lo, ci_hi),
        "false_negative_rate": fn_rate,
        "false_positive_rate": fp_rate,
    }


def print_family_results(name, materials, run_fn):
    print("\n" + "-" * 78)
    print(f"{name} — n_materials={len(materials)}")
    print("-" * 78)
    print(f"{'planted':>8} | {'n_checks':>8} | {'recovered':>10} | {'95% CI':>18} | {'FN rate':>8} | {'FP rate':>8}")
    for i, p in enumerate(PLANTED_RATES):
        r = run_fn(materials, p, seed=SEED + i)
        ci = r["recovered_ci95"]
        print(
            f"{r['planted_rate']:>8.2f} | {r['n_checks']:>8d} | {r['recovered_rate']:>10.4f} | "
            f"[{ci[0]:.4f}, {ci[1]:.4f}] | {r['false_negative_rate']:>8.4f} | {r['false_positive_rate']:>8.4f}"
        )


def main():
    print("=" * 78)
    print("Experiment 1, Half-A (positive control) — DFT-grounded oracles on REAL Materials Project data")
    print("=" * 78)
    print("\nSCOPE: Half-A only (software correctness against real reference values).")
    print("Half-B (precision audit trusting these values) is HELD pending Mustafa's DFT-protocol")
    print("sign-off per CLAUDE.md SS8 rule 1 -- see module docstring.")

    materials = load_materials()
    print(f"\nTotal real materials loaded: {len(materials)}")

    print_family_results("Stability oracle (energy_above_hull)", materials, run_stability_positive_control)
    print_family_results("Metallicity oracle (band_gap)", materials, run_metallicity_positive_control)
    print_family_results("Sign/magnitude oracle (total_magnetization)", materials, run_magnetization_positive_control)

    print("\n" + "=" * 78)
    print("Interpretation: FN rate = fraction of injected violations missed (should be ~0).")
    print("FP rate = fraction of clean/unperturbed real claims wrongly flagged (should be ~0).")
    print("This validates the 3 oracle functions' comparison logic on real reference values,")
    print("NOT whether those reference values themselves are the right DFT protocol/tolerance")
    print("choice for the paper -- that is Half-B's job and needs Mustafa's review first.")


if __name__ == "__main__":
    main()
