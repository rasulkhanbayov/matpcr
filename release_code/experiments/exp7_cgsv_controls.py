"""
exp7_cgsv_controls.py
=======================
Experiment 7 (new, per the supervisor audit's EX2 "self-verification
controls"): isolates whether CGSV's PCR gain (Experiment 4/CLAUDE.md SS15) is
attributable to the ORACLE'S PHYSICAL-CONSISTENCY SIGNAL specifically, or
could be produced just as well by extra inference-time compute alone. Three
controls, same items/models/K/decoding as Experiment 4, only the revision
signal changes:

  1. UNAIDED SELF-REFINE: same multi-turn loop, model is told only "please
     double-check your answer and revise if needed" -- no oracle check, no
     physics-specific feedback, generic self-critique prompting.
  2. GENERIC RE-PROMPTING: same multi-turn loop, model is just asked the
     IDENTICAL original question again ("please reconsider and give your
     final answer again") -- tests whether merely re-asking at equal compute,
     with no critique framing at all, produces a similar gain.
  3. BEST-OF-N (N=3): no multi-turn revision at all -- sample N=3 independent
     single-turn answers per item (same prompt, same decoding), and report
     the PCR of (a) a random pick among the N and (b) an oracle-oracle upper
     bound (best of N, i.e. consistent if ANY of the N answers is consistent)
     as a ceiling reference -- NOT a fair comparison to CGSV since this uses
     3x the model calls with no verifier-based selection, but establishes
     whether sheer resampling alone can match CGSV's effect size.

If CGSV's real oracle-grounded revision (Experiment 4) outperforms all three
controls at equal or lower compute, that supports attributing the gain to
the physical-consistency signal specifically, not to generic
self-reflection or resampling. Scope: XRD and spectrum only, matching
Experiment 4 (the same two modalities where a genuine continuous quantity is
re-derivable).

Run: python3 experiments/exp7_cgsv_controls.py --n 30 --seeds 3 --k 2
"""

from __future__ import annotations

import os

# MATPCR_DATA_ROOT is host-specific -- set it in the environment before
# running on a new host; see experiments/slurm/README.md.
MATPCR_DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", "/ephemeral/matpcr")
os.environ["HF_HOME"] = os.path.join(MATPCR_DATA_ROOT, "hf_cache")

import argparse
import json
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import mcnemar_exact  # noqa: E402

import pilot  # noqa: E402
from exp2_pcr_sweep import MODELS  # noqa: E402
from exp4_cgsv import (  # noqa: E402
    check_oracle,
    call_model,
    MAX_ROUNDS_DEFAULT,
)

SELF_REFINE_MESSAGE = (
    "Please double-check your answer above. If you think it could be more accurate, "
    "revise it; otherwise restate it. End again with a line: FINAL_ANSWER: <value> {unit_hint}"
)

RE_PROMPT_MESSAGE = "{original_prompt}"  # literally the same question again, no critique framing

UNIT_HINT = {"xrd": "deg", "spectrum": "cm-1"}


def run_control_item(control: str, model_key: str, modality: str, item: dict, api_key: str, k_max: int):
    """Mirrors exp4_cgsv.run_cgsv_item's structure exactly, except the
    feedback message differs by control condition and never mentions the
    oracle's verdict."""
    turns = [{"role": "user", "text": item["prompt"]}]
    total_cost = 0.0
    before_consistent = None
    after_consistent = None
    rounds_used = 0

    for round_i in range(k_max + 1):
        chain_text, cost = call_model(model_key, item["image_path"], turns, api_key)
        total_cost += cost or 0.0
        turns.append({"role": "assistant", "text": chain_text})

        parsed = pilot.parse_chain(chain_text)
        if parsed is None:
            return None, total_cost

        consistent = check_oracle(modality, item, parsed)
        if consistent is None:
            return None, total_cost

        if round_i == 0:
            before_consistent = consistent
        after_consistent = consistent
        rounds_used = round_i

        # Unlike exp4_cgsv, we do NOT break early on "consistent" for the
        # generic-reprompting / self-refine controls -- CGSV breaks early
        # specifically because the ORACLE says there's nothing left to fix;
        # these controls have no oracle, so a fair equal-compute comparison
        # always runs the full K+1 rounds. (Breaking early here would just
        # copy CGSV's compute savings without copying its signal, which
        # confounds the comparison the other way.)
        if round_i == k_max:
            break

        if control == "self_refine":
            turns.append({"role": "user", "text": SELF_REFINE_MESSAGE.format(unit_hint=UNIT_HINT[modality])})
        elif control == "re_prompt":
            turns.append({"role": "user", "text": RE_PROMPT_MESSAGE.format(original_prompt=item["prompt"])})
        else:
            raise ValueError(control)

    return {
        "control": control,
        "modality": modality,
        "model": model_key,
        "source_file": item["source_file"],
        "before_consistent": bool(before_consistent),
        "after_consistent": bool(after_consistent),
        "rounds_used": rounds_used,
    }, total_cost


