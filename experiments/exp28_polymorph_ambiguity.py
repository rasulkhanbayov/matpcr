"""
exp28_polymorph_ambiguity.py
============================
KBS revision R1 (Reviewer 1 minor 1): the DFT prompts give the model a chemical
formula only, while each oracle checks the claim against ONE Materials Project entry
(material_id). Structures with the same composition (polymorphs) can differ in
hull energy, band gap and magnetization, so the formula alone may not determine the
reference label.

Part 1 (offline, archived 3,000-material batch): for formulas that occur more than
once in the batch, how often do the polymorphs disagree on each oracle's reference
class (near-hull / computed gap class with abstention / magnetic class)?

Part 2 (needs MP_API_KEY; --query): for every material evaluated in the main DFT
evaluation (exp2), fetch ALL Materials Project entries with the same reduced formula
(fields: material_id, energy_above_hull, band_gap, total_magnetization, nsites), then
re-score every recorded claim two ways and compare with the per-entry score:
  ground-state  : against the formula's lowest-E_hull polymorph
  any-polymorph : consistent if ANY polymorph of the formula supports the claim
The polymorph table is cached to $MATPCR_DATA_ROOT/mp_data/mp_polymorphs.json with its
retrieval date and database version.

Run: python experiments/exp28_polymorph_ambiguity.py [--query]
Writes: experiments/exp28_results.json
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import final_oracle  # noqa: E402  near-hull stability abstention (final protocol)
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", os.path.join(os.path.dirname(HERE), "data"))
BATCH = os.path.join(DATA_ROOT, "mp_data", "mp_reference_batch.jsonl")
POLY = os.path.join(DATA_ROOT, "mp_data", "mp_polymorphs.json")
# main-evaluation DFT records (the ones behind the Article's main table)
RECORD_FILES = ["exp2_dft_results_panther_20260805.jsonl", "exp2_gpt56sol_dft.jsonl"]


def ref_class(t, m):
    """Oracle reference class, or None if the oracle abstains."""
    if t == "stability":
        if final_oracle.RULE != "original" and final_oracle.in_band(m["energy_above_hull"]):
            return None  # near-hull abstention band (final protocol)
        return m["energy_above_hull"] <= 0.05
    if t == "metallicity":
        g = m["band_gap"]
        return True if g <= 0.05 else (False if g >= 0.20 else None)
    if t == "magnetism":
        n = m.get("nsites") or 0
        return (abs(m["total_magnetization"]) / n >= 0.05) if n else None
    raise ValueError(t)


def part1(batch):
    by_f = defaultdict(list)
    for m in batch:
        by_f[m["formula_pretty"]].append(m)
    multi = {f: v for f, v in by_f.items() if len(v) > 1}
    out = {"n_formulas": len(by_f), "n_polymorphic_formulas": len(multi),
           "n_entries_in_polymorphic_formulas": sum(len(v) for v in multi.values())}
    for t in ["stability", "metallicity", "magnetism"]:
        n = dis = 0
        for v in multi.values():
            cls = {ref_class(t, m) for m in v} - {None}
            if len(cls) >= 1:
                n += 1
                dis += len(cls) > 1
        out[t] = {"polymorphic_formulas_scored": n, "label_disagreement": dis, "share": dis / n if n else None}
    return out


def query_polymorphs(formulas):
    from mp_api.client import MPRester
    key = os.environ["MP_API_KEY"]
    table = {}
    with MPRester(key) as mpr:
        formulas = sorted(formulas)
        for i in range(0, len(formulas), 100):
            chunk = formulas[i:i + 100]
            docs = mpr.materials.summary.search(
                formula=chunk, fields=["material_id", "formula_pretty", "energy_above_hull", "band_gap",
                                       "total_magnetization", "nsites"])
            for d in docs:
                table.setdefault(d.formula_pretty, []).append(dict(
                    material_id=str(d.material_id), energy_above_hull=d.energy_above_hull, band_gap=d.band_gap,
                    total_magnetization=d.total_magnetization, nsites=d.nsites))
            print(f"  queried {min(i + 100, len(formulas))}/{len(formulas)} formulas", flush=True)
        try:
            db_version = mpr.get_database_version()
        except Exception:  # noqa: BLE001
            db_version = None
    return {"retrieval_date": datetime.date.today().isoformat(), "database_version": db_version,
            "fields": ["material_id", "energy_above_hull", "band_gap", "total_magnetization", "nsites"],
            "polymorphs": table}


def part2(batch_by_id, poly):
    recs = []
    for f in RECORD_FILES:
        p = os.path.join(HERE, f)
        if os.path.exists(p):
            for line in open(p):
                r = json.loads(line)
                if r.get("consistent") is not None and final_oracle.keep(r):
                    recs.append(r)
    out = {}
    # Magnetism is omitted from re-scoring: a MAGNETIC claim can be inconsistent because of its
    # magnitude while its class matches, and the result files do not store the claimed class,
    # so the claimed class cannot be recovered from the consistency label alone.
    for t in ["stability", "metallicity"]:
        n = agree_gs = agree_any_change = 0
        flips = defaultdict(int)
        for r in recs:
            if r["modality"] != t:
                continue
            m = batch_by_id[r["source_id"]]
            entries = [e for e in poly["polymorphs"].get(m["formula_pretty"], [])
                       if e["energy_above_hull"] is not None and e["band_gap"] is not None]
            if not entries:
                continue
            own = ref_class(t, m)
            claim_pos = own if r["consistent"] else (not own)   # binary class claimed by the model
            gs = min(entries, key=lambda e: e["energy_above_hull"])
            gs_cls = ref_class(t, gs)
            any_cls = {ref_class(t, e) for e in entries} - {None}
            n += 1
            gs_consistent = (gs_cls == claim_pos) if gs_cls is not None else None
            any_consistent = claim_pos in any_cls
            agree_gs += gs_consistent == r["consistent"]
            flips[(r["consistent"], gs_consistent)] += 1
            agree_any_change += any_consistent != r["consistent"]
        out[t] = {"n_records": n,
                  "agree_with_ground_state_scoring": agree_gs / n if n else None,
                  "changed_by_any_polymorph_scoring": agree_any_change / n if n else None,
                  "transitions_entry_to_groundstate": {f"{a}->{b}": c for (a, b), c in flips.items()}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", action="store_true")
    args = ap.parse_args()
    batch = [json.loads(l) for l in open(BATCH)]
    res = {"part1_within_batch": part1(batch)}
    print(json.dumps(res["part1_within_batch"], indent=1))
    if args.query:
        used = set()
        for f in RECORD_FILES:
            p = os.path.join(HERE, f)
            if os.path.exists(p):
                used |= {json.loads(l)["source_id"] for l in open(p)}
        by_id = {m["material_id"]: m for m in batch}
        formulas = {by_id[i]["formula_pretty"] for i in used if i in by_id}
        if os.path.exists(POLY):
            poly = json.load(open(POLY))
            missing = formulas - set(poly["polymorphs"])
            if missing:
                print(f"cache lacks {len(missing)} formulas; re-querying all")
                poly = query_polymorphs(formulas)
        else:
            poly = query_polymorphs(formulas)
        json.dump(poly, open(POLY, "w"))
        res["part2_meta"] = {k: poly[k] for k in ("retrieval_date", "database_version")}
        res["part2_formula_level_rescoring"] = part2(by_id, poly)
        print(json.dumps(res["part2_formula_level_rescoring"], indent=1))
    json.dump(res, open(os.path.join(HERE, "exp28_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
