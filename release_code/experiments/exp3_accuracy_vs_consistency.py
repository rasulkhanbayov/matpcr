"""
exp3_accuracy_vs_consistency.py
=================================
Experiment 3 (matpcr_runbook.txt): on a labeled subset, measure ANSWER
ACCURACY and PCR (physical consistency) on the SAME items, and report the
divergence -- the four-cell breakdown (correct+consistent, correct+
inconsistent, wrong+consistent, wrong+inconsistent) -- to show PCR carries
information beyond accuracy.

SCOPE (decided 2026-07-10, see conversation): only 3 of the 6 oracle families
have a genuine, non-circular ground-truth "accuracy" criterion distinct from
the oracle's own consistency check:
  - XRD:       accuracy = claim within a TIGHT window (0.1deg) of the single
               NEAREST true reference peak (closest-match accuracy).
               consistency = the oracle's existing LOOSE 0.5deg tolerance.
  - Spectrum:  accuracy = claim within a TIGHT window (2 cm^-1) of the single
               nearest REAL measured peak's position (closest-match accuracy).
               consistency = the oracle's prominence-based check
               (spectrum_peak_exists) -- a genuinely different axis: a claim
               can be positionally close but fail prominence, or prominence-
               satisfying but positionally off from the nearest real peak if
               a different peak nearby also satisfies prominence.
  - Stability: accuracy = claim matches Materials Project's OWN strict
               is_stable label (essentially exact-zero hull threshold).
               consistency = the oracle's LOOSER 0.05 eV/atom tolerance.
               This directly reuses the real 19% definition-mismatch already
               found during Half-B (see CLAUDE.md) -- turns a previously
               "flagged as unresolved" finding into a quantified Exp 3 result.

SEM is EXCLUDED: the current prompt only elicits a structured FEATURE-SIZE
claim, not a structured SCALE-BAR-VALUE claim, so there is no non-circular
accuracy ground truth available without changing the prompt and re-collecting
data (out of scope for this pass). Metallicity/magnetism are excluded because,
unlike stability, they don't have an equivalent looser-vs-stricter-threshold
split already characterized.

Run: python3 experiments/exp3_accuracy_vs_consistency.py --n 30 --seeds 3
"""

from __future__ import annotations

import os

# MATPCR_DATA_ROOT is host-specific -- set it in the environment before
# running on a new host; see experiments/slurm/README.md.
MATPCR_DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", "/ephemeral/matpcr")
os.environ["HF_HOME"] = os.path.join(MATPCR_DATA_ROOT, "hf_cache")

import argparse
import json
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import xrd_peak_consistent, spectrum_peak_exists, stability_claim_consistent  # noqa: E402

import pilot  # noqa: E402
import pilot_dft  # noqa: E402
from halfB_collect import xrd_reference_peaks, spectrum_signal  # noqa: E402
from exp2_pcr_sweep import MODELS, run_one_image_item, run_one_dft_item  # noqa: E402

MP_DATA_PATH = os.path.join(MATPCR_DATA_ROOT, "mp_data", "mp_reference_batch.jsonl")

XRD_ACCURACY_TOL_DEG = 0.1
SPECTRUM_ACCURACY_TOL = 2.0


def check_xrd_both(item: dict, parsed: dict):
    ref = xrd_reference_peaks(item["source_file"])
    if ref is None or not ref:
        return None, None
    claim = parsed["value"]
    consistent = xrd_peak_consistent(claim, ref, tol_deg=0.5)
    nearest_dist = min(abs(r - claim) for r in ref)
    accurate = nearest_dist <= XRD_ACCURACY_TOL_DEG
    return accurate, consistent


def check_spectrum_both(item: dict, parsed: dict):
    sig = spectrum_signal(item["source_file"])
    if sig is None:
        return None, None
    xs, ys = sig
    claim = parsed["value"]
    consistent = spectrum_peak_exists(claim, xs, ys, x_tol=5.0)
    # nearest REAL measured peak position (local maxima), not just nearest raw sample
    from scipy.signal import find_peaks
    import numpy as np

    rng = ys.max() - ys.min()
    if rng <= 0:
        return None, None
    norm = (ys - ys.min()) / rng
    peak_idx, _ = find_peaks(norm, prominence=0.05, distance=5)
    if peak_idx.size == 0:
        return None, None
    nearest_dist = float(np.min(np.abs(xs[peak_idx] - claim)))
    accurate = nearest_dist <= SPECTRUM_ACCURACY_TOL
    return accurate, consistent


