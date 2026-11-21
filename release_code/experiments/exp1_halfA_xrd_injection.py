"""
exp1_halfA_xrd_injection.py
===========================
Experiment 1, Half-A (positive control) for the XRD oracle family, on REAL
opXRD data (not synthetic).

Pipeline per pattern:
  1. Parse a real opXRD pattern_N.json: real measured two_theta_values/intensities
     AND its labeled crystal structure (lattice + basis).
  2. Build a pymatgen Structure from the label; compute reference 2-theta peaks
     via XRDCalculator (Bragg's law from real crystallography, not fabricated).
  3. Extract the pattern's real measured peaks (local maxima in the real signal).
  4. For each measured peak, flip a biased coin at the target planted rate p:
       - unperturbed (clean): claim the true measured 2theta value.
       - perturbed (violation): claim a 2theta shifted by a random offset large
         enough to guarantee it falls outside tolerance of every reference peak
         AND every other real measured peak (so the injected violation is truly
         a violation, not an accidental match).
  5. Run xrd_peak_consistent(claim, reference_two_thetas) from matpcr_metrics.py.
  6. Recovered violation rate = fraction flagged inconsistent by the oracle.
     Compare to the planted rate p. This is the positive-control check: if the
     oracle is correct, recovered ~= planted (catches injected violations = no
     false negatives). It does NOT test precision (Half-B, manual, separate).

Run: python3 experiments/exp1_halfA_xrd_injection.py
"""

from __future__ import annotations

import ast
import glob
import json
import os
import re
import sys

import numpy as np
from pymatgen.analysis.diffraction.xrd import XRDCalculator
from pymatgen.core import Lattice, Structure
from scipy.signal import find_peaks

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import xrd_peak_consistent, bootstrap_ci  # noqa: E402

OPXRD_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "opxrd")
INSTITUTIONS = ["CNRS", "EMPA", "HKUST", "IKFT", "INT", "LBNL", "USC"]
TWO_THETA_WINDOW = (5.0, 90.0)
TOL_DEG = 0.5
PLANTED_RATES = [0.1, 0.3, 0.5]
N_PATTERNS_PER_INSTITUTION = 60  # keep total runtime reasonable; still hundreds overall
MAX_PEAKS_PER_PATTERN = 15
# Real patterns often have only 1-4 GENUINE Bragg reflections; the rest of the
# scan is background/noise that find_peaks still registers as local maxima.
# Confirmed directly (HKUST-A/pattern_16): points at 17-33% of the pattern's
# max intensity, barely above the median background level, are NOT real
# peaks -- testing them as if they were claimed peaks manufactures spurious
# "violations" that reflect nothing about xrd_peak_consistent's correctness.
# Require a peak to be at least this fraction of the pattern's own max
# intensity to be treated as a genuine claim-worthy peak at all.
MIN_RELATIVE_INTENSITY = 0.5
SEED = 0


