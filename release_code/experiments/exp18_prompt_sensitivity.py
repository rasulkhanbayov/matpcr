"""
exp18_prompt_sensitivity.py
=============================
matpcr_REDFLAGS.txt A7 ("RUN and ENTER prompt/format sensitivity: PCR under
at least two paraphrased prompt templates per constraint type, and report
whether the model ranking survives"). Unlike exp9_tolerance_sensitivity.py
(pure re-analysis of already-collected claims at different oracle
tolerances), this needs NEW model calls: the question is whether PARAPHRASING
the prompt itself -- not the oracle's tolerance -- changes which model looks
best, i.e. whether the reported model ranking is an artifact of one specific
wording.

Scope: XRD, spectrum, stability -- the same three constraint types
exp9_tolerance_sensitivity.py covers, for the same reason (SEM's prompt is
already close to a minimal restatement of the task with little room for a
genuinely different paraphrase without changing what's being asked;
metallicity/magnetism are left for a follow-up given real API budget is
being spent here, not reused data).

Two prompt VARIANTS per constraint type:
  - "original": pilot.py's / pilot_dft.py's existing prompt, verbatim.
  - "paraphrase": same task, same required FINAL_ANSWER format, different
    surface wording (different sentence structure/word choice), written
    independently rather than as a minimal edit of the original -- meant to
    probe genuine phrasing sensitivity, not just "does adding one word break
    the parser."

Models: gemini, gpt4o, claude, gpt56 (4 of the paper's API models -- the
ones with strong existing signal on these three constraint types; local
Qwen and the other 5 API models are left out to bound real API spend for a
robustness check, not a headline result).

Reports, per constraint type: each model's rate under each prompt variant,
and the pairwise RANK AGREEMENT between the two variants (same metric
exp9_tolerance_sensitivity.py uses, applied to prompt variant instead of
oracle tolerance) -- does which model "wins" survive rewording the question.

Run: python3 experiments/exp18_prompt_sensitivity.py --n 20
"""

from __future__ import annotations

import os

MATPCR_DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", "/ephemeral/matpcr")
os.environ["HF_HOME"] = os.path.join(MATPCR_DATA_ROOT, "hf_cache")

import argparse
import glob
import json
import random
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pilot  # noqa: E402
import pilot_dft  # noqa: E402
from matpcr_metrics import xrd_peak_consistent, spectrum_peak_exists, stability_claim_consistent  # noqa: E402
from halfB_collect import xrd_reference_peaks, spectrum_signal  # noqa: E402
from exp2_pcr_sweep import call_with_hard_timeout, MODELS  # noqa: E402

OPXRD_ROOT = os.path.join(REPO_ROOT, "opxrd")
RRUFF_ROOT = os.path.join(MATPCR_DATA_ROOT, "rruff", "extracted")
MP_DATA_PATH = os.path.join(MATPCR_DATA_ROOT, "mp_data", "mp_reference_batch.jsonl")

PROMPT_MODELS = ["gemini", "gpt4o", "claude", "gpt56"]

# ----------------------------------------------------------------------------
# Paraphrased prompts: independently worded, same task + same required
# FINAL_ANSWER format as pilot.py/pilot_dft.py's originals (parser reuse
# requires the format to match; the SURFACE wording of the task is what's
# deliberately varied).
# ----------------------------------------------------------------------------
XRD_PARAPHRASE = (
    "You are looking at a powder X-ray diffractogram: intensity (y-axis) plotted against "
    "2theta in degrees (x-axis). Find the tallest peak in the plot and report where its "
    "summit falls on the x-axis. Use the tick marks and gridlines as a ruler -- don't just "
    "eyeball its distance from the left edge. Report the 2theta value to one decimal place, "
    "e.g. '28.4 deg'. Briefly explain your reading, then finish with a line reading exactly: "
    "FINAL_ANSWER: <value> deg"
)

