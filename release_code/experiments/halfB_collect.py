"""
halfB_collect.py
=================
Experiment 1, Half-B data collection: gather >=100 REAL oracle-FIRED cases
per modality (XRD, SEM, spectrum) for MANUAL precision review. This script
does NOT do the manual review -- it generates real model claims (same
prompts/models as pilot.py), runs them through the actual oracle
(xrd_peak_consistent / sem_feature_size_consistent / spectrum_peak_exists),
and keeps requesting more items until each modality has >=TARGET_FIRED fired
cases (oracle said "inconsistent"). The human reviews the output afterward
(see experiments/halfB_review_<modality>.html, built by halfB_report.py) and
records precision = (real violations) / (fired cases reviewed).

Reuses pilot.py's item builders and model runners directly -- same real
data (opXRD/NFFA-EUROPE/RRUFF), same prompts, same parser.

Known landmine (found this session): opXRD contains at least one pattern
(CNRS/pattern_678) with a 13,488-atom basis that makes pymatgen's XRD
symmetry analysis hang effectively indefinitely (observed: >3 hours CPU
time, killed). MAX_BASIS_ATOMS below skips any phase over that size --
this is a real, permanent guard, not a temporary workaround.

Run: python3 experiments/halfB_collect.py --target 100 --modalities xrd sem spectrum --models local api
"""

from __future__ import annotations

import os

# MATPCR_DATA_ROOT is host-specific -- set it in the environment before
# running on a new host; see experiments/slurm/README.md.
MATPCR_DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", "/ephemeral/matpcr")
os.environ["HF_HOME"] = os.path.join(MATPCR_DATA_ROOT, "hf_cache")

import argparse
import ast
import json
import re
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import xrd_peak_consistent, sem_feature_size_consistent, spectrum_peak_exists  # noqa: E402

import pilot  # noqa: E402  (reuse build_*_items, run_local_qwen, run_api_openrouter, parse_chain)

MAX_BASIS_ATOMS = 500  # see module docstring: pattern_678 (13,488 atoms) hung pymatgen indefinitely

# SECOND landmine found later (2026-07-11, during Experiment 3 development):
# atom count alone does NOT predict a hang. CNRS/pattern_62.json (276 atoms,
# under the MAX_BASIS_ATOMS cap) hung pymatgen's XRDCalculator.get_pattern()
# indefinitely -- confirmed directly, a separate 20-atom pattern
# (CNRS/pattern_735.json) also took 15s and produced a suspiciously large
# 9,742-peak reference pattern, meaning pymatgen's symmetry analysis time
# depends on the structure's actual (low/no) symmetry, not just its size.
# MAX_BASIS_ATOMS is necessary but not sufficient. Fixed with a real
# wall-clock timeout via signal.alarm (Linux/Unix only, fine for this
# deployment) around the specific call that hangs -- a thread-based timeout
# would NOT work here for the same reason it failed for the network hang
# (see exp2_pcr_sweep.py's incident note): pymatgen's C-extension-backed
# symmetry code does not yield to a thread join, only a genuine signal/
# process-level interrupt can stop it.
XRD_CALC_TIMEOUT_S = 20


class _XrdCalcTimeout(Exception):
    pass


def _get_pattern_with_timeout(calc, structure, two_theta_range, timeout_s=XRD_CALC_TIMEOUT_S):
    import signal

    def _handler(signum, frame):
        raise _XrdCalcTimeout()

    old_handler = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(timeout_s)
    try:
        return calc.get_pattern(structure, two_theta_range=two_theta_range)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

UNIT_TO_NM = {"nm": 1.0, "um": 1000.0, "µm": 1000.0, "μm": 1000.0, "mm": 1_000_000.0}


# ----------------------------------------------------------------------------
# Oracle-checking per modality (mirrors pilot.py's data sources exactly)
# ----------------------------------------------------------------------------
def xrd_reference_peaks(source_file: str):
    """Build the reference 2theta list from ALL usable phases (same fix as
    exp1_halfA_xrd_injection.py), skipping any phase whose basis exceeds
    MAX_BASIS_ATOMS."""
    from pymatgen.core import Structure, Lattice
    from pymatgen.analysis.diffraction.xrd import XRDCalculator

    with open(source_file, encoding="utf-8", errors="replace") as f:
        d = json.load(f)
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
            xi = json.loads(xray_info_raw)
            if xi.get("primary_wavelength"):
                wavelength = float(xi["primary_wavelength"])
        except Exception:
            pass
    calc = XRDCalculator(wavelength=wavelength)

    refs = []
    for phase_raw in phases:
        try:
            phase = json.loads(phase_raw) if isinstance(phase_raw, str) else phase_raw
            lattice_raw = phase.get("lattice")
            basis_raw = phase.get("basis")
            if not lattice_raw or not basis_raw:
                continue
            basis_list = json.loads(basis_raw)
            if len(basis_list) > MAX_BASIS_ATOMS:
                continue
            a, b, c, al, be, ga = ast.literal_eval(lattice_raw)
            lattice = Lattice.from_parameters(a, b, c, al, be, ga)
            species, coords = [], []
            for site_raw in basis_list:
                site = json.loads(site_raw) if isinstance(site_raw, str) else site_raw
                m = re.match(r"[A-Za-z]+", site.get("symbol", ""))
                if not m:
                    continue
                species.append(m.group(0))
                coords.append([site["x"], site["y"], site["z"]])
            if not species:
                continue
            structure = Structure(lattice, species, coords)
            pattern = _get_pattern_with_timeout(calc, structure, (5, 90))
            refs.extend(pattern.x.tolist())
        except _XrdCalcTimeout:
            # A real, reproducible hang (confirmed on CNRS/pattern_62.json,
            # 276 atoms) -- skip this phase rather than block the whole
            # pipeline. Not silently swallowed: this is a known, documented
            # landmine, not an unexpected error.
            continue
        except Exception:
            continue
    return refs if refs else None


