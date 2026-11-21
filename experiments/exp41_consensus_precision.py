"""
exp41_consensus_precision.py
============================
KBS revision R1 (Reviewer 2 W3): oracle precision from adjudicated consensus labels.

Consensus label for every case of the second-annotator subsample (30 per family, stratified by the first
annotator's verdict): the shared label where the two annotators agreed, otherwise the label both
annotators agreed on when adjudicating (KBS_revision_R1/human_review/annotations/adj_<family>.txt).
Consensus precision for the whole audited population is the stratum-weighted estimate
    p_C = sum_s (N_s / N) * (share of consensus-"real" in the sampled cases of stratum s),
strata s = first annotator's verdict (real / false positive), with a 95% interval from per-stratum
Jeffreys posteriors (10,000 draws, seed 0). Only cases scored under the active stability rule are used
(final protocol: near-hull stability cases are not scored). Also reports the first annotator's
full-audit precision, and how often the adjudicated label sided with each annotator.

Run: MATPCR_DATA_ROOT=... python experiments/exp41_consensus_precision.py
Writes: experiments/exp41_results.json
"""

from __future__ import annotations

import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from exp37_two_annotator_precision import FAM, load, scored_cases  # noqa: E402

HR = os.path.join(REPO, "KBS_revision_R1", "human_review")
ADJ = {"xrd": "adj_xrd.txt", "sem": "adj_sem.txt", "spectrum": "adj_spectrum.txt",
       "magnetism": "adj_magnestism.txt"}  # file names as delivered


def load_adj(fam):
    fn = ADJ.get(fam)
    if not fn:
        return {}
    p = os.path.join(HR, "annotations", fn)
    t = re.sub(r'("verdict"\s*:\s*)(real|false_positive|unsure)\b', r'\1"\2"', open(p).read())
    return {r["case"]: r["verdict"] for r in json.loads(t)["reviews"]}


def main():
    rng = np.random.default_rng(0)
    out = {}
    print(f"{'family':<12}{'prec A (full)':>14}{'consensus':>11}  95% CI          n_sub  adjudicated  sided A/B")
    for fam, af in FAM.items():
        A = load(os.path.join(REPO, af))
        B = load(os.path.join(HR, f"second_annotator_{fam}_review.json"))
        J = load_adj(fam)
        keep = scored_cases(fam)
        if keep is not None:
            A = {c: v for c, v in A.items() if c in keep}
            B = {c: v for c, v in B.items() if c in keep}
        cons = {}
        for c in B:
            if c not in A:
                continue
            if A[c] == B[c]:
                cons[c] = A[c]
            else:
                if c not in J:
                    raise SystemExit(f"{fam}: case {c} disagrees but has no adjudicated label")
                cons[c] = J[c]
        sided = {"A": sum(1 for c in J if c in cons and A.get(c) == J[c]),
                 "B": sum(1 for c in J if c in cons and B.get(c) == J[c])}
        strata = {s: [c for c, v in A.items() if v == s] for s in ("real", "false_positive")}
        N = sum(len(v) for v in strata.values())
        samp = {s: [c for c in cons if A[c] == s and cons[c] in ("real", "false_positive")] for s in strata}
        p = sum(len(strata[s]) / N * (np.mean([cons[c] == "real" for c in samp[s]]) if samp[s] else 0.0) for s in strata)
        draws = np.zeros(10_000)
        for s in strata:
            n_s = len(samp[s]); k_s = sum(cons[c] == "real" for c in samp[s])
            if n_s:
                draws += len(strata[s]) / N * rng.beta(k_s + 0.5, n_s - k_s + 0.5, size=10_000)
        lo, hi = np.percentile(draws, [2.5, 97.5])
        pA = len(strata["real"]) / N
        out[fam] = dict(precision_A_full=pA, n_audited=N, precision_consensus=float(p),
                        precision_consensus_ci95=[float(lo), float(hi)], n_subsample=len(cons),
                        n_adjudicated=len([c for c in J if c in cons]), adjudication_sided_with=sided)
        print(f"{fam:<12}{pA:>14.3f}{p:>11.3f}  [{lo:.3f}, {hi:.3f}]   {len(cons):>4}  {out[fam]['n_adjudicated']:>10}   "
              f"{sided['A']}/{sided['B']}")
    json.dump(out, open(os.path.join(HERE, "exp41_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
