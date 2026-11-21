"""
exp13_second_reviewer_kappa.py
=================================
REVISION_PLAN.md Phase 2, EX6 ("not executable by me alone" per the plan's
own note): Cohen's kappa for inter-rater agreement on the Half-B manual
precision review, needed because a single reviewer's precision numbers
(CLAUDE.md SS11/SS19) have no way to show whether "real violation" vs.
"false positive" is a judgment call two people would actually agree on, or
whether it depends heavily on who is looking.

WHAT THIS SCRIPT DOES NOT DO: it does not, and cannot, generate the second
reviewer's judgments -- that is real human labor by a second person, and
substituting a second LLM pass for a second HUMAN would defeat the entire
point of a human precision audit (CLAUDE.md SS8 rule 1: the oracle's
correctness claim rests on genuine human judgment, not a model grading
itself). What IS built here:
  1. The existing review pages (experiments/halfB_review_{xrd,sem,spectrum,
     dft_stability,dft_metallicity,dft_magnetism}.html) already ARE the
     second-reviewer harness -- they are static, self-contained, and any
     second person can open the same file fresh and click through
     independently, blind to the first reviewer's verdicts (the first
     reviewer's exports -- xrd.txt/sem.txt/spectrum.txt/stability.txt/
     metallicity.txt/magnetism.txt -- are plain files in the repo root, not
     baked into the HTML, so a second reviewer opening the .html sees no
     trace of the first reviewer's answers). No new UI needed.
  2. THIS script: once a second reviewer has exported their own review (same
     JSON format, same case-numbering as the original -- confirmed
     deterministic via halfB_report.py's file-order case numbering, see
     exp10_violation_taxonomy.py's docstring for the same mapping argument),
     load both exports and compute Cohen's kappa per family via
     matpcr_metrics.cohens_kappa (added this session, smoke-tested).

Per CLAUDE.md SS19, the 3 DFT review files (stability.txt/metallicity.txt/
magnetism.txt) in the repo root are STALE (pre-date the Mustafa-driven oracle
correction) -- a second review should target the NEW pages
(halfB_review_dft_{stability,metallicity,magnetism}.html, generated after
the fix) once a first reviewer has completed those, not the old stale
export files. This script accepts a --family argument and does not assume
which pairing is ready.

Run (once two export files exist):
    python3 experiments/exp13_second_reviewer_kappa.py \\
        --family xrd --reviewer_a xrd.txt --reviewer_b xrd_reviewer2.txt
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import cohens_kappa  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_review(path):
    with open(path) as f:
        raw = f.read()
    # The DFT export files (stability.txt/metallicity.txt/magnetism.txt) were
    # observed (CLAUDE.md SS9) to contain UNQUOTED verdict tokens, e.g.
    # `"verdict": real` instead of `"verdict": "real"` -- invalid strict
    # JSON. Apply the same regex pre-pass used when those were first parsed,
    # rather than assuming every export is strictly valid JSON.
    fixed = re.sub(r'"verdict":\s*(real|false_positive|unsure)\b', r'"verdict": "\1"', raw)
    d = json.loads(fixed)
    return {r["case"]: r["verdict"] for r in d["reviews"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True, choices=[
        "xrd", "sem", "spectrum", "dft_stability", "dft_metallicity", "dft_magnetism"
    ])
    ap.add_argument("--reviewer_a", required=True, help="path to reviewer A's exported review JSON")
    ap.add_argument("--reviewer_b", required=True, help="path to reviewer B's exported review JSON")
    args = ap.parse_args()

    review_a = _load_review(args.reviewer_a)
    review_b = _load_review(args.reviewer_b)

    common_cases = sorted(set(review_a) & set(review_b))
    if not common_cases:
        raise SystemExit(
            f"No overlapping case numbers between {args.reviewer_a} and {args.reviewer_b} "
            "-- both reviewers must have reviewed the SAME review page (same family, "
            "same underlying halfB_fired_cases.jsonl / halfB_dft_fired_cases.jsonl state "
            "at review time) for case numbers to line up."
        )
    if len(common_cases) < len(review_a) or len(common_cases) < len(review_b):
        print(f"WARNING: reviewer A had {len(review_a)} cases, reviewer B had {len(review_b)}, "
              f"only {len(common_cases)} overlap -- one reviewer may have reviewed a partial "
              "set or a different/stale export. Proceeding on the overlap only.")

    a_labels = [review_a[c] for c in common_cases]
    b_labels = [review_b[c] for c in common_cases]

    kappa = cohens_kappa(a_labels, b_labels)
    raw_agreement = sum(1 for x, y in zip(a_labels, b_labels) if x == y) / len(common_cases)

    disagreements = [
        {"case": c, "reviewer_a": review_a[c], "reviewer_b": review_b[c]}
        for c in common_cases if review_a[c] != review_b[c]
    ]

    print(f"Family: {args.family}")
    print(f"Cases compared: {len(common_cases)}")
    print(f"Raw agreement: {raw_agreement:.1%}")
    print(f"Cohen's kappa: {kappa:.3f}")
    print(f"Disagreements: {len(disagreements)}")
    for d in disagreements[:20]:
        print(f"  case {d['case']}: A={d['reviewer_a']!r} vs B={d['reviewer_b']!r}")

    # Standard Landis & Koch (1977) qualitative bands -- reported as a common
    # convention, not a claim that this specific threshold is the "right"
    # bar for THIS review task.
    if kappa < 0:
        band = "poor (worse than chance)"
    elif kappa < 0.20:
        band = "slight"
    elif kappa < 0.40:
        band = "fair"
    elif kappa < 0.60:
        band = "moderate"
    elif kappa < 0.80:
        band = "substantial"
    else:
        band = "almost perfect"
    print(f"Qualitative band (Landis & Koch 1977 convention): {band}")

    out = {
        "family": args.family, "n_cases": len(common_cases), "raw_agreement": raw_agreement,
        "cohens_kappa": kappa, "qualitative_band": band, "disagreements": disagreements,
    }
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"exp13_kappa_{args.family}.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWritten to: {out_path}")


if __name__ == "__main__":
    main()
