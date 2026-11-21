"""
exp9_tolerance_sensitivity.py
================================
REVISION_PLAN.md Phase 2, item 19 (audit EX7): does the model ranking (which
model has the highest PCR) survive reasonable changes to each oracle's
tolerance, or is the ranking an artifact of one specific threshold choice?

Reuses the EXISTING Half-B fired-cases files (halfB_fired_cases.jsonl,
halfB_dft_fired_cases.jsonl) directly -- these already contain the full
population (fired AND non-fired records, despite the filename; confirmed
2026-07-19: xrd n=205, sem n=481, spectrum n=575, stability n=395,
metallicity n=255, magnetism n=241) with each record's real parsed claim and
enough provenance (source_file / reference dict) to re-derive ground truth
and re-check consistency at DIFFERENT tolerances. NO new model calls --
this is a pure re-analysis of already-collected claims, which is why it can
run immediately without touching the API budget the other Phase 2 items are
spending.

Three modalities, three different tolerance axes:
  - XRD: tol_deg in {0.25, 0.5 (current), 0.75, 1.0} -- re-derive each
    source_file's reference peak list once (xrd_reference_peaks, cached) and
    re-check the record's parsed 2theta claim at each tolerance.
  - Spectrum: x_tol in {10, 20 (current), 30} cm^-1 CROSSED with
    prominence_frac in {0.03, 0.05 (current), 0.08} -- re-derive each
    source_file's signal once (spectrum_signal, cached) and re-check.
  - Stability: tol_eV_atom in STABILITY_SENSITIVITY_TOLERANCES_EV_ATOM
    (0, 0.025, 0.05, 0.10), reusing matpcr_metrics's own preregistered grid
    -- no new grid invented here, just applied at the per-record level
    instead of only being documented as a range.

SEM and metallicity/magnetism are NOT included: SEM's tolerance is an exact
FOV threshold with no ambiguity window (per CLAUDE.md's Half-A note, this
oracle is a simple deterministic comparison, nothing to sweep); metallicity
already HAS a preregistered dead-zone (not a continuous tolerance to sweep);
magnetism's threshold sensitivity is a separate, not-yet-scoped question.

Reports, per modality: the per-model consistency rate at each tolerance
value/combination, and whether the model RANKING (argsort of rates) is
stable across the tolerance grid (Kendall-tau-like simple rank agreement
count vs. the current/default tolerance's ranking).

Run: python3 experiments/exp9_tolerance_sensitivity.py
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matpcr_metrics import (  # noqa: E402
    xrd_peak_consistent,
    spectrum_peak_exists,
    stability_claim_consistent,
    STABILITY_SENSITIVITY_TOLERANCES_EV_ATOM,
)
from halfB_collect import xrd_reference_peaks, spectrum_signal  # noqa: E402

FIRED_CASES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "halfB_fired_cases.jsonl")
DFT_FIRED_CASES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "halfB_dft_fired_cases.jsonl")

XRD_TOLS_DEG = (0.25, 0.5, 0.75, 1.0)
SPECTRUM_X_TOLS = (10.0, 20.0, 30.0)
SPECTRUM_PROMINENCE_FRACS = (0.03, 0.05, 0.08)

_xrd_ref_cache = {}
_spectrum_signal_cache = {}


def _get_xrd_refs(source_file):
    if source_file not in _xrd_ref_cache:
        try:
            _xrd_ref_cache[source_file] = xrd_reference_peaks(source_file)
        except Exception:
            _xrd_ref_cache[source_file] = None
    return _xrd_ref_cache[source_file]


def _get_spectrum_signal(source_file):
    if source_file not in _spectrum_signal_cache:
        try:
            _spectrum_signal_cache[source_file] = spectrum_signal(source_file)
        except Exception:
            _spectrum_signal_cache[source_file] = None
    return _spectrum_signal_cache[source_file]


def rank_agreement(rates_by_tol):
    """rates_by_tol: list of {model: rate} dicts, one per tolerance setting.
    Returns the fraction of all model PAIRS whose relative order (which of
    the two has the higher rate) agrees between the FIRST setting (treated
    as the reference/current default) and every other setting, averaged."""
    settings = list(rates_by_tol)
    if len(settings) < 2:
        return None
    models = sorted(settings[0].keys())
    pairs = [(a, b) for i, a in enumerate(models) for b in models[i + 1 :]]
    if not pairs:
        return None
    ref = settings[0]
    agreements = []
    for other in settings[1:]:
        n_agree = 0
        for a, b in pairs:
            if a not in other or b not in other:
                continue
            ref_sign = np.sign(ref[a] - ref[b])
            other_sign = np.sign(other[a] - other[b])
            if ref_sign == other_sign:
                n_agree += 1
        agreements.append(n_agree / len(pairs))
    return float(np.mean(agreements))


def run_xrd_sweep():
    with open(FIRED_CASES_PATH) as f:
        records = [json.loads(line) for line in f if json.loads(line).get("modality") == "xrd"]

    per_tol_model_results = []
    for tol in XRD_TOLS_DEG:
        model_hits = {}
        for r in records:
            claim = r.get("parsed", {}).get("value") if isinstance(r.get("parsed"), dict) else None
            if claim is None:
                continue
            refs = _get_xrd_refs(r["source_file"])
            if not refs:
                continue
            consistent = xrd_peak_consistent(claim, refs, tol_deg=tol)
            model = r["model"]
            model_hits.setdefault(model, []).append(consistent)
        rates = {m: float(np.mean(v)) for m, v in model_hits.items() if v}
        per_tol_model_results.append(rates)
        print(f"[xrd] tol_deg={tol}: " + ", ".join(f"{m}={r:.3f}(n={len(model_hits[m])})" for m, r in sorted(rates.items())))

    agreement = rank_agreement(per_tol_model_results)
    print(f"[xrd] rank agreement vs default (tol=0.5): {agreement}")
    return {"modality": "xrd", "tolerances": XRD_TOLS_DEG, "rates_by_tol": per_tol_model_results, "rank_agreement": agreement}


def run_spectrum_sweep():
    with open(FIRED_CASES_PATH) as f:
        records = [json.loads(line) for line in f if json.loads(line).get("modality") == "spectrum"]

    grid = [(xt, pf) for xt in SPECTRUM_X_TOLS for pf in SPECTRUM_PROMINENCE_FRACS]
    # Put the current default (20.0, 0.05) first so rank_agreement treats it as the reference.
    grid.sort(key=lambda t: (t != (20.0, 0.05), t))

    per_setting_model_results = []
    for x_tol, prom in grid:
        model_hits = {}
        for r in records:
            claim = r.get("parsed", {}).get("value") if isinstance(r.get("parsed"), dict) else None
            if claim is None:
                continue
            sig = _get_spectrum_signal(r["source_file"])
            if sig is None:
                continue
            xs, ys = sig
            consistent = spectrum_peak_exists(claim, xs, ys, x_tol=x_tol, prominence_frac=prom)
            model = r["model"]
            model_hits.setdefault(model, []).append(consistent)
        rates = {m: float(np.mean(v)) for m, v in model_hits.items() if v}
        per_setting_model_results.append(rates)
        print(f"[spectrum] x_tol={x_tol} prom={prom}: " + ", ".join(f"{m}={r:.3f}(n={len(model_hits[m])})" for m, r in sorted(rates.items())))

    agreement = rank_agreement(per_setting_model_results)
    print(f"[spectrum] rank agreement vs default (x_tol=20, prom=0.05): {agreement}")
    return {"modality": "spectrum", "grid": grid, "rates_by_setting": per_setting_model_results, "rank_agreement": agreement}


def run_stability_sweep():
    with open(DFT_FIRED_CASES_PATH) as f:
        records = [json.loads(line) for line in f if json.loads(line).get("claim_type") == "stability"]

    tols = list(STABILITY_SENSITIVITY_TOLERANCES_EV_ATOM)
    tols.sort(key=lambda t: (t != 0.05, t))  # default (0.05) first

    per_tol_model_results = []
    for tol in tols:
        model_hits = {}
        for r in records:
            claimed = r.get("parsed")
            if claimed not in ("STABLE", "UNSTABLE"):
                continue
            hull = r.get("reference", {}).get("energy_above_hull")
            if hull is None:
                continue
            consistent = stability_claim_consistent(claimed == "STABLE", hull, tol_eV_atom=tol)
            model = r["model"]
            model_hits.setdefault(model, []).append(consistent)
        rates = {m: float(np.mean(v)) for m, v in model_hits.items() if v}
        per_tol_model_results.append(rates)
        print(f"[stability] tol_eV_atom={tol}: " + ", ".join(f"{m}={r:.3f}(n={len(model_hits[m])})" for m, r in sorted(rates.items())))

    agreement = rank_agreement(per_tol_model_results)
    print(f"[stability] rank agreement vs default (tol=0.05): {agreement}")
    return {"modality": "stability", "tolerances": tols, "rates_by_tol": per_tol_model_results, "rank_agreement": agreement}


def main():
    results = {
        "xrd": run_xrd_sweep(),
        "spectrum": run_spectrum_sweep(),
        "stability": run_stability_sweep(),
    }
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp9_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWritten to: {out_path}")
    print("\nSEM excluded (exact-threshold oracle, no ambiguity window to sweep).")
    print("Metallicity/magnetism excluded (metallicity already has a preregistered")
    print("dead-zone rather than a single continuous tolerance; magnetism's threshold")
    print("sensitivity is a separate, not-yet-scoped question).")


if __name__ == "__main__":
    main()
