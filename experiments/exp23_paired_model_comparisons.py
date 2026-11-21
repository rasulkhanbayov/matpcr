"""
exp23_paired_model_comparisons.py
=================================
KBS revision R1 (Reviewer 2 W4, W6): replace interval-overlap reasoning with
item-level tests of model differences, corrected for multiplicity, with effect
sizes, intervals and the minimum detectable difference.

Design facts this script relies on (verified from the records, see exp22):
  * Image arms (diffraction, microscopy, spectra): within each seed, all nine models
    were given the SAME 30 items (builder seed 2000+100*seed), so comparisons are
    PAIRED on the items both models answered checkably.
  * DFT arms (stability, metallicity, magnetism): each (model, seed) cell drew a
    DIFFERENT block of 30 materials, so comparisons are UNPAIRED.

For a pair of models (A, B) and a scope (one constraint type, or all six pooled):
  effect      = PCR_A - PCR_B, on the paired common items (image arms) plus each model's
                own items (DFT arms), pooled
  95% CI      = bootstrap (B=10,000): image arms resample paired items jointly, DFT arms
                resample each model's items independently
  p           = image-only scopes: exact McNemar on discordant pairs;
                DFT-only scopes: Fisher exact test;
                pooled scopes: two-sided bootstrap p (2*min(P(d<=0), P(d>=0)))
  MDE         = (z_0.975 + z_0.80) * bootstrap SE: the smallest difference the
                design detects with 80% power at alpha=0.05 (two-sided)
Families corrected with Holm (matpcr_metrics.holm_bonferroni):
  F1 headline: the five comparisons stated in the submitted manuscript
  F2 all 36 model pairs on overall PCR
  F3 microscopy: Qwen2.5-VL-7B vs each of the other eight models

Run: python experiments/exp23_paired_model_comparisons.py
Writes: experiments/exp23_results.json
"""

from __future__ import annotations

import itertools
import json
import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import final_oracle  # noqa: E402  near-hull stability abstention (final protocol)
import sys
from collections import defaultdict

import numpy as np
from scipy.stats import fisher_exact

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from matpcr_metrics import holm_bonferroni, mcnemar_exact  # noqa: E402

FILES = ["exp2_results_panther.jsonl", "exp2_dft_results_panther_20260805.jsonl",
         "exp2_gpt56sol_geometric.jsonl", "exp2_gpt56sol_dft.jsonl"]
MODELS = ["local", "gemini", "gpt4o", "claude", "opus46", "gpt56", "gpt56sol", "qwen3vl", "qwen3vl_thinking"]
LABEL = {"local": "Qwen2.5-VL-7B", "gemini": "Gemini 2.5 Flash Lite", "gpt4o": "GPT-4o",
         "claude": "Claude Sonnet 4.5", "opus46": "Claude Opus 4.6", "gpt56": "GPT-5.6-Terra",
         "gpt56sol": "GPT-5.6-Sol", "qwen3vl": "Qwen3-VL-8B-Instruct", "qwen3vl_thinking": "Qwen3-VL-8B-Thinking"}
IMAGE = ["xrd", "sem", "spectrum"]
DFT = ["stability", "metallicity", "magnetism"]
B = 10_000
Z = 1.959964 + 0.841621


def load():
    out = defaultdict(dict)  # (model, mod) -> {(seed, source_id): consistent}
    for f in FILES:
        for line in open(os.path.join(HERE, f)):
            r = json.loads(line)
            if not final_oracle.keep(r):
                continue
            out[(r["model"], r["modality"])][(r["seed"], r["source_id"])] = bool(r["consistent"])
    return out


