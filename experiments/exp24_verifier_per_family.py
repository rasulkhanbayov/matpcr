"""
exp24_verifier_per_family.py
============================
KBS revision R1 (Reviewer 1, minor 2): break the in-distribution (source-disjoint
80/20) verifier result down by constraint family. No retraining: the random-split
test set is reconstructed with exp5_train_verifier.make_split (deterministic,
seed 0) and aligned with the per-item probabilities stored in exp5_results.jsonl.

For each family: n, violation base rate, precision/recall/F1 at 0.5, ROC AUC with a
source-level bootstrap 95% CI (B=5000), and the AUC of a trivial
"family prior" baseline, so a per-family AUC is not mistaken for family identification.

Run: python experiments/exp24_verifier_per_family.py
Writes: experiments/exp24_results.json
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from matpcr_metrics import precision_recall_f1, roc_auc  # noqa: E402

DATASET = os.path.join(HERE, "exp5_verifier_dataset.jsonl")
RESULTS = os.path.join(HERE, "exp5_results.jsonl")


def make_split_random(records, seed=0):
    # identical to exp5_train_verifier.make_split(mode="random"); copied so this
    # script does not import torch/transformers.
    rng = np.random.default_rng(seed)
    unique_sources = sorted(set(r["source_id"] for r in records))
    rng.shuffle(unique_sources)
    test_sources = set(unique_sources[: max(1, int(0.2 * len(unique_sources)))])
    return [r for r in records if r["source_id"] in test_sources]


def main():
    records = [json.loads(l) for l in open(DATASET)]
    test = make_split_random(records)
    run = next(json.loads(l) for l in open(RESULTS) if json.loads(l)["run_name"] == "random")
    probs, labels = run["probs"], run["labels"]
    assert len(test) == len(probs), (len(test), len(probs))
    assert [r["violation"] for r in test] == labels, "label order mismatch: split reconstruction failed"
    print(f"Reconstructed random-split test set: n={len(test)} (matches stored scores and labels exactly)\n")

    fam = defaultdict(list)
    for r, p in zip(test, probs):
        fam[r["modality"]].append((r["source_id"], p, r["violation"]))

    rng = np.random.default_rng(0)
    out = {}
    print(f"{'family':<12}{'n':>5}{'viol%':>7}{'prec':>7}{'rec':>7}{'F1':>7}{'AUC':>8}  95% CI (source bootstrap)")
    for m in ["xrd", "sem", "spectrum", "stability", "metallicity", "magnetism"]:
        rows = fam[m]
        y = [v for _, _, v in rows]
        s = [p for _, p, _ in rows]
        prf = precision_recall_f1([1 if p >= 0.5 else 0 for p in s], y)
        auc = roc_auc(s, y) if 0 < sum(y) < len(y) else float("nan")
        by_src = defaultdict(list)
        for sid, p, v in rows:
            by_src[sid].append((p, v))
        srcs = list(by_src)
        boots = []
        for _ in range(5000):
            pick = rng.integers(0, len(srcs), len(srcs))
            ss, yy = [], []
            for i in pick:
                for p, v in by_src[srcs[i]]:
                    ss.append(p); yy.append(v)
            if 0 < sum(yy) < len(yy):
                boots.append(roc_auc(ss, yy))
        lo, hi = (np.percentile(boots, [2.5, 97.5]) if boots else (float("nan"),) * 2)
        out[m] = dict(n=len(rows), n_sources=len(srcs), violation_rate=float(np.mean(y)), **prf,
                      auc=float(auc), auc_ci95=[float(lo), float(hi)])
        print(f"{m:<12}{len(rows):>5}{100*np.mean(y):>6.1f}%{prf['precision']:>7.3f}{prf['recall']:>7.3f}"
              f"{prf['f1']:>7.3f}{auc:>8.3f}  [{lo:.3f}, {hi:.3f}]")

    # family-prior baseline: score = training-set violation rate of the item's family
    train_ids = {r["source_id"] for r in test}
    train = [r for r in records if r["source_id"] not in train_ids]
    prior = {m: np.mean([r["violation"] for r in train if r["modality"] == m]) for m in fam}
    prior_auc = roc_auc([prior[r["modality"]] for r in test], labels)
    print(f"\nPooled in-distribution AUC (stored scores): {roc_auc(probs, labels):.3f}; "
          f"family-prior-only baseline AUC: {prior_auc:.3f}")
    out["_pooled"] = dict(auc=float(roc_auc(probs, labels)), family_prior_auc=float(prior_auc))
    json.dump(out, open(os.path.join(HERE, "exp24_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