def parse_structure_and_peaks(path: str):
    """Return (reference_two_thetas: list[float], measured_two_thetas: list[float])
    for one opXRD pattern, or None if the pattern lacks usable structure/peak data.
    """
    with open(path, encoding="utf-8", errors="replace") as f:
        d = json.load(f)

    two_theta = np.asarray(d.get("two_theta_values", []), dtype=float)
    intensities = np.asarray(d.get("intensities", []), dtype=float)
    if two_theta.size < 3 or intensities.size != two_theta.size:
        return None

    try:
        label = json.loads(d["label"])
    except Exception:
        return None

    phases = label.get("phases") or []
    if not phases:
        return None

    wavelength = 1.5406
    xray_info_raw = label.get("xray_info")
    if xray_info_raw:
        try:
            xray_info = json.loads(xray_info_raw)
            if xray_info.get("primary_wavelength"):
                wavelength = float(xray_info["primary_wavelength"])
        except Exception:
            pass
    calc = XRDCalculator(wavelength=wavelength)

    # Real opXRD samples can be MULTI-PHASE (e.g. HKUST-A/pattern_5 has 3, pattern_15
    # has 4) -- a real measured peak can legitimately come from ANY phase present,
    # not just phases[0]. Using only phases[0] as the reference was confirmed
    # directly to cause false positives: 4 of 5 remaining HKUST Half-A false
    # positives (2026-07-06 investigation) were multi-phase samples where the
    # "wrong" peak actually matched phase 2/3/4, just not phase 0. Build the
    # reference from the UNION of every phase with usable lattice+basis --
    # xrd_peak_consistent only needs "does this claim match ANY real reference
    # peak", so no phase_fraction weighting is needed even though the field
    # exists in the schema (and is always None in every sample checked so far).
    reference_two_thetas = []
    n_phases_used = 0
    for phase_raw in phases:
        try:
            phase = json.loads(phase_raw) if isinstance(phase_raw, str) else phase_raw
        except Exception:
            continue

        lattice_raw = phase.get("lattice")
        basis_raw = phase.get("basis")
        if not lattice_raw or not basis_raw:
            continue

        try:
            a, b, c, alpha, beta, gamma = ast.literal_eval(lattice_raw)
            lattice = Lattice.from_parameters(a, b, c, alpha, beta, gamma)

            basis_list = json.loads(basis_raw)
            species, coords = [], []
            for site_raw in basis_list:
                site = json.loads(site_raw) if isinstance(site_raw, str) else site_raw
                m = re.match(r"[A-Za-z]+", site.get("symbol", ""))
                if not m:
                    continue
                species.append(m.group(0))
                coords.append([site["x"], site["y"], site["z"]])
            if len(species) == 0:
                continue

            structure = Structure(lattice, species, coords)
            pattern = calc.get_pattern(structure, two_theta_range=TWO_THETA_WINDOW)
            reference_two_thetas.extend(pattern.x.tolist())
            n_phases_used += 1
        except Exception:
            continue

    if n_phases_used == 0 or len(reference_two_thetas) == 0:
        return None

    rng = intensities.max() - intensities.min()
    if rng <= 0:
        return None
    norm_int = (intensities - intensities.min()) / rng
    peak_idx, _ = find_peaks(norm_int, prominence=0.05, distance=5)
    if peak_idx.size == 0:
        return None

    measured_two_thetas = two_theta[peak_idx]
    measured_intensities = intensities[peak_idx]
    # Real instrument scans can extend outside the oracle's physically-realizable
    # window (e.g. <5deg or >90deg); xrd_peak_consistent correctly rejects claims
    # there, so exclude them here -- otherwise they read as spurious FPs on CLEAN
    # (unperturbed) claims, which is a harness bug, not an oracle bug.
    lo, hi = TWO_THETA_WINDOW
    in_window = (measured_two_thetas >= lo) & (measured_two_thetas <= hi)
    measured_two_thetas = measured_two_thetas[in_window]
    measured_intensities = measured_intensities[in_window]
    if measured_two_thetas.size == 0:
        return None

    resolved = _resolve_peak_envelopes(measured_two_thetas, measured_intensities)
    if len(resolved) == 0:
        return None
    pattern_max_intensity = float(intensities.max())
    resolved = [
        (tt, inten) for tt, inten in resolved
        if inten >= MIN_RELATIVE_INTENSITY * pattern_max_intensity
    ]
    if len(resolved) == 0:
        return None
    resolved = sorted(resolved, key=lambda x: -x[1])[:MAX_PEAKS_PER_PATTERN]
    measured_two_thetas = [tt for tt, _ in resolved]

    return reference_two_thetas, measured_two_thetas