SPECTRUM_PARAPHRASE = (
    "The plot shows a Raman spectrum: intensity on the vertical axis, Raman shift in cm-1 on "
    "the horizontal axis. Locate the tallest peak and report its horizontal position (the "
    "Raman shift, in cm-1) as a number, e.g. '520 cm-1'. Briefly explain how you located it, "
    "then finish with a line reading exactly: FINAL_ANSWER: <value> cm-1"
)

STABILITY_PARAPHRASE = (
    "A material has the chemical formula {formula}. Drawing on general materials-chemistry "
    "knowledge, would this composition sit on (or essentially on) the thermodynamic convex "
    "hull -- i.e., is it a stable phase rather than one that would decompose into other "
    "phases? Answer with exactly one of two labels, STABLE or UNSTABLE (any case you'd call "
    "borderline or metastable should be labeled UNSTABLE). Keep your explanation to 2-4 "
    "sentences and commit to a judgment even under uncertainty -- do not hedge or ask for more "
    "data. Finish with exactly one line: FINAL_ANSWER: STABLE or FINAL_ANSWER: UNSTABLE"
)

PROMPT_VARIANTS = {
    "xrd": {"original": None, "paraphrase": XRD_PARAPHRASE},  # filled in per-item from pilot.py
    "spectrum": {"original": None, "paraphrase": SPECTRUM_PARAPHRASE},
    "stability": {"original": pilot_dft.PROMPTS["stability"], "paraphrase": STABILITY_PARAPHRASE},
}


def build_xrd_items(n, seed):
    items = pilot.build_xrd_items(n, seed=seed)
    for it in items:
        it["prompt_original"] = it["prompt"]
    return items


def build_spectrum_items(n, seed):
    items = pilot.build_spectrum_items(n, seed=seed)
    for it in items:
        it["prompt_original"] = it["prompt"]
    return items


def build_stability_materials(n, seed):
    with open(MP_DATA_PATH) as f:
        pool = [json.loads(line) for line in f]
    random.Random(seed).shuffle(pool)
    return pool[:n]


def call_model(model_key, kind, image_path, prompt, api_key):
    spec = MODELS[model_key]
    if kind == "image":
        if spec["kind"] == "local":
            result, err = call_with_hard_timeout(pilot.run_local_qwen, image_path, prompt)
            return (result, 0.0) if err is None else (None, 0.0)
        result, err = call_with_hard_timeout(
            pilot.run_api_openrouter, image_path, prompt, api_key, model=spec["api_model"]
        )
        if err is not None:
            return None, 0.0
        chain_text, cost = result
        return chain_text, cost or 0.0
    else:
        if spec["kind"] == "local":
            result, err = call_with_hard_timeout(pilot_dft.run_text_local_qwen, prompt)
            return (result, 0.0) if err is None else (None, 0.0)
        result, err = call_with_hard_timeout(pilot_dft.run_text_api_openrouter, prompt, api_key, model=spec["api_model"])
        if err is not None:
            return None, 0.0
        chain_text, cost = result
        return chain_text, cost or 0.0


def rank_agreement(rates_a, rates_b):
    models = sorted(set(rates_a) & set(rates_b))
    pairs = [(a, b) for i, a in enumerate(models) for b in models[i + 1:]]
    if not pairs:
        return None
    n_agree = 0
    for a, b in pairs:
        if np.sign(rates_a[a] - rates_a[b]) == np.sign(rates_b[a] - rates_b[b]):
            n_agree += 1
    return n_agree / len(pairs)


def run_xrd(n, seed, api_key, total_cost):
    items = build_xrd_items(n, seed)
    rates = {}
    for variant, alt_prompt in PROMPT_VARIANTS["xrd"].items():
        hits = {}
        for it in items:
            prompt = it["prompt_original"] if variant == "original" else alt_prompt
            for model_key in PROMPT_MODELS:
                chain_text, cost = call_model(model_key, "image", it["image_path"], prompt, api_key)
                total_cost[0] += cost
                if not isinstance(chain_text, str):
                    continue
                parsed = pilot.parse_chain(chain_text)
                if parsed is None:
                    continue
                refs = xrd_reference_peaks(it["source_file"])
                if not refs:
                    continue
                consistent = xrd_peak_consistent(parsed["value"], refs, tol_deg=0.5)
                hits.setdefault(model_key, []).append(consistent)
        rates[variant] = {m: float(np.mean(v)) for m, v in hits.items() if v}
        print(f"[xrd/{variant}] " + ", ".join(f"{m}={r:.3f}(n={len(hits[m])})" for m, r in sorted(rates[variant].items())), flush=True)
    agreement = rank_agreement(rates["original"], rates["paraphrase"])
    print(f"[xrd] rank agreement original-vs-paraphrase: {agreement}")
    return {"modality": "xrd", "rates_by_variant": rates, "rank_agreement": agreement}


