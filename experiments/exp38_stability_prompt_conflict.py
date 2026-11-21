"""
exp38_stability_prompt_conflict.py
==================================
KBS revision R1: the second-annotator pass (exp37) exposed a conflict between the stability
prompt and the stability oracle. The prompt tells models to "treat any borderline or metastable
case as UNSTABLE", while the oracle requires STABLE whenever E_hull <= 0.05 eV/atom. A model that
follows the prompt on a near-hull material (0 < E_hull <= 0.05) is therefore flagged.

This script quantifies the effect by re-scoring every stability record under two alternative
rules that remove the conflict (E_hull = 0 and E_hull > 0.05 are scored exactly as before):
  abstain : 0 < E_hull <= 0.05 is excluded, like the metallicity abstention band
  accept  : in 0 < E_hull <= 0.05, UNSTABLE is also accepted (the prompt's own instruction)
A record in that band whose oracle verdict is "inconsistent" must have claimed UNSTABLE, so both
rules can be applied without the stored claim.

Outputs, for the main evaluation (exp2 records) and the common set (exp29):
  * per-model stability PCR under the original / abstain / accept rules
  * per-model pooled DFT and overall PCR, and the overall model ranking, under each rule
  * the stability precision audit with the conflicting cases removed

Run: MATPCR_DATA_ROOT=... python experiments/exp38_stability_prompt_conflict.py
Writes: experiments/exp38_results.json
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict

from scipy.stats import kendalltau

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", os.path.join(REPO, "data"))
MODELS = ["local", "gemini", "gpt4o", "claude", "opus46", "gpt56", "gpt56sol", "qwen3vl", "qwen3vl_thinking"]
MAIN = ["exp2_results_panther.jsonl", "exp2_dft_results_panther_20260805.jsonl",
        "exp2_gpt56sol_geometric.jsonl", "exp2_gpt56sol_dft.jsonl"]
COMMON = ["exp29_results.jsonl", "exp29_results_local.jsonl"]


def band(e):
    return 0 < e <= 0.05


def rescore(recs, hull, rule):
    out = []
    for r in recs:
        if r["modality"] != "stability" or not band(hull[r["source_id"]]):
            out.append(r["consistent"])
        elif rule == "original":
            out.append(r["consistent"])
        elif rule == "accept":
            out.append(True)        # STABLE was already consistent; UNSTABLE is now accepted too
        elif rule == "abstain":
            out.append(None)        # excluded
    return out


def summarize(recs, hull, label):
    res = {}
    for rule in ["original", "abstain", "accept"]:
        vals = rescore(recs, hull, rule)
        by = defaultdict(lambda: defaultdict(list))
        for r, v in zip(recs, vals):
            if v is not None:
                by[r["model"]][r["modality"]].append(v)
        res[rule] = {}
        for m in MODELS:
            if m not in by:
                continue
            st = by[m].get("stability", [])
            dft = [v for t in ("stability", "metallicity", "magnetism") for v in by[m].get(t, [])]
            allv = [v for t in by[m] for v in by[m][t]]
            res[rule][m] = dict(stability=sum(st) / len(st) if st else None, n_stability=len(st),
                                dft=sum(dft) / len(dft) if dft else None,
                                overall=sum(allv) / len(allv) if allv else None)
    models = [m for m in MODELS if m in res["original"]]
    print(f"\n=== {label}")
    print(f"{'model':<18}" + "".join(f"{r + ' stab':>16}{r + ' all':>14}" for r in res))
    for m in models:
        print(f"{m:<18}" + "".join(f"{res[r][m]['stability']:>16.3f}{(res[r][m]['overall'] or 0):>14.3f}" for r in res))
    for r in ["abstain", "accept"]:
        tau = kendalltau([res["original"][m]["overall"] for m in models], [res[r][m]["overall"] for m in models])[0]
        taus = kendalltau([res["original"][m]["stability"] for m in models], [res[r][m]["stability"] for m in models])[0]
        res[f"kendall_tau_overall_{r}"] = tau
        res[f"kendall_tau_stability_{r}"] = taus
        print(f"Kendall tau vs original, {r}: overall {tau:.3f}, stability {taus:.3f}")
    n_band = sum(1 for x in recs if x["modality"] == "stability" and band(hull[x["source_id"]]))
    n_stab = sum(1 for x in recs if x["modality"] == "stability")
    n_band_fired = sum(1 for x in recs if x["modality"] == "stability" and band(hull[x["source_id"]]) and not x["consistent"])
    res["band_share"] = dict(stability_records=n_stab, in_band=n_band, in_band_flagged=n_band_fired)
    print(f"stability records in 0<E_hull<=0.05: {n_band}/{n_stab}; flagged there (UNSTABLE claims): {n_band_fired}")
    return res


def main():
    mp = [json.loads(l) for l in open(os.path.join(DATA_ROOT, "mp_data", "mp_reference_batch.jsonl"))]
    hull = {m["material_id"]: m["energy_above_hull"] for m in mp}
    main_recs = [json.loads(l) for f in MAIN for l in open(os.path.join(HERE, f))]
    main_recs = [r for r in main_recs if r["modality"] != "stability" or r["source_id"] in hull]
    common = [json.loads(l) for f in COMMON if os.path.exists(os.path.join(HERE, f)) for l in open(os.path.join(HERE, f))]
    common = [dict(r) for r in common if r["checkable"]]
    out = {"main": summarize(main_recs, hull, "main evaluation (Table 2 records)"),
           "common": summarize(common, hull, "common class-balanced DFT set")}

    # precision audit: remove the conflicting fired cases (UNSTABLE claim with 0<E_hull<=0.05)
    import ast
    dft = [json.loads(l) for l in open(os.path.join(HERE, "halfB_dft_fired_cases.jsonl"))]
    fired = [r for r in dft if r["claim_type"] == "stability" and str(r["fired"]).lower() == "true"]
    txt = re.sub(r'("verdict"\s*:\s*)(real|false_positive|unsure)\b', r'\1"\2"',
                 open(os.path.join(REPO, "stability_halfB_review_2026-08-06.txt")).read())
    A = {r["case"]: r["verdict"] for r in json.loads(txt)["reviews"]}
    keep = []
    for i, r in enumerate(fired, 1):
        ref = r["reference"] if isinstance(r["reference"], dict) else ast.literal_eval(r["reference"])
        if not band(ref["energy_above_hull"]):
            keep.append(A[i])
    nr, nf = keep.count("real"), keep.count("false_positive")
    out["audit_without_conflict"] = dict(n=len(keep), real=nr, false_positive=nf, precision=nr / (nr + nf),
                                         removed=len(fired) - len(keep))
    print(f"\nStability audit without the conflicting band: {nr}/{nr + nf} = {nr / (nr + nf):.3f} "
          f"(removed {len(fired) - len(keep)} of {len(fired)} fired cases)")
    json.dump(out, open(os.path.join(HERE, "exp38_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
