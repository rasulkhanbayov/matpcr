"""
exp2_pcr_sweep.py
==================
Experiment 2 (matpcr_runbook.txt): the main PCR sweep. Fills the paper's
Table 1: Physical-Consistency Rate (PCR) and per-constraint violation rate
rho_t, for every (model, modality) cell, with bootstrap 95% CIs and S seeds.

Reuses the exact same real data sources, item builders, prompts, and oracle
functions already validated in Experiment 1 (pilot.py / pilot_dft.py /
halfB_collect.py / halfB_collect_dft.py) -- Experiment 2 does NOT redefine
any of that; it just runs more items through more models and aggregates with
matpcr_metrics.physical_consistency_rate + bootstrap_ci.

Models (per the runbook's "one local + 2-3 frontier API" spec):
  - local:  Qwen2.5-VL-7B-Instruct (image modalities) -- no text variant
            needed here since pilot_dft.py's run_text_local_qwen covers DFT.
  - gemini: google/gemini-2.5-flash-lite (cheap, already used throughout)
  - gpt4o:  openai/gpt-4o (frontier)
  - claude: anthropic/claude-sonnet-4.5 (frontier)

Modalities: xrd, sem, spectrum (image/VLM) + stability, metallicity,
magnetism (text/LLM) -- all 6 oracle families from Experiment 1.

IMPORTANT: DFT-grounded modality numbers inherit the same caveat as
Experiment 1 -- Materials Project reference values are NOT YET
independently validated by the domain co-author (Mustafa). Report DFT PCR
numbers as provisional in any manuscript text, per CLAUDE.md's OVERRIDE note.

Run: python3 experiments/exp2_pcr_sweep.py --n 30 --seeds 3
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
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import (  # noqa: E402
    ItemResult,
    physical_consistency_rate,
    violation_rate_by_type,
    bootstrap_ci,
)

import pilot  # noqa: E402
import pilot_dft  # noqa: E402

# INCIDENT (2026-07-10): a real run hung for >1hr on a single OpenRouter API
# call. First diagnosis was that urllib.request.urlopen(timeout=60)'s
# socket-level timeout wasn't bounding a stalled response-body read
# (confirmed via `ss -tnp`: CLOSE-WAIT with unread bytes). Tried a daemon
# thread + join(timeout) backstop here -- that did NOT fix it either: the
# underlying blocking call doesn't respond to a thread join, so the run
# stalled again with 84 leaked daemon threads all stuck on the same kind of
# hung read. The REAL fix was in pilot.py/pilot_dft.py: switched from urllib
# to `requests` with an explicit (connect, read) timeout tuple, which
# enforces the read timeout per socket .recv() call and actually aborts a
# stalled read. This thread wrapper is kept as a secondary backstop only --
# with the requests fix in place it should never need to fire.
HARD_CALL_TIMEOUT_S = 90


def call_with_hard_timeout(fn, *args, timeout=HARD_CALL_TIMEOUT_S, **kwargs):
    result = {}

    def target():
        try:
            result["value"] = fn(*args, **kwargs)
        except Exception as e:
            result["error"] = e

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return None, TimeoutError(f"{fn.__name__} exceeded {timeout}s hard timeout")
    if "error" in result:
        return None, result["error"]
    return result.get("value"), None
from halfB_collect import xrd_reference_peaks, sem_scale_bar, spectrum_signal, UNIT_TO_NM  # noqa: E402
from halfB_collect_dft import check_oracle as check_dft_oracle  # noqa: E402
from matpcr_metrics import xrd_peak_consistent, sem_feature_size_consistent, spectrum_peak_exists  # noqa: E402

IMAGE_MODALITIES = ["xrd", "sem", "spectrum"]
DFT_CLAIM_TYPES = ["stability", "metallicity", "magnetism"]
ALL_MODALITIES = IMAGE_MODALITIES + DFT_CLAIM_TYPES

MODELS = {
    "local": {"kind": "local", "api_model": None},
    "gemini": {"kind": "api", "api_model": "google/gemini-2.5-flash-lite"},
    "gpt4o": {"kind": "api", "api_model": "openai/gpt-4o"},
    "claude": {"kind": "api", "api_model": "anthropic/claude-sonnet-4.5"},
    # Current-generation refresh (added 2026-07-17 per the supervisor audit's EX3/EX4:
    # the original 4-model set was flagged as 1-2 generations stale). All 4 confirmed
    # vision-capable and reachable on the existing OpenRouter key. qwen3vl_thinking is
    # the reasoning-mode condition (EX4: does explicit reasoning improve consistency),
    # run via the API rather than loaded locally like the original Qwen2.5-VL-7B, since
    # this is a different model family/weights, not a drop-in local-inference swap.
    "opus46": {"kind": "api", "api_model": "anthropic/claude-opus-4.6"},
    "gpt56": {"kind": "api", "api_model": "openai/gpt-5.6-terra"},
    "qwen3vl": {"kind": "api", "api_model": "qwen/qwen3-vl-8b-instruct"},
    "qwen3vl_thinking": {"kind": "api", "api_model": "qwen/qwen3-vl-8b-thinking"},
    # Flagship-tier addition (matpcr_REDFLAGS.txt A5, 2026-08-06): GPT-5.6-Terra
    # above is OpenAI's balanced tier, not flagship -- gpt56sol is the sibling
    # flagship tier the red-flag file named explicitly, added to test whether
    # flagship capability beats balanced within the same generation/family.
    "gpt56sol": {"kind": "api", "api_model": "openai/gpt-5.6-sol"},
}

REFRESH_MODELS = ["opus46", "gpt56", "qwen3vl", "qwen3vl_thinking"]
FLAGSHIP_ADDENDUM_MODELS = ["gpt56sol"]

MP_DATA_PATH = os.path.join(MATPCR_DATA_ROOT, "mp_data", "mp_reference_batch.jsonl")


def check_image_oracle(modality: str, item: dict, parsed: dict):
    """Return True/False/None, mirroring halfB_collect.py's check_oracle."""
    if modality == "xrd":
        ref = xrd_reference_peaks(item["source_file"])
        if ref is None:
            return None
        return xrd_peak_consistent(parsed["value"], ref, tol_deg=0.5)
    if modality == "sem":
        bar = sem_scale_bar(item["source_file"])
        if bar is None or bar.get("status") != "ok":
            return None
        unit = parsed["unit"]
        mult = UNIT_TO_NM.get(unit)
        if mult is None:
            return None
        claimed_nm = parsed["value"] * mult
        long_edge = max(bar["image_w"], bar["image_h"])
        return sem_feature_size_consistent(claimed_nm, bar["scale_nm"], bar["marker_px"], long_edge)
    if modality == "spectrum":
        sig = spectrum_signal(item["source_file"])
        if sig is None:
            return None
        xs, ys = sig
        return spectrum_peak_exists(parsed["value"], xs, ys, x_tol=5.0)
    return None


