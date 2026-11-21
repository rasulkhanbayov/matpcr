"""
exp22_coverage.py
=================
KBS revision R1 (Reviewer 1 M4, Reviewer 2 W5): how much of each
(model, constraint-type) cell PCR actually covers, and how the model ordering
changes under different treatments of non-checkable chains.

Definitions (per model x constraint type, pooled over S=3 seeds, 30 attempted
items per seed, i.e. 90 attempted items per cell):
  attempted   items sent to the model (90 per cell; every logged cell has n_items=30)
  evaluable   items for which the oracle has a defined reference, independent of the model:
                - DFT arms: reconstructed exactly. Each cell drew a contiguous block of 30
                  materials from the fixed-seed shuffled Materials Project pool
                  (exp2_pcr_sweep.py, Random(42)); every recorded material maps to exactly one
                  block. Metallicity items with a band gap inside the 0.05-0.20 eV abstention
                  band are non-evaluable.
                - Image arms: all nine models saw the same 30 items per seed (builder seed
                  2000 + 100*seed). An item counts as evaluable if at least one model produced a
                  checkable claim on it. This is a lower bound on true evaluability: an item no
                  model answered parseably counts as non-evaluable.
  checkable   evaluable items whose chain stated a parseable claim the oracle could score
              (the records in the result files). This share also absorbs the rare API
              failures/timeouts, which the result files do not record separately.
  coverage    checkable / evaluable  (model-attributable share)

Conventions for non-checkable evaluable items:
  excluded  (paper)   PCR = consistent / checkable
  penalised           PCR = consistent / evaluable           (silence counts as a violation)
  lenient             PCR = (consistent + non-checkable) / evaluable

Run: python experiments/exp22_coverage.py
Writes: experiments/exp22_results.json
"""

from __future__ import annotations

import json
import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import final_oracle  # noqa: E402  near-hull stability abstention (final protocol)
import random
from collections import defaultdict

from scipy.stats import kendalltau

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", os.path.join(os.path.dirname(HERE), "data"))
FILES = ["exp2_results_panther.jsonl", "exp2_dft_results_panther_20260805.jsonl",
         "exp2_gpt56sol_geometric.jsonl", "exp2_gpt56sol_dft.jsonl"]
MODELS = ["local", "gemini", "gpt4o", "claude", "opus46", "gpt56", "gpt56sol", "qwen3vl", "qwen3vl_thinking"]
LABEL = {"local": "Qwen2.5-VL-7B", "gemini": "Gemini 2.5 Flash Lite", "gpt4o": "GPT-4o",
         "claude": "Claude Sonnet 4.5", "opus46": "Claude Opus 4.6", "gpt56": "GPT-5.6-Terra",
         "gpt56sol": "GPT-5.6-Sol", "qwen3vl": "Qwen3-VL-8B-Instruct", "qwen3vl_thinking": "Qwen3-VL-8B-Thinking"}
IMAGE = ["xrd", "sem", "spectrum"]
DFT = ["stability", "metallicity", "magnetism"]
BLOCK = 30
SEEDS = 3


