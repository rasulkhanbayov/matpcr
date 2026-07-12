"""
mp_fetch_reference_data.py
============================
Pull real Materials Project reference values for the 3 DFT-grounded oracles'
Half-A (positive control) harness:
  - stability_claim_consistent   <- energy_above_hull_eV_atom
  - metallicity_claim_consistent <- band_gap_eV
  - property_sign_magnitude_consistent <- total_magnetization (target property,
    chosen 2026-07-09 for its 100% coverage and real sign balance -- see
    CLAUDE.md "Materials Project" section for why bulk/shear modulus and
    formation_energy_per_atom were rejected).

This is real reference DATA, not a Half-B precision judgment -- pulling real
numbers from a public database is software/data plumbing, not a DFT-protocol
trust decision. Mustafa's sign-off (per CLAUDE.md SS8 rule 1) is required
before HALF-B (treating these values as ground truth for precision numbers)
proceeds, but is NOT required for Half-A, which only tests whether the
oracle's comparison logic correctly recovers synthetic violations against
known values -- pure software correctness.

Requires MP_API_KEY in the environment (see /tmp/matpcr_secrets/.env).

Run: MP_API_KEY=... python3 experiments/mp_fetch_reference_data.py --n 2000
"""

from __future__ import annotations

import argparse
import json
import os

from mp_api.client import MPRester

OUT_PATH = "/ephemeral/matpcr/mp_data/mp_reference_batch.jsonl"

FIELDS = [
    "material_id",
    "formula_pretty",
    "energy_above_hull",
    "is_stable",
    "band_gap",
    "is_metal",
    "total_magnetization",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--out", default=OUT_PATH)
    args = ap.parse_args()

    api_key = os.environ.get("MP_API_KEY")
    if not api_key:
        raise SystemExit("MP_API_KEY not set in environment.")

    chunk_size = 1000  # confirmed working; larger chunk_size (e.g. 3000) hits an API limit
    num_chunks = max(1, -(-args.n // chunk_size))  # ceiling division

    with MPRester(api_key) as mpr:
        docs = mpr.materials.summary.search(
            num_chunks=num_chunks, chunk_size=chunk_size, fields=FIELDS
        )

    n_written = 0
    with open(args.out, "w") as f:
        for d in docs:
            if d.energy_above_hull is None or d.band_gap is None or d.total_magnetization is None:
                continue
            record = {
                "material_id": str(d.material_id),
                "formula_pretty": d.formula_pretty,
                "energy_above_hull": d.energy_above_hull,
                "is_stable": d.is_stable,
                "band_gap": d.band_gap,
                "is_metal": d.is_metal,
                "total_magnetization": d.total_magnetization,
            }
            f.write(json.dumps(record) + "\n")
            n_written += 1

    print(f"Fetched {len(docs)} materials, wrote {n_written} with all required fields to {args.out}")


if __name__ == "__main__":
    main()
