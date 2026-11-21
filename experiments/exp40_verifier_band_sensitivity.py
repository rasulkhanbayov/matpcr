"""
exp40_verifier_band_sensitivity.py
==================================
KBS revision R1: the verifier was trained and evaluated on oracle labels produced under the original
stability rule. Under the final protocol, near-hull stability records (0 < E_hull <= 0.05 eV/atom)
are not scored. Without retraining, this script re-evaluates the stored per-item verifier scores on
the test items that ARE scored under the final rule, for both the reported runs (exp5_results.jsonl)
and the released adapters (exp5_results_rev_p100_fp32.jsonl):
  * in-distribution split: pooled AUC and the stability-family AUC
  * held-out stability split: AUC
with source-level / percentile bootstrap 95% intervals (B=5000, seed 0).

Run: MATPCR_DATA_ROOT=... python experiments/exp40_verifier_band_sensitivity.py
Writes: experiments/exp40_results.json
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import final_oracle  # noqa: E402
from exp24_verifier_per_family import make_split_random  # noqa: E402
from matpcr_metrics import roc_auc  # noqa: E402


def auc_ci(p, y, rng, B=5000):
    p, y = np.asarray(p), np.asarray(y)
    b = []
    for _ in range(B):
        i = rng.integers(0, len(y), len(y))
        if 0 < y[i].sum() < len(y):
            b.append(roc_auc(p[i].tolist(), y[i].tolist()))
    return roc_auc(p.tolist(), y.tolist()), np.percentile(b, [2.5, 97.5]).tolist()


def scored(r):
    return r["modality"] != "stability" or not final_oracle.in_band(final_oracle.hull()[r["source_id"]])


def main():
    records = [json.loads(l) for l in open(os.path.join(HERE, "exp5_verifier_dataset.jsonl"))]
    test_rand = make_split_random(records)
    test_stab = [r for r in records if r["modality"] == "stability"]
    out = {}
    for tag, fn in [("reported", "exp5_results.jsonl"), ("released", "exp5_results_rev_p100_fp32.jsonl")]:
        runs = {json.loads(l)["run_name"]: json.loads(l) for l in open(os.path.join(HERE, fn))}
        rng = np.random.default_rng(0)
        res = {}
        for name, test, run in [("in_distribution_pooled", test_rand, runs["random"]),
                                ("in_distribution_stability", test_rand, runs["random"]),
                                ("heldout_stability", test_stab, runs["modality_heldout_stability"])]:
            assert len(test) == len(run["probs"])
            rows = [(r, p, y) for r, p, y in zip(test, run["probs"], run["labels"])]
            if name == "in_distribution_stability":
                rows = [x for x in rows if x[0]["modality"] == "stability"]
            for rule, keep in [("original", lambda r: True), ("final", scored)]:
                sub = [x for x in rows if keep(x[0])]
                a, ci = auc_ci([x[1] for x in sub], [x[2] for x in sub], rng)
                res[f"{name}|{rule}"] = dict(n=len(sub), auc=float(a), ci95=[float(c) for c in ci])
        out[tag] = res
        print(f"== {tag}")
        for k, v in res.items():
            print(f"  {k:<36} n={v['n']:>4} AUC={v['auc']:.3f} [{v['ci95'][0]:.3f}, {v['ci95'][1]:.3f}]")
    json.dump(out, open(os.path.join(HERE, "exp40_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