def run_one_image_item(model_key: str, modality: str, item: dict, api_key: str):
    spec = MODELS[model_key]
    if spec["kind"] == "local":
        result, err = call_with_hard_timeout(pilot.run_local_qwen, item["image_path"], item["prompt"])
        if err is not None:
            print(f"  [WARN] local call failed/timed out: {err}")
            return None, item["source_file"], 0.0
        chain_text = result
        cost = 0.0
    else:
        result, err = call_with_hard_timeout(
            pilot.run_api_openrouter, item["image_path"], item["prompt"], api_key, model=spec["api_model"]
        )
        if err is not None:
            print(f"  [WARN] {model_key} call failed/timed out: {err}")
            return None, item["source_file"], 0.0
        chain_text, cost = result
        cost = cost or 0.0
    if not isinstance(chain_text, str):
        print(f"  [WARN] {model_key}/{modality}: non-string chain_text ({type(chain_text)}), dropping item")
        return None, item["source_file"], cost
    parsed = pilot.parse_chain(chain_text)
    if parsed is None:
        return None, item["source_file"], cost
    consistent = check_image_oracle(modality, item, parsed)
    if consistent is None:
        return None, item["source_file"], cost
    return ItemResult(consistent=bool(consistent), n_checks=1, n_violations=0 if consistent else 1, constraint_type=modality), item["source_file"], cost


