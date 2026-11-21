"""
final_oracle.py
===============
Shared helper that applies the FINAL stability rule to already-collected records (KBS revision,
2026-10-16; see matpcr_metrics.stability_claim_consistent). Near-hull materials,
0 < E_hull <= 0.05 eV/atom, form an abstention band: their stability records are excluded from
PCR, exactly like the metallicity abstention band. Records store only the consistency verdict, and
outside the band the verdict is identical under the original and final rules, so re-scoring is
exact: band records are dropped and every other record is kept unchanged.

Set MATPCR_STABILITY_RULE=original to reproduce the original rule (no abstention), for the
Supplementary Information.
"""

from __future__ import annotations

import ast
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", os.path.join(os.path.dirname(HERE), "data"))
RULE = os.environ.get("MATPCR_STABILITY_RULE", "abstain")
TOL = 0.05
ON_HULL_ATOL = 1e-6
_HULL = None


def hull():
    global _HULL
    if _HULL is None:
        p = os.path.join(DATA_ROOT, "mp_data", "mp_reference_batch.jsonl")
        _HULL = {json.loads(l)["material_id"]: json.loads(l)["energy_above_hull"] for l in open(p)}
    return _HULL


def in_band(e_hull: float) -> bool:
    return ON_HULL_ATOL < e_hull <= TOL


def keep(record: dict, modality_key: str = "modality", id_key: str = "source_id") -> bool:
    """True if the record is scored under the active rule."""
    if RULE == "original" or record.get(modality_key) != "stability":
        return True
    return not in_band(hull()[record[id_key]])


def filter_records(records, modality_key: str = "modality", id_key: str = "source_id"):
    return [r for r in records if keep(r, modality_key, id_key)]


def keep_dft_fired(record: dict) -> bool:
    """For halfB_dft_fired_cases.jsonl records (claim_type + embedded reference)."""
    if RULE == "original" or record.get("claim_type") != "stability":
        return True
    ref = record["reference"] if isinstance(record["reference"], dict) else ast.literal_eval(record["reference"])
    return not in_band(ref["energy_above_hull"])
