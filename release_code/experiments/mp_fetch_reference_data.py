"""
mp_fetch_reference_data.py
============================
Pull real Materials Project reference values for the 3 DFT-grounded oracles'
Half-A (positive control) harness:
  - stability_claim_consistent      <- energy_above_hull_eV_atom
  - metallicity_claim_consistent    <- band_gap_eV
  - magnetism_magnitude_consistent  <- total_magnetization (Bohr magnetons,
    RAW/un-normalized) + nsites (atom count, for per-atom normalization inside
    the oracle). Target property chosen 2026-07-09 for its 100% coverage and
    real magnetic/non-magnetic class balance -- see CLAUDE.md "Materials
    Project" section for why bulk/shear modulus and formation_energy_per_atom
    were rejected.

Per the domain co-author's review (M.K., 2026-07): Materials Project is an
acceptable primary computational reference for all three oracles -- rerunning
DFT for the full sample is not necessary -- but the manuscript must describe
these values as STANDARDIZED COMPUTATIONAL REFERENCES, not experimental
ground truth, and must pin the exact database/API version, retrieval date,
calculation type, and fields used. This script now records that provenance
alongside the data (PROVENANCE dict below, written to a sidecar file) rather
than leaving it to be reconstructed after the fact.

This is real reference DATA, not a Half-B precision judgment -- pulling real
numbers from a public database is software/data plumbing, not a DFT-protocol
trust decision. Mustafa's sign-off (per CLAUDE.md SS8 rule 1) was required
before HALF-B (treating these values as ground truth for precision numbers)
proceeded, and has now been given (2026-07, see VERSION2/Dr_mustafas_comments)
conditional on the oracle corrections implemented in matpcr_metrics.py.

Requires MP_API_KEY in the environment (see /tmp/matpcr_secrets/.env).

Run: MP_API_KEY=... python3 experiments/mp_fetch_reference_data.py --n 3000
"""

from __future__ import annotations

import argparse
import json
import os

from mp_api.client import MPRester

# MATPCR_DATA_ROOT is host-specific -- set it in the environment before
# running on a new host; see experiments/slurm/README.md.
MATPCR_DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", "/ephemeral/matpcr")
OUT_PATH = os.path.join(MATPCR_DATA_ROOT, "mp_data", "mp_reference_batch.jsonl")
PROVENANCE_PATH = os.path.join(MATPCR_DATA_ROOT, "mp_data", "mp_provenance.json")

# All fields actually consumed by the 3 DFT-grounded oracles. "nsites" is the
# atom count needed to convert MP's raw total_magnetization (Bohr magnetons,
# whole-cell) into the per-atom magnitude the corrected magnetism oracle
# requires -- added per the co-author's magnetism redesign (raw totals across
# cells of different sizes are not physically comparable without this).
FIELDS = [
    "material_id",
    "formula_pretty",
    "energy_above_hull",
    "is_stable",
    "band_gap",
    "is_metal",
    "total_magnetization",
    "nsites",
]

CALCULATION_TYPE = (
    "GGA/GGA+U relaxation, Materials Project standard workflow "
    "(https://docs.materialsproject.org/methodology/materials-methodology) "
    "-- semilocal functional; known to underestimate band gaps, which is why "
    "the metallicity oracle restricts to a clearly-gapped/clearly-gapless "
    "decision with an explicit abstention band rather than a single threshold."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--out", default=OUT_PATH)
    ap.add_argument("--provenance_out", default=PROVENANCE_PATH)
    ap.add_argument(
        "--retrieval_date", required=True,
        help="Date this pull is performed, e.g. 2026-07-16 -- passed explicitly "
             "rather than stamped automatically, since this environment disallows "
             "wall-clock calls inside orchestrated scripts.",
    )
    args = ap.parse_args()

    api_key = os.environ.get("MP_API_KEY")
    if not api_key:
        raise SystemExit("MP_API_KEY not set in environment.")

    chunk_size = 1000  # confirmed working; larger chunk_size (e.g. 3000) hits an API limit
    num_chunks = max(1, -(-args.n // chunk_size))  # ceiling division

    with MPRester(api_key) as mpr:
        db_version = mpr.get_database_version()
        docs = mpr.materials.summary.search(
            num_chunks=num_chunks, chunk_size=chunk_size, fields=FIELDS
        )

    n_written = 0
    n_skipped_no_nsites = 0
    with open(args.out, "w") as f:
        for d in docs:
            if d.energy_above_hull is None or d.band_gap is None or d.total_magnetization is None:
                continue
            if not d.nsites or d.nsites <= 0:
                n_skipped_no_nsites += 1
                continue
            record = {
                "material_id": str(d.material_id),
                "formula_pretty": d.formula_pretty,
                "energy_above_hull": d.energy_above_hull,
                "is_stable": d.is_stable,
                "band_gap": d.band_gap,
                "is_metal": d.is_metal,
                "total_magnetization": d.total_magnetization,
                "nsites": d.nsites,
            }
            f.write(json.dumps(record) + "\n")
            n_written += 1

    provenance = {
        "source": "Materials Project (materialsproject.org)",
        "client": "mp-api",
        "database_version": db_version,
        "retrieval_date": args.retrieval_date,
        "calculation_type": CALCULATION_TYPE,
        "fields_pulled": FIELDS,
        "n_requested": args.n,
        "n_docs_returned": len(docs),
        "n_written_with_all_fields": n_written,
        "n_skipped_missing_nsites": n_skipped_no_nsites,
        "note": (
            "These are standardized computational references (Materials Project's "
            "own DFT calculations), not experimental ground truth. Own-DFT "
            "validation is reserved for missing or clearly questionable cases, "
            "per the domain co-author's review, not run over this full sample."
        ),
    }
    with open(args.provenance_out, "w") as f:
        json.dump(provenance, f, indent=2)

    print(f"Fetched {len(docs)} materials, wrote {n_written} with all required fields to {args.out}")
    print(f"Skipped {n_skipped_no_nsites} with missing nsites (needed for magnetism-per-atom normalization).")
    print(f"Provenance written to {args.provenance_out}: MP database_version={db_version}, retrieval_date={args.retrieval_date}")


if __name__ == "__main__":
    main()
