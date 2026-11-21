"""
exp37_two_annotator_precision.py
================================
KBS revision R1 (Reviewer 2 W3): oracle precision under each of the two annotators.

Annotator A (first) labelled every audited fired case. Annotator B (second) labelled a random
subsample of 30 per family, stratified by A's verdict (exp32: false positives over-sampled, at least
3). B's precision for the whole audited population is therefore the stratum-weighted estimate

    p_B = sum_s (N_s / N) * (share of B-"real" within the sampled cases of stratum s),

with strata s in {A-real, A-false-positive} (A-unsure cases are excluded, as in Table 1). The 95%
interval combines per-stratum Jeffreys posteriors (10,000 draws). Also reports A's
precision on the same 30 cases, raw agreement and Cohen's kappa (from exp13), and the direction of
disagreements.

Run: python experiments/exp37_two_annotator_precision.py
Writes: experiments/exp37_results.json
"""

from __future__ import annotations

import json
import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import final_oracle  # noqa: E402  near-hull stability abstention (final protocol)
import re

import numpy as np

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import cohens_kappa  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HR = os.path.join(REPO, "KBS_revision_R1", "human_review")
FAM = {"xrd": "xrd.txt", "sem": "sem.txt", "spectrum": "spectrum_halfB_review_2026-08-06.txt",
       "stability": "stability_halfB_review_2026-08-06.txt", "metallicity": "metallicity_halfB_review_2026-08-06.txt",
       "magnetism": "magnetism_halfB_review_2026-08-06.txt"}
KAPPA = {"xrd": "xrd", "sem": "sem", "spectrum": "spectrum", "stability": "dft_stability",
         "metallicity": "dft_metallicity", "magnetism": "dft_magnetism"}


def load(p):
    t = re.sub(r'("verdict"\s*:\s*)(real|false_positive|unsure)\b', r'\1"\2"', open(p).read())
    return {r["case"]: r["verdict"] for r in json.loads(t)["reviews"]}


def scored_cases(fam):
    """Case numbers (1-based, review-page order) that are scored under the active stability rule."""
    if fam not in ("Stability", "stability"):
        return None
    recs = [json.loads(l) for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "halfB_dft_fired_cases.jsonl"))]
    fired = [r for r in recs if r["claim_type"] == "stability" and str(r["fired"]).lower() == "true"]
    return {i for i, r in enumerate(fired, 1) if final_oracle.keep_dft_fired(r)}


def main():
    rng = np.random.default_rng(0)
    out = {}
    print(f"{'family':<12}{'A prec':>8}{'B prec (stratified)':>26}{'agree':>8}{'kappa':>7}   A->B disagreements")
    for fam, af in FAM.items():
        A = load(os.path.join(REPO, af))
        B = load(os.path.join(HR, f"second_annotator_{fam}_review.json"))
        keep = scored_cases(fam)
        if keep is not None:
            A = {c: v for c, v in A.items() if c in keep}
            B = {c: v for c, v in B.items() if c in keep}
        strata = {"real": [c for c, v in A.items() if v == "real"], "false_positive": [c for c, v in A.items() if v == "false_positive"]}
        N = sum(len(v) for v in strata.values())
        samp = {s: [c for c in B if A.get(c) == s and B[c] in ("real", "false_positive")] for s in strata}
        rate = {s: (np.mean([B[c] == "real" for c in samp[s]]) if samp[s] else 0.0) for s in strata}
        pB = sum(len(strata[s]) / N * rate[s] for s in strata)
        # interval: draw each stratum's B-"real" rate from its Jeffreys posterior Beta(k+1/2, n-k+1/2)
        # and combine with the stratum weights (a plain resampling bootstrap has zero variance when
        # a stratum is all-agree, which understates the uncertainty of a 3- or 27-case stratum)
        boots = np.zeros(10_000)
        for s in strata:
            n_s = len(samp[s]); k_s = sum(B[c] == "real" for c in samp[s])
            if n_s:
                boots += len(strata[s]) / N * rng.beta(k_s + 0.5, n_s - k_s + 0.5, size=10_000)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        pA = len(strata["real"]) / N
        # agreement on exactly the cases scored under the active rule
        common = sorted(c for c in B if c in A)
        a_lab = [A[c] for c in common]; b_lab = [B[c] for c in common]
        agree = sum(x == y for x, y in zip(a_lab, b_lab)) / len(common)
        kappa = cohens_kappa(a_lab, b_lab) if len(set(a_lab) | set(b_lab)) > 1 else float("nan")
        dis = {f"{a}->{b}": sum(1 for c in B if A.get(c) == a and B[c] == b)
               for a in ("real", "false_positive") for b in ("real", "false_positive") if a != b}
        out[fam] = dict(precision_A=pA, precision_B_stratified=float(pB), precision_B_ci95=[float(lo), float(hi)],
                        n_audited=N, n_second=len(B), n_compared=len(common), kappa=kappa, raw_agreement=agree, disagreements=dis,
                        B_real_rate_within_A_real=float(rate["real"]), B_real_rate_within_A_fp=float(rate["false_positive"]))
        print(f"{fam:<12}{pA:>8.3f}{pB:>10.3f} [{lo:.3f}, {hi:.3f}]   {agree:>8.3f}{kappa:>7.2f}   {dis}")
    json.dump(out, open(os.path.join(HERE, "exp37_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
