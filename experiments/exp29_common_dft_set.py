"""
exp29_common_dft_set.py
=======================
KBS revision R1 (Reviewer 2 W4; Reviewer 1 M4): evaluate ALL nine models on ONE
common, class-balanced set of materials per DFT constraint type, so model
comparisons on the DFT arms are paired (the main sweep, exp2, drew a different
30-material block per model and seed) and per-class rates have adequate n.

Design (fixed before any model call):
  * pool: the archived 3,000-material Materials Project batch (mp_reference_batch.jsonl)
  * per constraint type, 90 materials drawn with random.Random(2026):
      45 from each reference class, using the oracle's own class definitions
        stability   near-hull (E_hull <= 0.05 eV/atom)   vs  above hull
        metallicity gap <= 0.05 eV                       vs  gap >= 0.20 eV (abstention band excluded)
        magnetism   |M|/atom >= 0.05 muB                 vs  below
  * every model gets the same 270 items; prompts, parsers and oracles are exactly those
    of exp2_pcr_sweep.run_one_dft_item (pilot_dft.PROMPTS)
  * non-checkable responses are recorded (checkable=false) so coverage is measured

Run (resumable; appends):
  python experiments/exp29_common_dft_set.py --models gemini gpt4o claude opus46 gpt56 gpt56sol qwen3vl qwen3vl_thinking
  MATPCR_LOCAL_DEVICE=cpu MATPCR_LOCAL_DTYPE=float32 python experiments/exp29_common_dft_set.py --models local --local_timeout 900
Output: experiments/exp29_results.jsonl ; summary via --summarize
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import exp2_pcr_sweep as sweep  # noqa: E402

OUT = os.environ.get("EXP29_OUT", os.path.join(HERE, "exp29_results.jsonl"))
TYPES = ["stability", "metallicity", "magnetism"]
N_PER_CLASS = 45
CLASS = {
    "stability": lambda m: m["energy_above_hull"] <= 0.05,
    "metallicity": lambda m: m["band_gap"] <= 0.05,
    "magnetism": lambda m: abs(m["total_magnetization"]) / max(m["nsites"], 1) >= 0.05,
}


def build_item_sets():
    pool = [json.loads(l) for l in open(sweep.MP_DATA_PATH)]
    rng = random.Random(2026)
    sets = {}
    for t in TYPES:
        cands = [m for m in pool if not (t == "metallicity" and 0.05 < m["band_gap"] < 0.20)]
        if t == "magnetism":
            cands = [m for m in cands if m.get("nsites")]
        pos = sorted([m for m in cands if CLASS[t](m)], key=lambda m: m["material_id"])
        neg = sorted([m for m in cands if not CLASS[t](m)], key=lambda m: m["material_id"])
        chosen = rng.sample(pos, N_PER_CLASS) + rng.sample(neg, N_PER_CLASS)
        rng.shuffle(chosen)
        sets[t] = chosen
    return sets


def done_keys():
    if not os.path.exists(OUT):
        return set()
    return {(r["model"], r["modality"], r["source_id"]) for r in map(json.loads, open(OUT))}


_lock = threading.Lock()


def run_model(model, sets, api_key, total_cost):
    done = done_keys()
    for t in TYPES:
        for m in sets[t]:
            if (model, t, m["material_id"]) in done:
                continue
            r, sid, cost = sweep.run_one_dft_item(model, t, m, api_key)
            rec = {"modality": t, "model": model, "source_id": sid, "ref_class_positive": bool(CLASS[t](m)),
                   "checkable": r is not None, "consistent": (r.consistent if r is not None else None),
                   "cost_usd": cost}
            with _lock:
                total_cost[0] += cost or 0.0
                with open(OUT, "a") as f:
                    f.write(json.dumps(rec) + "\n")
        print(f"[{model}] {t} done, running cost ${total_cost[0]:.3f}", flush=True)


def summarize():
    local = os.path.join(HERE, "exp29_results_local.jsonl")
    paths = [os.path.join(HERE, "exp29_results.jsonl")] + ([local] if os.path.exists(local) else [])
    recs = [json.loads(l) for p in paths for l in open(p)]
    from collections import defaultdict
    cells = defaultdict(list)
    for r in recs:
        cells[(r["model"], r["modality"])].append(r)
    print(f"{'model':<18}{'type':<12}{'n':>4}{'chk':>5}{'PCR':>7}{'PCR+':>7}{'PCR-':>7}{'bal':>7}")
    for (m, t), rs in sorted(cells.items()):
        ch = [r for r in rs if r["checkable"]]
        pos = [r["consistent"] for r in ch if r["ref_class_positive"]]
        neg = [r["consistent"] for r in ch if not r["ref_class_positive"]]
        pcr = sum(r["consistent"] for r in ch) / len(ch) if ch else float("nan")
        pp = sum(pos) / len(pos) if pos else float("nan")
        pn = sum(neg) / len(neg) if neg else float("nan")
        print(f"{m:<18}{t:<12}{len(rs):>4}{len(ch):>5}{pcr:>7.3f}{pp:>7.3f}{pn:>7.3f}{(pp + pn) / 2:>7.3f}")
    print(f"total cost ${sum(r['cost_usd'] or 0 for r in recs):.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=[])
    ap.add_argument("--local_timeout", type=int, default=sweep.HARD_CALL_TIMEOUT_S)
    ap.add_argument("--limit", type=int, default=None, help="smoke test: items per type")
    ap.add_argument("--summarize", action="store_true")
    args = ap.parse_args()
    if args.summarize:
        summarize()
        return
    sweep.call_with_hard_timeout = functools.partial(sweep.call_with_hard_timeout.__wrapped__
                                                     if hasattr(sweep.call_with_hard_timeout, "__wrapped__")
                                                     else sweep.call_with_hard_timeout,
                                                     timeout=args.local_timeout if args.models == ["local"]
                                                     else sweep.HARD_CALL_TIMEOUT_S)
    sets = build_item_sets()
    if args.limit:
        sets = {t: v[: args.limit] for t, v in sets.items()}
    with open(os.path.join(HERE, "exp29_item_set.json"), "w") as f:
        json.dump({t: [m["material_id"] for m in v] for t, v in build_item_sets().items()}, f, indent=1)
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if any(sweep.MODELS[m]["kind"] == "api" for m in args.models) and not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set.")
    total = [0.0]
    with ThreadPoolExecutor(max_workers=len(args.models)) as ex:
        list(ex.map(lambda m: run_model(m, sets, api_key, total), args.models))
    print(f"Total cost this run: ${total[0]:.3f}")


if __name__ == "__main__":
    main()
