"""
exp14_scaling_and_utility.py
===============================
REVISION_PLAN.md Phase 2, item 23 (lowest priority, audit EX12/EX13 -- "if
time/budget allow after 1-22"). Two independent, small analyses:

  A. DOWNSTREAM UTILITY DEMO (EX12): does the released verifier (Experiment
     5) have practical value as a best-of-N selector? Uses exp7_cgsv_
     controls.py's own "best_of_n" control records (N=3 independent
     single-turn samples per item, no verifier involved in the sampling
     itself) -- reuses that data directly, no new model calls. For each
     item with N=3 sampled answers, the verifier scores each answer's chain
     text and the LOWEST-scored (least likely to be a violation) one is
     picked; PCR of that "verifier-picked" choice is compared against (a)
     PCR of a RANDOM pick among the N (exp7's own first_consistent field
     already reports this) and (b) the ORACLE-ORACLE ceiling (exp7's
     any_consistent: best possible outcome if you always picked correctly,
     which needs the oracle itself, not obtainable at real inference time --
     an upper bound, not a fair comparison). If verifier-picked PCR sits
     meaningfully above random-pick and below the oracle ceiling, that is
     genuine evidence of practical utility as a triage/selection tool.
     REQUIRES exp7_results.jsonl to contain "best_of_n" control records --
     if exp7 has not reached that stage yet, this script says so explicitly
     and does not fabricate a result from partial data.

  B. CAPABILITY/SCALING TREND (EX13): does PCR track a rough model
     capability ordering? NO universal, comparable benchmark score exists
     for all 8 models used across this project (4 original + 4 refresh,
     spanning different providers/families) -- fabricating a continuous
     "capability score" would be exactly the kind of invented number
     CLAUDE.md's rule 2 warns against. Instead, reports PCR (from
     exp2_results.jsonl + exp2_refresh_results.jsonl, pooled) against each
     model's release family/generation as an ORDINAL, not cardinal, axis
     (e.g. "gpt4o" is an earlier generation than "gpt56"; "claude" i.e.
     Sonnet 4.5 is an earlier generation than "opus46"), and reports
     whether PCR increases, decreases, or shows no clear trend within each
     same-provider generation pair -- a much weaker but honestly-scoped
     claim than a fitted scaling curve across unrelated model families
     would be.

Run: python3 experiments/exp14_scaling_and_utility.py
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import bootstrap_ci  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP7_PATH = os.path.join(REPO_ROOT, "experiments", "exp7_results.jsonl")
EXP2_PATHS = [
    os.path.join(REPO_ROOT, "experiments", "exp2_results.jsonl"),
    os.path.join(REPO_ROOT, "experiments", "exp2_refresh_results.jsonl"),
]

# Same-provider generation pairs, ordered (earlier, later) -- the ONLY
# comparisons where "which is more capable" is uncontroversial without a
# fabricated score. Cross-provider comparisons (e.g. gpt4o vs claude) are
# deliberately NOT included -- there is no non-controversial ordering there.
GENERATION_PAIRS = [
    ("gpt4o", "gpt56", "OpenAI: GPT-4o -> GPT-5.6-Terra"),
    ("claude", "opus46", "Anthropic: Claude Sonnet 4.5 -> Claude Opus 4.6"),
    ("qwen3vl", "qwen3vl_thinking", "Qwen: Qwen3-VL-8B-Instruct -> Qwen3-VL-8B-Thinking (same generation, reasoning-mode variant)"),
]


def run_utility_demo():
    if not os.path.exists(EXP7_PATH):
        return {"status": "not_available", "reason": f"{EXP7_PATH} does not exist yet"}
    best_of_n_records = []
    with open(EXP7_PATH) as f:
        for line in f:
            d = json.loads(line)
            if d.get("control") == "best_of_n":
                best_of_n_records.append(d)
    if not best_of_n_records:
        return {"status": "not_available", "reason": "exp7_results.jsonl has no 'best_of_n' records yet "
                                                       "(exp7_cgsv_controls.py has not reached that control stage)"}

    # exp7's best_of_n records report first_consistent (random-pick proxy:
    # the first of the N samples) and any_consistent (oracle-oracle ceiling)
    # directly -- no verifier-based selection was implemented in exp7 itself
    # (it doesn't need to be scored by a verifier, that's THIS script's job
    # to add on top of the same records). Since exp7 does not persist the
    # actual N individual chain texts (only the aggregate first/any flags),
    # a genuine verifier-based reselection is not reconstructable from this
    # file alone -- reported honestly below rather than approximated.
    first_pcr = np.mean([r["first_consistent"] for r in best_of_n_records])
    any_pcr = np.mean([r["any_consistent"] for r in best_of_n_records])
    return {
        "status": "partial",
        "n_items": len(best_of_n_records),
        "random_pick_pcr": float(first_pcr),
        "oracle_ceiling_pcr": float(any_pcr),
        "verifier_picked_pcr": None,
        "limitation": (
            "exp7_cgsv_controls.py's best_of_n records store only the aggregate "
            "first_consistent/any_consistent flags, not each of the N individual chain "
            "texts -- a genuine verifier-based reselection needs per-candidate chain text "
            "to score, which was not persisted. Reporting random-pick vs. oracle-ceiling "
            "PCR (both directly available) as a partial result; a full verifier-vs-random "
            "comparison would need exp7_cgsv_controls.py extended to persist each "
            "candidate's chain_text, which was not in scope for this pass."
        ),
    }


def load_exp2_pooled():
    records = []
    for path in EXP2_PATHS:
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                records.append(json.loads(line))
    return records


def run_scaling_trend():
    records = load_exp2_pooled()
    if not records:
        return {"status": "not_available", "reason": "no exp2 result files found"}

    by_model = {}
    for r in records:
        m = r["model"]
        val = r.get("consistent")
        if val is None:
            continue
        by_model.setdefault(m, []).append(bool(val))

    model_pcr = {}
    for m, vals in by_model.items():
        if len(vals) < 5:
            continue
        pcr, lo, hi = bootstrap_ci(np.array(vals, dtype=float))
        model_pcr[m] = {"n": len(vals), "pcr": float(pcr), "ci_lo": float(lo), "ci_hi": float(hi)}

    print("Per-model pooled PCR (all modalities combined):")
    for m, d in sorted(model_pcr.items(), key=lambda kv: -kv[1]["pcr"]):
        print(f"  {m:20s} n={d['n']:5d} PCR={d['pcr']:.3f} [{d['ci_lo']:.3f},{d['ci_hi']:.3f}]")

    pair_results = []
    for earlier, later, label in GENERATION_PAIRS:
        if earlier not in model_pcr or later not in model_pcr:
            pair_results.append({"pair": label, "status": "not_available",
                                  "reason": f"missing PCR for {earlier if earlier not in model_pcr else later} "
                                            "(refresh sweep may not have finished for this model yet)"})
            continue
        e, l = model_pcr[earlier], model_pcr[later]
        # A trend is called only if the two CIs do not overlap -- otherwise
        # "no clear trend" is the honest read, not a coin-flip direction call.
        if l["ci_lo"] > e["ci_hi"]:
            direction = "increase (later generation higher, CIs do not overlap)"
        elif e["ci_lo"] > l["ci_hi"]:
            direction = "decrease (later generation LOWER, CIs do not overlap)"
        else:
            direction = "no clear trend (CIs overlap)"
        pair_results.append({
            "pair": label, "status": "available",
            "earlier": {"model": earlier, **e}, "later": {"model": later, **l},
            "direction": direction,
        })
        print(f"\n{label}:")
        print(f"  {earlier}: PCR={e['pcr']:.3f} [{e['ci_lo']:.3f},{e['ci_hi']:.3f}]")
        print(f"  {later}: PCR={l['pcr']:.3f} [{l['ci_lo']:.3f},{l['ci_hi']:.3f}]")
        print(f"  -> {direction}")

    return {"status": "ok", "per_model_pcr": model_pcr, "generation_pairs": pair_results}


def main():
    print("=" * 70)
    print("A. Downstream utility demo (best-of-N)")
    print("=" * 70)
    utility = run_utility_demo()
    print(json.dumps(utility, indent=2))

    print("\n" + "=" * 70)
    print("B. Capability/scaling trend (same-provider generation pairs only)")
    print("=" * 70)
    scaling = run_scaling_trend()

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp14_results.json")
    with open(out_path, "w") as f:
        json.dump({"utility_demo": utility, "scaling_trend": scaling}, f, indent=2)
    print(f"\nWritten to: {out_path}")


if __name__ == "__main__":
    main()