_SEM_BAR_CACHE = {}


def sem_scale_bar(source_file: str):
    """Run the same extractor as sem_scalebar_extractor.py on this specific
    image (on demand, not from the pre-existing 300-image sample file --
    the pilot's images are a different random draw)."""
    if source_file in _SEM_BAR_CACHE:
        return _SEM_BAR_CACHE[source_file]
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import sem_scalebar_extractor as ext

    result = ext.process_image(source_file)
    _SEM_BAR_CACHE[source_file] = result
    return result


def spectrum_signal(source_file: str):
    xs, ys = [], []
    with open(source_file, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("##"):
                continue
            parts = line.split(",")
            if len(parts) != 2:
                continue
            try:
                x, y = float(parts[0]), float(parts[1])
            except ValueError:
                continue
            xs.append(x)
            ys.append(y)
    if len(xs) < 10:
        return None
    return np.asarray(xs), np.asarray(ys)


def check_oracle(item, parsed):
    """Return True (consistent) / False (fired/inconsistent) / None (could
    not evaluate -- skip, don't count either way)."""
    modality = item["modality"]
    if modality == "xrd":
        ref = xrd_reference_peaks(item["source_file"])
        if ref is None:
            return None
        return xrd_peak_consistent(parsed["value"], ref, tol_deg=0.5)

    if modality == "sem":
        bar = sem_scale_bar(item["source_file"])
        if bar is None or bar.get("status") != "ok":
            return None
        unit = parsed["unit"]
        mult = UNIT_TO_NM.get(unit)
        if mult is None:
            return None
        claimed_nm = parsed["value"] * mult
        long_edge = max(bar["image_w"], bar["image_h"])
        return sem_feature_size_consistent(claimed_nm, bar["scale_nm"], bar["marker_px"], long_edge)

    if modality == "spectrum":
        sig = spectrum_signal(item["source_file"])
        if sig is None:
            return None
        xs, ys = sig
        return spectrum_peak_exists(parsed["value"], xs, ys, x_tol=5.0)

    return None


# ----------------------------------------------------------------------------
# Main collection loop
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=100, help="fired cases needed per modality")
    ap.add_argument("--modalities", nargs="*", default=["xrd", "sem", "spectrum"])
    ap.add_argument("--models", nargs="*", default=["local", "api"])
    ap.add_argument("--batch_size", type=int, default=20, help="items pulled per round")
    ap.add_argument("--max_rounds", type=int, default=30, help="safety cap on rounds per modality")
    ap.add_argument("--out", default="experiments/halfB_fired_cases.jsonl")
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if "api" in args.models and not api_key:
        print("WARNING: OPENROUTER_API_KEY not set; skipping API model.")
        args.models = [m for m in args.models if m != "api"]

    total_cost = 0.0
    seed_counter = 1000  # offset from pilot.py's own seeds to avoid resampling identical items

    with open(args.out, "w") as out_f:
        for modality in args.modalities:
            fired_count = 0
            round_i = 0
            print(f"\n=== {modality}: collecting until {args.target} fired cases ===")
            while fired_count < args.target and round_i < args.max_rounds:
                round_i += 1
                seed_counter += 1
                items = pilot.MODALITY_BUILDERS[modality](args.batch_size, seed=seed_counter)

                for item in items:
                    for model_key in args.models:
                        t0 = time.time()
                        try:
                            if model_key == "local":
                                chain_text = pilot.run_local_qwen(item["image_path"], item["prompt"])
                                cost = 0.0
                            else:
                                chain_text, cost = pilot.run_api_openrouter(item["image_path"], item["prompt"], api_key)
                                cost = cost or 0.0
                                total_cost += cost
                        except Exception as e:
                            chain_text = f"__ERROR__: {e}"
                            cost = 0.0
                        elapsed = time.time() - t0

                        parsed = pilot.parse_chain(chain_text)
                        if parsed is None:
                            continue

                        try:
                            oracle_result = check_oracle(item, parsed)
                        except Exception as e:
                            oracle_result = None
                            print(f"  [{modality}/{model_key}] oracle check error: {e}")
                        if oracle_result is None:
                            continue

                        fired = not oracle_result
                        record = {
                            "modality": modality,
                            "model": model_key,
                            "source_file": item["source_file"],
                            "image_path": item["image_path"],
                            "prompt": item["prompt"],
                            "chain_text": chain_text,
                            "parsed": parsed,
                            "oracle_consistent": oracle_result,
                            "fired": fired,
                            "cost_usd": cost,
                            "elapsed_s": elapsed,
                        }
                        out_f.write(json.dumps(record) + "\n")
                        out_f.flush()

                        if fired:
                            fired_count += 1

                print(f"  round {round_i}: fired_count={fired_count}/{args.target} (cost so far: ${total_cost:.4f})")

            if fired_count < args.target:
                print(f"  WARNING: {modality} only reached {fired_count}/{args.target} fired cases after {round_i} rounds (max_rounds hit).")

    print(f"\nTotal API cost: ${total_cost:.4f}")
    print(f"Fired cases written to: {args.out}")


if __name__ == "__main__":
    main()
