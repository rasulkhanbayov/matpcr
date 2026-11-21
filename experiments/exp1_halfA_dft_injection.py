"""
exp1_halfA_dft_injection.py
=============================
Experiment 1, Half-A (positive control) for the 3 DFT-grounded oracles, on
REAL Materials Project reference data (3000 real materials,
experiments/mp_fetch_reference_data.py).

SCOPE NOTE: per the domain co-author's review (M.K., 2026-07, see
VERSION2/Dr_mustafas_comments), Materials Project is now an APPROVED reference
source for completing Half-B for all 3 DFT-grounded oracles, conditional on
the oracle corrections implemented in matpcr_metrics.py (metallicity
abstention band, magnetism classify-then-magnitude redesign, stability
sensitivity reporting) -- all now in place. This script remains Half-A ONLY:
it tests whether stability_claim_consistent / metallicity_claim_consistent /
magnetism_magnitude_consistent correctly recover a KNOWN planted violation
rate against REAL reference values -- software correctness, re-run here
because the oracle functions themselves changed, not because the sign-off
status changed.

Method per oracle family, mirroring the XRD/SEM/spectrum harnesses:
  - Stability:    real materials' is_stable (from energy_above_hull) is the
                  clean claim; injected violation = the OPPOSITE claimed_stable
                  boolean. Re-run at all 4 sensitivity tolerances
                  (matpcr_metrics.STABILITY_SENSITIVITY_TOLERANCES_EV_ATOM).
  - Metallicity:  real materials' band_gap decides a ternary true state
                  (metallic / non-metallic / ambiguous-excluded) under the new
                  abstention band; materials whose true state is ambiguous are
                  skipped (n_skipped), matching how the oracle itself excludes
                  them from PCR. Injected violation = the opposite
                  claimed_metallic boolean, only for non-ambiguous materials.
  - Magnetism:    real materials' total_magnetization/nsites decides
                  magnetic-vs-not against the new preregistered threshold;
                  clean claim = the true classification (+ magnitude within
                  tolerance, for magnetic materials); injected violation =
                  the OPPOSITE classification, or (for magnetic materials) a
                  magnitude clearly outside the order-of-magnitude band. Sign
                  is never part of the claim or the check, per the redesign.

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
    magnetism_magnitude_consistent,
    STABILITY_SENSITIVITY_TOLERANCES_EV_ATOM,
    bootstrap_ci,
)

# MATPCR_DATA_ROOT is host-specific -- set it in the environment before
# running on a new host; see experiments/slurm/README.md.
MATPCR_DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", "/ephemeral/matpcr")
MP_DATA_PATH = os.path.join(MATPCR_DATA_ROOT, "mp_data", "mp_reference_batch.jsonl")
PLANTED_RATES = [0.1, 0.3, 0.5]
SEED = 0


def load_materials():
    with open(MP_DATA_PATH) as f:
        return [json.loads(line) for line in f]


def run_stability_positive_control(materials, planted_rate, seed, tol_eV_atom=0.05):
    rng = np.random.default_rng(seed)
    truth, flags, skipped = [], [], 0
    for m in materials:
        e_hull = m["energy_above_hull"]
        true_stable = e_hull <= tol_eV_atom  # matches the oracle's own tol_eV_atom
        is_violation = rng.random() < planted_rate
        claimed_stable = (not true_stable) if is_violation else true_stable
        consistent = stability_claim_consistent(claimed_stable, e_hull, tol_eV_atom=tol_eV_atom)
        if consistent is None:  # near-hull abstention band: not scored
            skipped += 1
            continue
        truth.append(1 if is_violation else 0)
        flags.append(0 if consistent else 1)
    return _summarize(truth, flags, planted_rate, seed, n_skipped=skipped)


def run_metallicity_positive_control(materials, planted_rate, seed, metal_max_eV=0.05, gap_min_eV=0.20):
    rng = np.random.default_rng(seed)
    truth, flags = [], []
    n_skipped = 0
    for m in materials:
        gap = m["band_gap"]
        if metal_max_eV < gap < gap_min_eV:
            n_skipped += 1  # ambiguous dead zone: the oracle itself excludes this material
            continue
        true_metallic = gap <= metal_max_eV
        is_violation = rng.random() < planted_rate
        claimed_metallic = (not true_metallic) if is_violation else true_metallic
        consistent = metallicity_claim_consistent(
            claimed_metallic, gap, metal_max_eV=metal_max_eV, gap_min_eV=gap_min_eV
        )
        truth.append(1 if is_violation else 0)
        flags.append(0 if consistent else 1)
    return _summarize(truth, flags, planted_rate, seed, n_skipped)


def run_magnetism_positive_control(materials, planted_rate, seed, magnetic_threshold=0.05):
    rng = np.random.default_rng(seed)
    truth, flags = [], []
    n_skipped = 0
    for m in materials:
        n_atoms = m.get("nsites")
        if not n_atoms or n_atoms <= 0:
            n_skipped += 1
            continue
        ref_magnitude = abs(m["total_magnetization"]) / n_atoms
        true_magnetic = ref_magnitude >= magnetic_threshold
        is_violation = rng.random() < planted_rate

        if is_violation:
            if rng.random() < 0.5 or not true_magnetic:
                # flip the binary classification -- guaranteed violation
                claimed_magnetic = not true_magnetic
                claimed_magnitude = None
            else:
                # keep the (correct) classification, but give a magnitude
                # clearly outside the order-of-magnitude band -- guaranteed
                # violation only checkable for genuinely magnetic materials.
                claimed_magnetic = True
                claimed_magnitude = ref_magnitude * rng.uniform(15.0, 50.0)
        else:
            claimed_magnetic = true_magnetic
            claimed_magnitude = (
                ref_magnitude * rng.uniform(0.2, 3.0) if true_magnetic else None
            )
            # sign is never part of the claim under the corrected oracle -- confirm
            # a randomly-signed clean claim is still accepted, exercising that path.
            if claimed_magnitude is not None and rng.random() < 0.5:
                claimed_magnitude = -claimed_magnitude

        consistent = magnetism_magnitude_consistent(
            claimed_magnetic, claimed_magnitude, m["total_magnetization"], n_atoms,
            magnetic_threshold_muB_per_atom=magnetic_threshold,
        )
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


def print_family_results(name, materials, run_fn, **kwargs):
    print("\n" + "-" * 78)
    print(f"{name} — n_materials={len(materials)}")
    print("-" * 78)
    print(f"{'planted':>8} | {'n_checks':>8} | {'n_skip':>7} | {'recovered':>10} | {'95% CI':>18} | {'FN rate':>8} | {'FP rate':>8}")
    for i, p in enumerate(PLANTED_RATES):
        r = run_fn(materials, p, seed=SEED + i, **kwargs)
        ci = r["recovered_ci95"]
        print(
            f"{r['planted_rate']:>8.2f} | {r['n_checks']:>8d} | {r['n_skipped']:>7d} | {r['recovered_rate']:>10.4f} | "
            f"[{ci[0]:.4f}, {ci[1]:.4f}] | {r['false_negative_rate']:>8.4f} | {r['false_positive_rate']:>8.4f}"
        )


def main():
    print("=" * 78)
    print("Experiment 1, Half-A (positive control) — DFT-grounded oracles on REAL Materials Project data")
    print("=" * 78)
    print("\nSCOPE: Half-A (software correctness), re-run because the oracle functions changed")
    print("per the domain co-author's review (metallicity abstention band, magnetism")
    print("classify-then-magnitude redesign, stability sensitivity). See module docstring.")

    materials = load_materials()
    print(f"\nTotal real materials loaded: {len(materials)}")

    print("\n" + "=" * 78)
    print("STABILITY: sensitivity sweep over tol_eV_atom in "
          f"{STABILITY_SENSITIVITY_TOLERANCES_EV_ATOM} (per M.K.'s review)")
    print("=" * 78)
    for tol in STABILITY_SENSITIVITY_TOLERANCES_EV_ATOM:
        print_family_results(
            f"Stability oracle (energy_above_hull, tol_eV_atom={tol})",
            materials, run_stability_positive_control, tol_eV_atom=tol,
        )

    print_family_results(
        "Metallicity oracle (band_gap, metal_max_eV=0.05, gap_min_eV=0.20)",
        materials, run_metallicity_positive_control,
    )
    print_family_results(
        "Magnetism-magnitude oracle (total_magnetization/nsites, threshold=0.05 muB/atom)",
        materials, run_magnetism_positive_control,
    )

    print("\n" + "=" * 78)
    print("Interpretation: FN rate = fraction of injected violations missed (should be ~0).")
    print("FP rate = fraction of clean/unperturbed real claims wrongly flagged (should be ~0).")
    print("n_skip = materials excluded from this oracle (metallicity's ambiguous dead zone,")
    print("or magnetism's missing-nsites cases -- 0 expected for magnetism after the")
    print("mp_fetch_reference_data.py update that requires nsites).")
    print("This validates the 3 oracle functions' comparison logic on real reference values,")
    print("now approved by the domain co-author as standardized computational references")
    print("(not experimental ground truth) -- see VERSION2/Dr_mustafas_comments.")


if __name__ == "__main__":
    main()
