"""
exp35_released_adapter_check.py
===============================
KBS revision R1: compare the released (retrained) verifier adapters with the runs reported in the
Article. The original training script never saved adapter weights, so the 13 splits were retrained
with the corrected script (seed 0; float32 on an NVIDIA P100, which lacks bfloat16 support) and the
resulting adapters are the ones released. This script reports, for each split, the reported AUC and
the released adapters' AUC with percentile bootstrap 95% and Bonferroni-widened (six held-out
comparisons) intervals (B=5000, seed 0).

Inputs: experiments/exp5_results.jsonl (reported), experiments/exp5_results_rev_p100_fp32.jsonl (released)
Run: python experiments/exp35_released_adapter_check.py
Writes: experiments/exp35_results.json
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from matpcr_metrics import roc_auc  # noqa: E402


def boot(p, y, rng, B=5000):
    p, y = np.asarray(p), np.asarray(y)
    n, out = len(y), []
    for _ in range(B):
        i = rng.integers(0, n, n)
        if 0 < y[i].sum() < n:
            out.append(roc_auc(p[i].tolist(), y[i].tolist()))
    return out


def main():
    old = {json.loads(l)["run_name"]: json.loads(l) for l in open(os.path.join(HERE, "exp5_results.jsonl"))}
    new = [json.loads(l) for l in open(os.path.join(HERE, "exp5_results_rev_p100_fp32.jsonl"))]
    rng = np.random.default_rng(0)
    out = {}
    print(f"{'split':<30}{'reported':>9}{'released':>9}   95% CI            Bonferroni(6) CI    F1 rep->rel")
    for r in new:
        if r["run_name"].startswith("constraint"):
            continue  # identical partition to modality_heldout_* in this benchmark
        b = boot(r["probs"], r["labels"], rng)
        ci = np.percentile(b, [2.5, 97.5]).tolist()
        bci = np.percentile(b, [2.5 / 6, 100 - 2.5 / 6]).tolist()
        o = old[r["run_name"]]
        out[r["run_name"]] = dict(reported_auc=o["roc_auc"], released_auc=r["roc_auc"], released_ci95=ci,
                                  released_bonferroni6_ci=bci, reported_f1=o["f1"], released_f1=r["f1"],
                                  released_precision=r["precision"], released_recall=r["recall"], released_ece=r["ece"])
        print(f"{r['run_name']:<30}{o['roc_auc']:>9.3f}{r['roc_auc']:>9.3f}   [{ci[0]:.3f}, {ci[1]:.3f}]    "
              f"[{bci[0]:.3f}, {bci[1]:.3f}]    {o['f1']:.3f}->{r['f1']:.3f}")
    json.dump(out, open(os.path.join(HERE, "exp35_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
