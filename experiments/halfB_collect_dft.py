"""
halfB_collect_dft.py
=====================
Experiment 1, Half-B data collection for the 3 DFT-grounded oracles
(stability, metallicity, magnetism-magnitude), mirroring halfB_collect.py's
pattern for the geometric oracles.

SCOPE NOTE: per the domain co-author's review (M.K., 2026-07, see
VERSION2/Dr_mustafas_comments), Materials Project is now an APPROVED
reference source for completing Half-B for all 3 oracles, conditional on the
oracle corrections in matpcr_metrics.py -- all implemented. This is a genuine
re-collection, not a re-aggregation: the metallicity and magnetism oracle
signatures changed (metallicity's abstention band; magnetism's
classify-then-magnitude redesign), and the magnetism prompt itself changed
(pilot_dft.py now asks for a magnitude estimate when the model claims
MAGNETIC, since the corrected oracle needs a genuine magnitude claim, not
a binary-classification proxy).

Method: real Materials Project formulas (text-only prompt, no image -- see
pilot_dft.py) -> real model claim -> parsed -> checked against the REAL MP
reference value for that exact material via the actual oracle function -> if
the oracle says "inconsistent" (fired), keep the case for review. Loop per
claim type until >=target fired cases accumulate.

Magnetism uses parse_magnetism_chain (not the generic parse_dft_chain) to get
both the classification AND the claimed magnitude (muB/atom) in one parse,
matching what magnetism_magnitude_consistent actually needs.

Run: python3 experiments/halfB_collect_dft.py --target 100
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
from matpcr_metrics import (  # noqa: E402
    stability_claim_consistent,
    metallicity_claim_consistent,
    magnetism_magnitude_consistent,
)

import pilot_dft  # noqa: E402  reuse PROMPTS, parse_dft_chain, parse_magnetism_chain, run_text_local_qwen, run_text_api_openrouter

MP_DATA_PATH = os.path.join(MATPCR_DATA_ROOT, "mp_data", "mp_reference_batch.jsonl")
MAGNETIC_THRESHOLD_MUB_PER_ATOM = 0.05
METALLICITY_METAL_MAX_EV = 0.05
METALLICITY_GAP_MIN_EV = 0.20


def load_materials():
    with open(MP_DATA_PATH) as f:
        return [json.loads(line) for line in f]


def check_oracle(claim_type: str, parsed, material: dict):
    """Return True (consistent) / False (fired) / None (not checkable) for
    this real claim against the real MP reference value.

    `parsed` is a bare label string for stability/metallicity, or the
    (classification, magnitude) tuple from parse_magnetism_chain for
    magnetism.
    """
    if claim_type == "stability":
        claimed_stable = parsed == "STABLE"
        return stability_claim_consistent(claimed_stable, material["energy_above_hull"], tol_eV_atom=0.05)

    if claim_type == "metallicity":
        claimed_metallic = parsed == "METALLIC"
        return metallicity_claim_consistent(
            claimed_metallic, material["band_gap"],
            metal_max_eV=METALLICITY_METAL_MAX_EV, gap_min_eV=METALLICITY_GAP_MIN_EV,
        )

    if claim_type == "magnetism":
        classification, magnitude = parsed
        if classification is None:
            return None
        n_atoms = material.get("nsites")
        if not n_atoms or n_atoms <= 0:
            return None
        claimed_magnetic = classification == "MAGNETIC"
        return magnetism_magnitude_consistent(
            claimed_magnetic, magnitude, material["total_magnetization"], n_atoms,
            magnetic_threshold_muB_per_atom=MAGNETIC_THRESHOLD_MUB_PER_ATOM,
        )

    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=100)
    ap.add_argument("--claim_types", nargs="*", default=["stability", "metallicity", "magnetism"])
    ap.add_argument("--models", nargs="*", default=["local", "api"])
    ap.add_argument("--batch_size", type=int, default=30)
    ap.add_argument("--max_rounds", type=int, default=30)
    ap.add_argument("--out", default="experiments/halfB_dft_fired_cases.jsonl")
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if "api" in args.models and not api_key:
        print("WARNING: OPENROUTER_API_KEY not set; skipping API model.")
        args.models = [m for m in args.models if m != "api"]

    materials = load_materials()
    # Shuffle before walking the cursor: the raw MP pull is NOT randomly
    # ordered (confirmed directly -- the first 200 materials in a fresh pull
    # were 89.5% non-magnetic vs. 25% over the full 3000-material pool),
    # which without shuffling starved the magnetism collection of any fired
    # cases for many rounds. A fixed seed keeps this reproducible.
    random.Random(7).shuffle(materials)
    print(f"Loaded {len(materials)} real materials from Materials Project (shuffled, seed=7).")

    total_cost = 0.0

    with open(args.out, "w") as out_f:
        for claim_type in args.claim_types:
            fired_count = 0
            round_i = 0
            cursor = 0  # walk through materials without replacement across rounds
            print(f"\n=== {claim_type}: collecting until {args.target} fired cases ===")

            while fired_count < args.target and round_i < args.max_rounds:
                round_i += 1
                batch = materials[cursor : cursor + args.batch_size]
                cursor += args.batch_size
                if not batch:
                    print(f"  Ran out of materials for {claim_type} after round {round_i}.")
                    break

                for m in batch:
                    prompt = pilot_dft.PROMPTS[claim_type].format(formula=m["formula_pretty"])
                    for model_key in args.models:
                        t0 = time.time()
                        try:
                            if model_key == "local":
                                chain_text = pilot_dft.run_text_local_qwen(prompt)
                                cost = 0.0
                            else:
                                chain_text, cost = pilot_dft.run_text_api_openrouter(prompt, api_key)
                                cost = cost or 0.0
                                total_cost += cost
                        except Exception as e:
                            chain_text = f"__ERROR__: {e}"
                            cost = 0.0
                        elapsed = time.time() - t0

                        if claim_type == "magnetism":
                            parsed = pilot_dft.parse_magnetism_chain(chain_text)
                            parsed_for_record = {"classification": parsed[0], "magnitude_muB_per_atom": parsed[1]}
                            if parsed[0] is None:
                                continue
                        else:
                            parsed = pilot_dft.parse_dft_chain(chain_text)
                            parsed_for_record = parsed
                            if parsed is None:
                                continue

                        try:
                            oracle_result = check_oracle(claim_type, parsed, m)
                        except Exception as e:
                            oracle_result = None
                            print(f"  [{claim_type}/{model_key}] oracle check error: {e}")
                        if oracle_result is None:
                            continue

                        fired = not oracle_result
                        record = {
                            "claim_type": claim_type,
                            "model": model_key,
                            "material_id": m["material_id"],
                            "formula": m["formula_pretty"],
                            "reference": {
                                "energy_above_hull": m["energy_above_hull"],
                                "is_stable": m["is_stable"],
                                "band_gap": m["band_gap"],
                                "is_metal": m["is_metal"],
                                "total_magnetization": m["total_magnetization"],
                                "nsites": m.get("nsites"),
                            },
                            "prompt": prompt,
                            "chain_text": chain_text,
                            "parsed": parsed_for_record,
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
                print(f"  WARNING: {claim_type} only reached {fired_count}/{args.target} fired cases.")

    print(f"\nTotal API cost: ${total_cost:.4f}")
    print(f"Fired cases written to: {args.out}")


if __name__ == "__main__":
    main()