def _resolve_peak_envelopes(two_thetas: np.ndarray, intensities: np.ndarray, cluster_gap_deg: float = 1.0):
    """Real experimental XRD peaks are broadened (crystallite size/strain), so
    scipy.signal.find_peaks with a fixed distance/prominence over-segments ONE
    broadened peak envelope into many spurious local maxima along its tail
    (confirmed directly: HKUST-A/pattern_16 -- one true (110) reflection at
    38.87deg produced 52 "peaks" spanning 30-46deg; only 6/15 top-intensity
    picks were actually near the true apex, the rest were points on the SAME
    peak's decaying tail. Widening find_peaks' `distance` made this WORSE, not
    better, by admitting baseline noise once the tight cluster thinned out.)

    Fix: cluster raw local maxima that are within `cluster_gap_deg` of each
    other (by 2theta proximity, not intensity) into one envelope, and keep
    ONLY the single tallest point per envelope as a genuine peak claim. This
    is a real peak-resolution step, not a tolerance tweak -- it changes how
    many DISTINCT peaks the pattern is judged to have, not how strictly each
    one is checked.

    Returns list of (two_theta, intensity) tuples, one per resolved envelope.
    """
    if two_thetas.size == 0:
        return []
    order = np.argsort(two_thetas)
    sorted_tt = two_thetas[order]
    sorted_int = intensities[order]

    envelopes = []
    current = [0]
    for i in range(1, sorted_tt.size):
        if sorted_tt[i] - sorted_tt[current[-1]] <= cluster_gap_deg:
            current.append(i)
        else:
            envelopes.append(current)
            current = [i]
    envelopes.append(current)

    resolved = []
    for env in envelopes:
        best_i = env[np.argmax(sorted_int[env])]
        resolved.append((float(sorted_tt[best_i]), float(sorted_int[best_i])))
    return resolved


def collect_dataset():
    """Walk all institutions, return list of (reference_two_thetas, measured_two_thetas)
    tuples, one per usable pattern."""
    dataset = []
    per_institution_counts = {}
    for inst in INSTITUTIONS:
        files = sorted(glob.glob(os.path.join(OPXRD_ROOT, inst, "**", "pattern_*.json"), recursive=True))
        n_used = 0
        for fp in files:
            if n_used >= N_PATTERNS_PER_INSTITUTION:
                break
            result = parse_structure_and_peaks(fp)
            if result is None:
                continue
            dataset.append(result)
            n_used += 1
        per_institution_counts[inst] = n_used
    return dataset, per_institution_counts


def make_safe_offset(rng: np.random.Generator, true_2theta: float, reference: list, all_measured: list):
    """Return an offset such that true_2theta + offset lands inside the 2theta
    window but is guaranteed >0.5deg (with margin) from every reference peak AND
    every other real measured peak in this pattern (so the injected violation
    cannot accidentally be "consistent"). Returns None if no such offset exists
    in TOL_DEG*3 attempts across the full search space (dense reference patterns,
    e.g. organic crystals with 100+ peaks, can leave no safe gap) -- callers must
    skip the peak in that case rather than inject an unverified claim.
    """
    lo, hi = TWO_THETA_WINDOW
    margin = TOL_DEG * 1.5  # safety margin beyond the oracle's own tolerance
    others = np.asarray(list(reference) + list(all_measured), dtype=float)
    for offset_mag in np.linspace(1.0, hi - lo, 60):
        for sign in (1.0, -1.0):
            candidate = true_2theta + sign * offset_mag
            if not (lo <= candidate <= hi):
                continue
            if others.size and np.abs(others - candidate).min() <= margin:
                continue
            return candidate
    return None