def run_one_dft_item(model_key: str, claim_type: str, material: dict, api_key: str):
    spec = MODELS[model_key]
    prompt = pilot_dft.PROMPTS[claim_type].format(formula=material["formula_pretty"])
    if spec["kind"] == "local":
        result, err = call_with_hard_timeout(pilot_dft.run_text_local_qwen, prompt)
        if err is not None:
            print(f"  [WARN] local call failed/timed out: {err}")
            return None, material["material_id"], 0.0
        chain_text = result
        cost = 0.0
    else:
        result, err = call_with_hard_timeout(pilot_dft.run_text_api_openrouter, prompt, api_key, model=spec["api_model"])
        if err is not None:
            print(f"  [WARN] {model_key} call failed/timed out: {err}")
            return None, material["material_id"], 0.0
        chain_text, cost = result
        cost = cost or 0.0

    if not isinstance(chain_text, str):
        # Defensive guard: a transient API/threading interaction was observed
        # once during Phase 2 model-refresh smoke testing to yield a non-str
        # chain_text with err=None (not reproduced on direct retries -- flagged
        # as a rare, unexplained flake, not a deterministic bug). Drop the item
        # rather than crash a multi-hour unattended sweep on one flaky call.
        print(f"  [WARN] {model_key}/{claim_type}: non-string chain_text ({type(chain_text)}), dropping item")
        return None, material["material_id"], cost

    if claim_type == "magnetism":
        # parse_magnetism_chain returns (classification, magnitude) --
        # check_dft_oracle (== halfB_collect_dft.check_oracle) now expects
        # exactly this tuple for magnetism, matching the corrected
        # classify-then-magnitude oracle's needs.
        classification, magnitude = pilot_dft.parse_magnetism_chain(chain_text)
        if classification is None:
            return None, material["material_id"], cost
        parsed = (classification, magnitude)
    else:
        parsed = pilot_dft.parse_dft_chain(chain_text)
        if parsed is None:
            return None, material["material_id"], cost

    consistent = check_dft_oracle(claim_type, parsed, material)
    if consistent is None:
        return None, material["material_id"], cost
    return (
        ItemResult(consistent=bool(consistent), n_checks=1, n_violations=0 if consistent else 1, constraint_type=claim_type),
        material["material_id"],
        cost,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30, help="items per (model, modality) cell, per seed")
    ap.add_argument("--seeds", type=int, default=3, help="number of seeds S")
    ap.add_argument("--modalities", nargs="*", default=ALL_MODALITIES)
    ap.add_argument("--models", nargs="*", default=list(MODELS.keys()))
    ap.add_argument("--out", default="experiments/exp2_results.jsonl")
    ap.add_argument(
        "--resume", action="store_true",
        help="skip (modality, model, seed) cells already present in --out and APPEND new results "
             "instead of overwriting. Added after a real run had to be killed mid-sweep (a Claude "
             "image-MIME-type bug) with 21 of 24 image-modality cells already correctly completed "
             "-- restarting from scratch would have re-spent real API budget for no reason.",
    )
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set.")

    completed_cells = set()
    if args.resume and os.path.exists(args.out):
        # A cell only counts as "done" if it reached a real majority of its
        # target n_items, not just "any record exists" -- a cell that failed
        # after 2/30 items (like the Claude+SEM 400-error cells) should NOT
        # be treated as complete and must be re-run.
        from collections import Counter
        with open(args.out) as f:
            cell_counts = Counter((r["modality"], r["model"], r["seed"]) for r in (json.loads(line) for line in f))
        completed_cells = {cell for cell, count in cell_counts.items() if count >= args.n * 0.5}
        print(f"Resuming: {len(completed_cells)} cells already have >=50% of n_items, will skip them.")

    # Only load Materials Project data if a DFT-grounded modality was
    # actually requested -- previously this was unconditional, so a
    # geometric-only run (e.g. --modalities xrd sem spectrum) crashed with
    # FileNotFoundError even though it never touches materials_pool at all
    # (confirmed as a real bug on Panther, 2026-08-05, running Tier 1 work
    # before an MP_API_KEY was available).
    materials_pool = []
    if any(m in DFT_CLAIM_TYPES for m in args.modalities):
        with open(MP_DATA_PATH) as f:
            materials_pool = [json.loads(line) for line in f]

        # The raw file is NOT randomly ordered -- confirmed directly: the first
        # ~20 rows skew heavily toward small energy_above_hull values (0.0006 to
        # 0.12), which produced a degenerate all-UNSTABLE-claim dry run that
        # looked like a bug but was actually a sampling bias. Shuffle once with a
        # fixed seed so cursor-based, without-replacement draws across
        # modalities/seeds are representative of the full 3000-material range.
        import random as _random
        _random.Random(42).shuffle(materials_pool)

    total_cost = 0.0
    all_records = []
    mp_cursor = 0  # walk materials without replacement across DFT seeds/modalities

    out_mode = "a" if args.resume else "w"
    with open(args.out, out_mode) as out_f:
        for modality in args.modalities:
            for model_key in args.models:
                for seed in range(args.seeds):
                    if modality not in IMAGE_MODALITIES:
                        # advance the cursor even for a skipped cell so a later,
                        # non-skipped DFT cell still gets fresh, non-overlapping
                        # materials -- otherwise resuming would re-use the same
                        # rows a completed earlier cell already consumed.
                        cell_materials = materials_pool[mp_cursor : mp_cursor + args.n]
                        mp_cursor += args.n

                    if (modality, model_key, seed) in completed_cells:
                        print(f"  [skip] {modality}/{model_key}/seed={seed} already complete", flush=True)
                        continue

                    items_for_seed = []
                    if modality in IMAGE_MODALITIES:
                        items_for_seed = pilot.MODALITY_BUILDERS[modality](args.n, seed=2000 + seed * 100)
                    else:
                        items_for_seed = cell_materials

                    results = []
                    for item_idx, entity in enumerate(items_for_seed):
                        t_item_start = time.time()
                        if modality in IMAGE_MODALITIES:
                            r, source_id, cost = run_one_image_item(model_key, modality, entity, api_key)
                        else:
                            r, source_id, cost = run_one_dft_item(model_key, modality, entity, api_key)
                        total_cost += cost
                        if r is not None:
                            results.append(r)
                            all_records.append(
                                {
                                    "modality": modality,
                                    "model": model_key,
                                    "seed": seed,
                                    "source_id": source_id,
                                    "consistent": r.consistent,
                                    "cost_usd": cost,
                                }
                            )
                            out_f.write(json.dumps(all_records[-1]) + "\n")
                            out_f.flush()
                        # Per-item heartbeat: a stalled/hung call (confirmed to happen
                        # despite in-library timeouts -- see call_with_hard_timeout's
                        # docstring) is visible immediately here, not just when a full
                        # 30-item cell finishes minutes/hours later.
                        print(
                            f"    item {item_idx + 1}/{len(items_for_seed)} "
                            f"({time.time() - t_item_start:.1f}s) checkable={r is not None}",
                            flush=True,
                        )

                    pcr = physical_consistency_rate(results) if results else float("nan")
                    print(
                        f"[{modality:12s}/{model_key:6s}/seed={seed}] n_items={len(items_for_seed)} "
                        f"n_checkable={len(results)} PCR={pcr:.4f} cost_so_far=${total_cost:.4f}",
                        flush=True,
                    )

    print(f"\nTotal cost: ${total_cost:.4f}", flush=True)
    print(f"Raw records written to: {args.out}", flush=True)


if __name__ == "__main__":
    main()