def main() -> None:
    recs = final_oracle.filter_records([json.loads(l) for f in FILES for l in open(os.path.join(HERE, f))])
    pool = [json.loads(l) for l in open(os.path.join(DATA_ROOT, "mp_data", "mp_reference_batch.jsonl"))]
    random.Random(42).shuffle(pool)
    pos = {m["material_id"]: i for i, m in enumerate(pool)}

    cell = defaultdict(list)  # (model, mod, seed) -> list of (source_id, consistent)
    for r in recs:
        cell[(r["model"], r["modality"], r["seed"])].append((r["source_id"], r["consistent"]))

    # evaluable item sets per (model, mod, seed)
    evaluable = {}
    for mod in IMAGE:
        for s in range(SEEDS):
            union = {sid for (m, mo, se), v in cell.items() if mo == mod and se == s for sid, _ in v}
            for m in MODELS:
                evaluable[(m, mod, s)] = union
    for (m, mod, s), v in cell.items():
        if mod not in DFT:
            continue
        blocks = {pos[sid] // BLOCK for sid, _ in v}
        assert len(blocks) == 1, (m, mod, s, blocks)
        b = blocks.pop()
        mats = pool[b * BLOCK:(b + 1) * BLOCK]
        if mod == "metallicity":
            mats = [x for x in mats if not (0.05 < x["band_gap"] < 0.20)]
        if mod == "stability" and final_oracle.RULE != "original":
            mats = [x for x in mats if not final_oracle.in_band(x["energy_above_hull"])]
        evaluable[(m, mod, s)] = {x["material_id"] for x in mats}

    table = {}
    for m in MODELS:
        for mod in IMAGE + DFT:
            att = ev = ch = co = 0
            for s in range(SEEDS):
                v = cell.get((m, mod, s), [])
                e = evaluable.get((m, mod, s), set())
                assert {sid for sid, _ in v} <= e
                att += BLOCK
                ev += len(e)
                ch += len(v)
                co += sum(1 for _, c in v if c)
            table[(m, mod)] = dict(attempted=att, evaluable=ev, checkable=ch, consistent=co,
                                   coverage=ch / ev, pcr_excluded=co / ch, pcr_penalised=co / ev,
                                   pcr_lenient=(co + ev - ch) / ev)

    def overall(m, key):
        t = [table[(m, mod)] for mod in IMAGE + DFT]
        co = sum(x["consistent"] for x in t); ch = sum(x["checkable"] for x in t); ev = sum(x["evaluable"] for x in t)
        return {"excluded": co / ch, "penalised": co / ev, "lenient": (co + ev - ch) / ev, "coverage": ch / ev}[key]

    print("Coverage = checkable / evaluable (pooled over 3 seeds)\n")
    hdr = f"{'Model':<24}" + "".join(f"{x:>12}" for x in IMAGE + DFT) + f"{'All':>8}"
    print(hdr)
    for m in MODELS:
        print(f"{LABEL[m]:<24}" + "".join(f"{table[(m, mod)]['coverage']:>12.3f}" for mod in IMAGE + DFT)
              + f"{overall(m, 'coverage'):>8.3f}")
    print("\nEvaluable items per cell (of 90 attempted):")
    print("  " + ", ".join(f"{mod}: {sorted({table[(m, mod)]['evaluable'] for m in MODELS})}" for mod in IMAGE + DFT))

    print("\nOverall PCR under three conventions, and rank (1 = best):")
    convs = ["excluded", "penalised", "lenient"]
    vals = {c: {m: overall(m, c) for m in MODELS} for c in convs}
    rank = {c: {m: 1 + sorted(MODELS, key=lambda x: -vals[c][x]).index(m) for m in MODELS} for c in convs}
    print(f"{'Model':<24}" + "".join(f"{c:>18}" for c in convs))
    for m in MODELS:
        print(f"{LABEL[m]:<24}" + "".join(f"{vals[c][m]:>12.3f} (#{rank[c][m]})" for c in convs))
    taus = {}
    for c in ["penalised", "lenient"]:
        tau, p = kendalltau([vals["excluded"][m] for m in MODELS], [vals[c][m] for m in MODELS])
        taus[c] = (tau, p)
        print(f"Kendall tau, excluded vs {c}: {tau:.3f} (p={p:.3g})")

    per_type_tau = {}
    for mod in IMAGE + DFT:
        a = [table[(m, mod)]["pcr_excluded"] for m in MODELS]
        per_type_tau[mod] = {c: kendalltau(a, [table[(m, mod)][f"pcr_{c}"] for m in MODELS])[0]
                             for c in ["penalised", "lenient"]}
    print("\nPer constraint type, Kendall tau of the model ordering vs the excluded convention:")
    for mod, d in per_type_tau.items():
        print(f"  {mod:<12} penalised {d['penalised']:.3f}   lenient {d['lenient']:.3f}")

    out = {"cells": {f"{m}|{mod}": v for (m, mod), v in table.items()},
           "overall": vals, "rank": rank, "kendall_tau_overall": taus, "kendall_tau_per_type": per_type_tau}
    json.dump(out, open(os.path.join(HERE, "exp22_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
