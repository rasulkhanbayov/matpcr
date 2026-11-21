"""
exp36_oracle_silent_summary.py
==============================
KBS revision R1 (Reviewer 1 M2): summarize the human audit of oracle-silent real responses
(pages built by exp33). For each family: the share of sampled oracle-silent responses the annotator
marked as a missed violation, with a Wilson 95% interval, and the implied recall on real responses

    recall = fired / (fired + missed),   missed = miss_rate * n_silent_population

where fired/n_silent_population are counted over the same Half-B response population the sample was
drawn from (the population whose fired cases were audited for precision). Unsure verdicts are
excluded from the rate and reported separately.

Run: python experiments/exp36_oracle_silent_summary.py --exports <dir with oracle_silent_<family>_review.json>
Writes: experiments/exp36_results.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import final_oracle  # noqa: E402  near-hull stability abstention (final protocol)
import re

HERE = os.path.dirname(os.path.abspath(__file__))
FAMILIES = ["xrd", "sem", "spectrum", "stability", "metallicity", "magnetism"]


def wilson(k, n, z=1.959964):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def truthy(x):
    return x is True or str(x).lower() == "true"


def population_counts(fam):
    if fam in ("xrd", "sem", "spectrum"):
        recs = [json.loads(l) for l in open(os.path.join(HERE, "halfB_fired_cases.jsonl"))]
        recs = [r for r in recs if r["modality"] == fam]
    else:
        recs = [json.loads(l) for l in open(os.path.join(HERE, "halfB_dft_fired_cases.jsonl"))]
        recs = [r for r in recs if r["claim_type"] == fam and final_oracle.keep_dft_fired(r)]
    fired = sum(truthy(r["fired"]) for r in recs)
    silent = sum((not truthy(r["fired"])) and truthy(r.get("oracle_consistent")) for r in recs)
    return fired, silent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exports", required=True)
    args = ap.parse_args()
    out = {}
    for fam in FAMILIES:
        fn = os.path.join(args.exports, f"oracle_silent_{fam}_review.json")
        if not os.path.exists(fn):
            print(f"{fam:<12} no export found ({fn})")
            continue
        txt = re.sub(r'("verdict"\s*:\s*)(missed_violation|clean|unsure)\b', r'\1"\2"', open(fn).read())
        rv = json.loads(txt)["reviews"]
        if fam == "stability" and final_oracle.RULE != "original":
            rv = [r for r in rv if not final_oracle.in_band(final_oracle.hull()[r["key"]])]
        v = [r["verdict"] for r in rv]
        miss, clean, uns = v.count("missed_violation"), v.count("clean"), v.count("unsure")
        n = miss + clean
        rate = miss / n if n else float("nan")
        lo, hi = wilson(miss, n)
        fired, silent = population_counts(fam)
        rec = lambda m: fired / (fired + m * silent) if fired + m * silent > 0 else float("nan")
        out[fam] = dict(n_decided=n, missed=miss, clean=clean, unsure=uns, unlabelled=v.count(None),
                        miss_rate=rate, miss_rate_ci95=[lo, hi], population_fired=fired, population_silent=silent,
                        implied_recall=rec(rate), implied_recall_ci95=[rec(hi), rec(lo)])
        print(f"{fam:<12} missed {miss}/{n} = {rate:.3f} [{lo:.3f}, {hi:.3f}]  (unsure {uns})  "
              f"implied recall {rec(rate):.3f} [{rec(hi):.3f}, {rec(lo):.3f}]")
    json.dump(out, open(os.path.join(HERE, "exp36_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