def run_best_of_n_item(model_key: str, modality: str, item: dict, api_key: str, n: int):
    """No multi-turn revision. Sample n independent single-turn answers.
    Report (a) the first answer (equivalent to "before", single sample) and
    (b) whether ANY of the n answers is consistent (an upper-bound
    reference, not a real selection strategy -- flagged as such in the
    aggregation, not presented as equivalent to CGSV)."""
    total_cost = 0.0
    results = []
    for _ in range(n):
        chain_text, cost = call_model(model_key, item["image_path"], [{"role": "user", "text": item["prompt"]}], api_key)
        total_cost += cost or 0.0
        parsed = pilot.parse_chain(chain_text)
        if parsed is None:
            results.append(None)
            continue
        consistent = check_oracle(modality, item, parsed)
        results.append(consistent)

    valid = [r for r in results if r is not None]
    if not valid:
        return None, total_cost

    return {
        "control": "best_of_n",
        "modality": modality,
        "model": model_key,
        "source_file": item["source_file"],
        "first_consistent": bool(valid[0]),
        "any_consistent": bool(any(valid)),
        "n_valid": len(valid),
    }, total_cost


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--k", type=int, default=MAX_ROUNDS_DEFAULT)
    ap.add_argument("--best_of_n", type=int, default=3)
    ap.add_argument("--modalities", nargs="*", default=["xrd", "spectrum"])
    ap.add_argument("--models", nargs="*", default=list(MODELS.keys()))
    ap.add_argument("--controls", nargs="*", default=["self_refine", "re_prompt", "best_of_n"])
    ap.add_argument("--out", default="experiments/exp7_results.jsonl")
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set.")

    total_cost = 0.0
    all_records = []
    with open(args.out, "w") as out_f:
        for control in args.controls:
            for modality in args.modalities:
                for model_key in args.models:
                    for seed in range(args.seeds):
                        t0 = time.time()
                        items = pilot.MODALITY_BUILDERS[modality](args.n, seed=5000 + seed * 100)
                        recs = []
                        for item in items:
                            if control == "best_of_n":
                                rec, cost = run_best_of_n_item(model_key, modality, item, api_key, args.best_of_n)
                            else:
                                rec, cost = run_control_item(control, model_key, modality, item, api_key, args.k)
                            total_cost += cost
                            if rec is not None:
                                recs.append(rec)
                                out_f.write(json.dumps(rec) + "\n")
                                out_f.flush()
                        all_records.extend(recs)
                        n = len(recs)
                        if control == "best_of_n":
                            first = sum(1 for r in recs if r["first_consistent"]) / max(n, 1)
                            anyc = sum(1 for r in recs if r["any_consistent"]) / max(n, 1)
                            print(
                                f"[{control}/{modality:8s}/{model_key:6s}/seed={seed}] n={n} "
                                f"PCR_first={first:.3f} PCR_any_of_{args.best_of_n}={anyc:.3f} "
                                f"(cost_so_far=${total_cost:.4f}) ({time.time()-t0:.1f}s)",
                                flush=True,
                            )
                        else:
                            pcr_before = sum(1 for r in recs if r["before_consistent"]) / max(n, 1)
                            pcr_after = sum(1 for r in recs if r["after_consistent"]) / max(n, 1)
                            print(
                                f"[{control}/{modality:8s}/{model_key:6s}/seed={seed}] n={n} "
                                f"PCR_before={pcr_before:.3f} PCR_after={pcr_after:.3f} "
                                f"(cost_so_far=${total_cost:.4f}) ({time.time()-t0:.1f}s)",
                                flush=True,
                            )

    print(f"\nTotal records: {len(all_records)}")
    print(f"Total API cost: ${total_cost:.4f}")
    print(f"Written to: {args.out}")


if __name__ == "__main__":
    main()