def run_spectrum(n, seed, api_key, total_cost):
    items = build_spectrum_items(n, seed)
    rates = {}
    for variant, alt_prompt in PROMPT_VARIANTS["spectrum"].items():
        hits = {}
        for it in items:
            prompt = it["prompt_original"] if variant == "original" else alt_prompt
            for model_key in PROMPT_MODELS:
                chain_text, cost = call_model(model_key, "image", it["image_path"], prompt, api_key)
                total_cost[0] += cost
                if not isinstance(chain_text, str):
                    continue
                parsed = pilot.parse_chain(chain_text)
                if parsed is None:
                    continue
                sig = spectrum_signal(it["source_file"])
                if sig is None:
                    continue
                xs, ys = sig
                consistent = spectrum_peak_exists(parsed["value"], xs, ys, x_tol=5.0)
                hits.setdefault(model_key, []).append(consistent)
        rates[variant] = {m: float(np.mean(v)) for m, v in hits.items() if v}
        print(f"[spectrum/{variant}] " + ", ".join(f"{m}={r:.3f}(n={len(hits[m])})" for m, r in sorted(rates[variant].items())), flush=True)
    agreement = rank_agreement(rates["original"], rates["paraphrase"])
    print(f"[spectrum] rank agreement original-vs-paraphrase: {agreement}")
    return {"modality": "spectrum", "rates_by_variant": rates, "rank_agreement": agreement}


def run_stability(n, seed, api_key, total_cost):
    materials = build_stability_materials(n, seed)
    rates = {}
    for variant, prompt_template in PROMPT_VARIANTS["stability"].items():
        hits = {}
        for mat in materials:
            prompt = prompt_template.format(formula=mat["formula_pretty"])
            for model_key in PROMPT_MODELS:
                chain_text, cost = call_model(model_key, "text", None, prompt, api_key)
                total_cost[0] += cost
                if not isinstance(chain_text, str):
                    continue
                claimed = pilot_dft.parse_dft_chain(chain_text)
                if claimed not in ("STABLE", "UNSTABLE"):
                    continue
                consistent = stability_claim_consistent(claimed == "STABLE", mat["energy_above_hull"])
                hits.setdefault(model_key, []).append(consistent)
        rates[variant] = {m: float(np.mean(v)) for m, v in hits.items() if v}
        print(f"[stability/{variant}] " + ", ".join(f"{m}={r:.3f}(n={len(hits[m])})" for m, r in sorted(rates[variant].items())), flush=True)
    agreement = rank_agreement(rates["original"], rates["paraphrase"])
    print(f"[stability] rank agreement original-vs-paraphrase: {agreement}")
    return {"modality": "stability", "rates_by_variant": rates, "rank_agreement": agreement}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--modalities", nargs="*", default=["xrd", "spectrum", "stability"])
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp18_results.json"))
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set.")

    total_cost = [0.0]
    t0 = time.time()
    results = {}
    if "xrd" in args.modalities:
        results["xrd"] = run_xrd(args.n, args.seed, api_key, total_cost)
    if "spectrum" in args.modalities:
        results["spectrum"] = run_spectrum(args.n, args.seed, api_key, total_cost)
    if "stability" in args.modalities:
        results["stability"] = run_stability(args.n, args.seed, api_key, total_cost)

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nTotal API cost: ${total_cost[0]:.4f}")
    print(f"Elapsed: {time.time() - t0:.0f}s")
    print(f"Written to: {args.out}")


if __name__ == "__main__":
    main()