def check_stability_both(parsed: str, material: dict):
    claimed_stable = parsed == "STABLE"
    consistent = stability_claim_consistent(claimed_stable, material["energy_above_hull"], tol_eV_atom=0.05)
    accurate = claimed_stable == material["is_stable"]  # MP's own strict flag
    # Raw label + true class kept on the record (not just the accurate bool) so
    # balanced accuracy / class-conditional rates can be computed downstream --
    # per the audit, raw accuracy on this arm is base-rate-confounded (most
    # sampled materials are MP-labeled unstable), so a single scalar hides that.
    return accurate, consistent, claimed_stable, bool(material["is_stable"])


def run_cell(modality: str, model_key: str, n: int, seed: int, api_key: str, materials_pool=None, mp_cursor=None):
    records = []
    if modality == "xrd":
        items = pilot.MODALITY_BUILDERS["xrd"](n, seed=3000 + seed * 100)
        for item in items:
            spec = MODELS[model_key]
            if spec["kind"] == "local":
                chain_text = pilot.run_local_qwen(item["image_path"], item["prompt"])
            else:
                chain_text, _ = pilot.run_api_openrouter(item["image_path"], item["prompt"], api_key, model=spec["api_model"])
            parsed = pilot.parse_chain(chain_text)
            if parsed is None:
                continue
            accurate, consistent = check_xrd_both(item, parsed)
            if accurate is None:
                continue
            records.append({
                "modality": modality, "model": model_key, "seed": seed,
                "source_id": item["source_file"], "accurate": accurate, "consistent": consistent,
            })

    elif modality == "spectrum":
        items = pilot.MODALITY_BUILDERS["spectrum"](n, seed=3000 + seed * 100)
        for item in items:
            spec = MODELS[model_key]
            if spec["kind"] == "local":
                chain_text = pilot.run_local_qwen(item["image_path"], item["prompt"])
            else:
                chain_text, _ = pilot.run_api_openrouter(item["image_path"], item["prompt"], api_key, model=spec["api_model"])
            parsed = pilot.parse_chain(chain_text)
            if parsed is None:
                continue
            accurate, consistent = check_spectrum_both(item, parsed)
            if accurate is None:
                continue
            records.append({
                "modality": modality, "model": model_key, "seed": seed,
                "source_id": item["source_file"], "accurate": accurate, "consistent": consistent,
            })

    elif modality == "stability":
        batch = materials_pool[mp_cursor[0] : mp_cursor[0] + n]
        mp_cursor[0] += n
        for material in batch:
            spec = MODELS[model_key]
            prompt = pilot_dft.PROMPTS["stability"].format(formula=material["formula_pretty"])
            if spec["kind"] == "local":
                chain_text = pilot_dft.run_text_local_qwen(prompt)
            else:
                chain_text, _ = pilot_dft.run_text_api_openrouter(prompt, api_key, model=spec["api_model"])
            parsed = pilot_dft.parse_dft_chain(chain_text)
            if parsed is None:
                continue
            accurate, consistent, claimed_stable, true_stable = check_stability_both(parsed, material)
            records.append({
                "modality": modality, "model": model_key, "seed": seed,
                "source_id": material["material_id"], "accurate": accurate, "consistent": consistent,
                "claimed_stable": claimed_stable, "true_stable": true_stable,
            })

    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--modalities", nargs="*", default=["xrd", "spectrum", "stability"])
    ap.add_argument("--models", nargs="*", default=list(MODELS.keys()))
    ap.add_argument("--out", default="experiments/exp3_results.jsonl")
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set.")

    with open(MP_DATA_PATH) as f:
        materials_pool = [json.loads(line) for line in f]
    random.Random(43).shuffle(materials_pool)  # different seed from exp2 to avoid identical draws
    mp_cursor = [0]

    all_records = []
    with open(args.out, "w") as out_f:
        for modality in args.modalities:
            for model_key in args.models:
                for seed in range(args.seeds):
                    t0 = time.time()
                    recs = run_cell(modality, model_key, args.n, seed, api_key, materials_pool, mp_cursor)
                    for r in recs:
                        out_f.write(json.dumps(r) + "\n")
                        out_f.flush()
                    all_records.extend(recs)
                    n_acc = sum(1 for r in recs if r["accurate"])
                    n_con = sum(1 for r in recs if r["consistent"])
                    print(
                        f"[{modality:10s}/{model_key:6s}/seed={seed}] n={len(recs)} "
                        f"accuracy={n_acc/max(len(recs),1):.3f} PCR={n_con/max(len(recs),1):.3f} "
                        f"({time.time()-t0:.1f}s)",
                        flush=True,
                    )

    print(f"\nTotal records: {len(all_records)}")
    print(f"Written to: {args.out}")


if __name__ == "__main__":
    main()