def compare(data, a, b, scope, rng):
    mods = scope
    paired_a, paired_b, un_a, un_b = [], [], [], []
    for mod in mods:
        da, db = data[(a, mod)], data[(b, mod)]
        if mod in IMAGE:
            common = sorted(set(da) & set(db))
            paired_a += [da[k] for k in common]
            paired_b += [db[k] for k in common]
        else:
            un_a += list(da.values())
            un_b += list(db.values())
    pa, pb = np.array(paired_a, float), np.array(paired_b, float)
    ua, ub = np.array(un_a, float), np.array(un_b, float)

    def diff(pa_, pb_, ua_, ub_):
        na, nb = len(pa_) + len(ua_), len(pb_) + len(ub_)
        return (pa_.sum() + ua_.sum()) / na - (pb_.sum() + ub_.sum()) / nb

    est = diff(pa, pb, ua, ub)
    boots = np.empty(B)
    for i in range(B):
        ip = rng.integers(0, len(pa), len(pa)) if len(pa) else np.array([], int)
        ia = rng.integers(0, len(ua), len(ua)) if len(ua) else np.array([], int)
        ib = rng.integers(0, len(ub), len(ub)) if len(ub) else np.array([], int)
        boots[i] = diff(pa[ip], pb[ip], ua[ia], ub[ib])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    se = boots.std(ddof=1)
    if len(ua) == 0:  # image-only: exact McNemar on paired items
        mc = mcnemar_exact(list(pb.astype(bool)), list(pa.astype(bool)))
        p, test = mc["p_value"], "McNemar (paired)"
        extra = {"discordant_b_only": mc["c_fixes"], "discordant_a_only": mc["b_regressions"]}
    elif len(pa) == 0:  # DFT-only: Fisher exact
        table = [[int(ua.sum()), int(len(ua) - ua.sum())], [int(ub.sum()), int(len(ub) - ub.sum())]]
        p, test, extra = float(fisher_exact(table)[1]), "Fisher exact (unpaired)", {}
    else:
        p = float(min(1.0, 2 * min((boots <= 0).mean(), (boots >= 0).mean())))
        p, test, extra = max(p, 1 / B), "bootstrap (paired image + unpaired DFT)", {}
    return dict(a=a, b=b, scope="+".join(scope), effect=float(est), ci95=[float(lo), float(hi)],
                se=float(se), mde80=float(Z * se), p=float(p), test=test,
                n_paired=len(pa), n_a_unpaired=len(ua), n_b_unpaired=len(ub), **extra)


def add_holm(rows):
    adj = holm_bonferroni([r["p"] for r in rows])
    for r, q in zip(rows, adj):
        r["p_holm"] = float(q)
    return rows


def show(title, rows):
    print(f"\n{title}")
    print(f"{'A':<22}{'B':<22}{'diff':>7}  {'95% CI':<17}{'MDE80':>6}{'p':>10}{'p_Holm':>10}  test")
    for r in rows:
        print(f"{LABEL[r['a']]:<22}{LABEL[r['b']]:<22}{r['effect']:>+7.3f}  [{r['ci95'][0]:+.3f},{r['ci95'][1]:+.3f}]"
              f"{r['mde80']:>7.3f}{r['p']:>10.2g}{r['p_holm']:>10.2g}  {r['test']}")


def main():
    data = load()
    rng = np.random.default_rng(0)
    ALL = IMAGE + DFT
    mcnemar_check = mcnemar_exact([True, False], [False, True])
    assert "p_value" in mcnemar_check, mcnemar_check.keys()

    headline = [("gpt56", "gpt4o"), ("opus46", "claude"), ("qwen3vl_thinking", "qwen3vl"), ("gpt56sol", "gpt56")]
    f1 = [compare(data, a, b, ALL, rng) for a, b in headline]
    f1 += [compare(data, m, "local", ["sem"], rng) for m in MODELS if m != "local"]
    add_holm(f1)
    show("F1: comparisons stated in the submitted manuscript (overall; microscopy vs Qwen2.5-VL-7B), Holm over 12", f1)

    f2 = add_holm([compare(data, a, b, ALL, rng) for a, b in itertools.combinations(MODELS, 2)])
    n_sig = sum(r["p_holm"] < 0.05 for r in f2)
    print(f"\nF2: all 36 model pairs on overall PCR -> {n_sig} significant after Holm; "
          f"median MDE80 = {np.median([r['mde80'] for r in f2]):.3f}, range "
          f"{min(r['mde80'] for r in f2):.3f}-{max(r['mde80'] for r in f2):.3f}")

    per_type = {}
    for mod in ALL:
        rows = add_holm([compare(data, a, b, [mod], rng) for a, b in itertools.combinations(MODELS, 2)])
        per_type[mod] = rows
        print(f"  {mod:<12} pairs significant after Holm (36 tests): {sum(r['p_holm'] < 0.05 for r in rows):>2}; "
              f"median MDE80 {np.median([r['mde80'] for r in rows]):.3f}")

    json.dump({"F1_headline": f1, "F2_all_pairs_overall": f2, "per_type_all_pairs": per_type},
              open(os.path.join(HERE, "exp23_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
