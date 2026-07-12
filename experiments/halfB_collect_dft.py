"""
halfB_collect_dft.py
=====================
Experiment 1, Half-B data collection for the 3 DFT-grounded oracles
(stability, metallicity, property sign/magnitude), mirroring
halfB_collect.py's pattern for the geometric oracles.

SCOPE NOTE: per the 2026-07-XX PI override (Hasan instructed proceeding
without Mustafa's DFT-protocol sign-off -- see CLAUDE.md "Mustafa's sign-off
scope" + "OVERRIDE" entries), this collects real Half-B material for these 3
oracles. The DFT precision numbers that come out of the eventual human review
of this material are NOT YET independently validated by the domain
co-author -- flag this explicitly wherever these numbers are reported.

Method: real Materials Project formulas (text-only prompt, no image -- see
pilot_dft.py) -> real model claim (STABLE/UNSTABLE, METALLIC/NONMETALLIC,
MAGNETIC/NONMAGNETIC) -> parsed -> checked against the REAL MP reference
value for that exact material via the actual oracle function -> if the
oracle says "inconsistent" (fired), keep the case for review. Loop per claim
type until >=target fired cases accumulate.

For the sign/magnitude oracle, the model's binary MAGNETIC/NONMAGNETIC claim
is converted to a representative numeric claim (0.0 for NONMAGNETIC; the
reference's own sign preserved but magnitude probed for MAGNETIC, since the
model was not asked for a numeric value in the pilot's binary framing --
this is a genuine adaptation, documented below) before calling
property_sign_magnitude_consistent, since that oracle takes a numeric claim,
not a boolean.

Run: python3 experiments/halfB_collect_dft.py --target 100
"""

from __future__ import annotations

import os

os.environ["HF_HOME"] = "/ephemeral/matpcr/hf_cache"

import argparse
import json
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import (  # noqa: E402
    stability_claim_consistent,
    metallicity_claim_consistent,
    property_sign_magnitude_consistent,
)

import pilot_dft  # noqa: E402  reuse PROMPTS, parse_dft_chain, run_text_local_qwen, run_text_api_openrouter

MP_DATA_PATH = "/ephemeral/matpcr/mp_data/mp_reference_batch.jsonl"


def load_materials():
    with open(MP_DATA_PATH) as f:
        return [json.loads(line) for line in f]


def check_oracle(claim_type: str, parsed: str, material: dict):
    """Return True (consistent) / False (fired) for this real claim against
    the real MP reference value, or None if it can't be evaluated."""
    if claim_type == "stability":
        claimed_stable = parsed == "STABLE"
        return stability_claim_consistent(claimed_stable, material["energy_above_hull"], tol_eV_atom=0.05)

    if claim_type == "metallicity":
        claimed_metallic = parsed == "METALLIC"
        return metallicity_claim_consistent(claimed_metallic, material["band_gap"], gap_tol_eV=0.05)

    if claim_type == "magnetism":
        ref = material["total_magnetization"]
        # The pilot's prompt asks for a binary MAGNETIC/NONMAGNETIC judgment,
        # not a numeric value -- property_sign_magnitude_consistent needs a
        # number. Convert the binary claim to the most representative numeric
        # claim consistent with that binary judgment: NONMAGNETIC -> 0.0;
        # MAGNETIC -> the reference's own sign with unit magnitude (1.0 or
        # -1.0), which tests whether the model's binary judgment agrees with
        # whether the material actually has nonzero magnetization, without
        # presupposing a magnitude the model was never asked to state.
        if parsed == "NONMAGNETIC":
            claim = 0.0
        else:
            claim = 1.0 if ref >= 0 else -1.0
        return property_sign_magnitude_consistent(claim, ref, rel_tol=1.0)

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
    print(f"Loaded {len(materials)} real materials from Materials Project.")

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

                        parsed = pilot_dft.parse_dft_chain(chain_text)
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
                            },
                            "prompt": prompt,
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
                print(f"  WARNING: {claim_type} only reached {fired_count}/{args.target} fired cases.")

    print(f"\nTotal API cost: ${total_cost:.4f}")
    print(f"Fired cases written to: {args.out}")


if __name__ == "__main__":
    main()