def run_positive_control(dataset, planted_rate: float, seed: int):
    rng = np.random.default_rng(seed)
    truth_labels = []  # 1 = violation planted, 0 = clean
    oracle_flags = []  # 1 = oracle says inconsistent, 0 = oracle says consistent
    n_skipped_no_safe_offset = 0

    for reference, measured in dataset:
        for true_2theta in measured:
            is_violation = rng.random() < planted_rate
            if is_violation:
                claim = make_safe_offset(rng, true_2theta, reference, measured)
                if claim is None:
                    # No offset in the window is guaranteed >margin from every
                    # reference/measured peak (dense pattern) -- skip rather than
                    # inject an unverified claim that could spuriously "match".
                    n_skipped_no_safe_offset += 1
                    continue
            else:
                claim = true_2theta
            consistent = xrd_peak_consistent(claim, reference, tol_deg=TOL_DEG, two_theta_window=TWO_THETA_WINDOW)
            truth_labels.append(1 if is_violation else 0)
            oracle_flags.append(0 if consistent else 1)

    truth = np.asarray(truth_labels)
    flags = np.asarray(oracle_flags)

    n = truth.size
    recovered_rate, ci_lo, ci_hi = bootstrap_ci(flags.astype(float), n_boot=5000, seed=seed)

    # False negatives: planted violation but oracle said consistent (missed).
    planted_idx = truth == 1
    clean_idx = truth == 0
    false_negative_rate = float(np.mean(flags[planted_idx] == 0)) if planted_idx.any() else float("nan")
    false_positive_rate = float(np.mean(flags[clean_idx] == 1)) if clean_idx.any() else float("nan")

    return {
        "n_skipped_no_safe_offset": n_skipped_no_safe_offset,
        "planted_rate": planted_rate,
        "n_checks": int(n),
        "n_planted_violations": int(planted_idx.sum()),
        "recovered_rate": recovered_rate,
        "recovered_ci95": (ci_lo, ci_hi),
        "false_negative_rate": false_negative_rate,  # missed violations -> should be ~0
        "false_positive_rate": false_positive_rate,  # clean flagged wrong -> should be ~0
    }


def main():
    print("=" * 78)
    print("Experiment 1, Half-A (positive control) — XRD oracle on REAL opXRD data")
    print("=" * 78)

    dataset, per_institution_counts = collect_dataset()
    print("\nPatterns with usable structure+peak data, by institution:")
    for inst, n in per_institution_counts.items():
        print(f"  {inst:6s}: {n}")
    total_patterns = len(dataset)
    total_peaks = sum(len(m) for _, m in dataset)
    print(f"\nTotal usable patterns: {total_patterns}")
    print(f"Total real measured peaks across those patterns: {total_peaks}")

    if total_patterns == 0:
        print("No usable patterns found — aborting.")
        return

    print("\n" + "-" * 78)
    print(f"{'planted':>8} | {'n_checks':>8} | {'skipped':>8} | {'recovered':>10} | {'95% CI':>18} | {'FN rate':>8} | {'FP rate':>8}")
    print("-" * 78)

    results = []
    for i, p in enumerate(PLANTED_RATES):
        r = run_positive_control(dataset, p, seed=SEED + i)
        results.append(r)
        ci = r["recovered_ci95"]
        print(
            f"{r['planted_rate']:>8.2f} | {r['n_checks']:>8d} | {r['n_skipped_no_safe_offset']:>8d} | "
            f"{r['recovered_rate']:>10.4f} | [{ci[0]:.4f}, {ci[1]:.4f}] | "
            f"{r['false_negative_rate']:>8.4f} | {r['false_positive_rate']:>8.4f}"
        )

    print("-" * 78)
    print("\nInterpretation:")
    print("  recovered_rate should track planted_rate closely -> oracle catches injected violations.")
    print("  false_negative_rate is the key Half-A number: fraction of PLANTED violations the")
    print("  oracle MISSED (said consistent). Should be ~0 if tol_deg=0.5 is tight enough relative")
    print("  to the injected offset (1-5 deg, guaranteed >0.5deg from all real peaks).")
    print("  false_positive_rate: fraction of CLEAN (real, unperturbed) claims wrongly flagged.")
    print("  Should be ~0 -- if not, the oracle's tolerance/window is too strict for real data")
    print("  (measurement noise, peak-picking imprecision) and needs recalibration before trusting")
    print("  any PCR number computed from it.")
    print("\nNOTE: this is Half-A only (catches false negatives via injection). Half-B (manual")
    print("precision audit of >=100 oracle-FIRED cases on REAL model outputs, not injected ones)")
    print("is separate, human work, and is NOT satisfied by this script.")


if __name__ == "__main__":
    main()
