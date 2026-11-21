"""
exp4_cgsv.py
=============
Experiment 4 (matpcr_runbook.txt): Constraint-Grounded Self-Verification (CGSV,
Algorithm 1 in matpcr_snjnl.tex). Measures PCR before vs. after a label-free,
oracle-driven revision loop, on the SAME items, same decoding, K rounds, and
tests the change with an exact paired McNemar test (matpcr_metrics.mcnemar_exact).

CGSV per item:
  1. Model answers once (round 0) -- this is the SAME chain/claim already used
     by Experiment 2/3 (identical prompts/builders), so "before" is directly
     comparable to prior PCR numbers, not a different setup.
  2. Oracle checks the claim. If consistent, stop (no violation to revise).
  3. If inconsistent, the model is shown a violation message -- NOT the correct
     answer (that would leak the label and make this a trivial oracle-in-the-
     loop rewrite, not a self-verification test) -- just the fact that no
     reference peak matches its stated value within tolerance, using the
     SAME wording the runbook's oracle-set V describes: "claim currently
     fails a physical-consistency check; the position does not match any
     resolvable peak. Reconsider and give a revised final answer."
  4. Model revises (multi-turn, own prior turns kept in context). Oracle
     re-checks. Repeat up to K rounds or until consistent.

Scope: XRD and spectrum ONLY. These are the two modalities where the oracle's
feedback is a genuine physical constraint the model can act on without the
message itself giving away the answer (SEM's feedback would effectively state
the scale factor; the 3 DFT claim types are single-shot classification, not
something a model can "look more carefully" at without new information --
CGSV needs a re-derivable, re-checkable continuous quantity, which XRD/
spectrum uniquely offer among the families already validated).

Run: python3 experiments/exp4_cgsv.py --n 30 --seeds 3 --k 2
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
from matpcr_metrics import xrd_peak_consistent, spectrum_peak_exists, mcnemar_exact, bootstrap_ci  # noqa: E402

import pilot  # noqa: E402
from halfB_collect import xrd_reference_peaks, spectrum_signal  # noqa: E402
from exp2_pcr_sweep import MODELS  # noqa: E402

MAX_ROUNDS_DEFAULT = 2

VIOLATION_MESSAGE = (
    "Your FINAL_ANSWER does not pass a physical-consistency check: the position you "
    "stated does not match any resolvable peak within tolerance. Look at the plot "
    "again, reconsider the peak's exact apex position, and give a revised answer. "
    "End again with a line: FINAL_ANSWER: <value> {unit_hint}"
)


def check_oracle(modality: str, item: dict, parsed: dict):
    if modality == "xrd":
        ref = xrd_reference_peaks(item["source_file"])
        if ref is None:
            return None
        return xrd_peak_consistent(parsed["value"], ref, tol_deg=0.5)
    if modality == "spectrum":
        sig = spectrum_signal(item["source_file"])
        if sig is None:
            return None
        xs, ys = sig
        return spectrum_peak_exists(parsed["value"], xs, ys, x_tol=5.0)
    return None


UNIT_HINT = {"xrd": "deg", "spectrum": "cm-1"}


# ----------------------------------------------------------------------------
# Multi-turn model runners -- pilot.py's run_local_qwen/run_api_openrouter only
# support a single-turn (image, prompt) call. CGSV's revise step needs the
# model's own prior answer kept in context, so these wrap the same underlying
# model/client with an explicit conversation history.
# ----------------------------------------------------------------------------
_LOCAL_MODEL = None
_LOCAL_PROCESSOR = None


def run_local_qwen_multiturn(image_path: str, turns: list, max_new_tokens: int = 600) -> str:
    """turns: list of {"role": "user"|"assistant", "text": ...}. Image is attached
    to the FIRST user turn only (matches how a human would re-examine the same
    plot across a conversation, not re-send it every round)."""
    global _LOCAL_MODEL, _LOCAL_PROCESSOR
    import torch
    from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
    from PIL import Image

    if _LOCAL_MODEL is None:
        model_id = "Qwen/Qwen2.5-VL-7B-Instruct"
        _LOCAL_MODEL = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_id, torch_dtype=torch.bfloat16, device_map="cuda:0"
        )
        _LOCAL_PROCESSOR = AutoProcessor.from_pretrained(model_id)

    image = Image.open(image_path).convert("RGB")
    messages = []
    first_user = True
    for turn in turns:
        if turn["role"] == "user":
            content = [{"type": "text", "text": turn["text"]}]
            if first_user:
                content.insert(0, {"type": "image"})
                first_user = False
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "assistant", "content": [{"type": "text", "text": turn["text"]}]})

    text = _LOCAL_PROCESSOR.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = _LOCAL_PROCESSOR(text=[text], images=[image], return_tensors="pt").to("cuda:0")
    out = _LOCAL_MODEL.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    result = _LOCAL_PROCESSOR.batch_decode(out[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)
    return result[0]


def run_api_openrouter_multiturn(image_path: str, turns: list, api_key: str, model: str) -> tuple:
    import base64
    import mimetypes
    import requests

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        mime_type = "image/png"

    messages = []
    first_user = True
    for turn in turns:
        if turn["role"] == "user":
            content = [{"type": "text", "text": turn["text"]}]
            if first_user:
                content.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}})
                first_user = False
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "assistant", "content": turn["text"]})

    payload = {"model": model, "messages": messages, "max_tokens": 700}
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=(10, 60),
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"], data.get("usage", {}).get("cost", None)


def call_model(model_key: str, image_path: str, turns: list, api_key: str):
    spec = MODELS[model_key]
    if spec["kind"] == "local":
        return run_local_qwen_multiturn(image_path, turns), 0.0
    return run_api_openrouter_multiturn(image_path, turns, api_key, model=spec["api_model"])


# ----------------------------------------------------------------------------
# CGSV loop (Algorithm 1): answer, check, revise up to K rounds.
# ----------------------------------------------------------------------------
def run_cgsv_item(model_key: str, modality: str, item: dict, api_key: str, k_max: int):
    turns = [{"role": "user", "text": item["prompt"]}]
    total_cost = 0.0
    before_consistent = None
    after_consistent = None
    rounds_used = 0
    claimed_values = []  # the model's stated numeric claim at each round it produced one --
    # per the audit's BL4 concern (a PCR gain could reflect the model retracting/hedging the
    # flagged claim rather than correcting the physics), this lets a downstream analysis check
    # whether a "fix" corresponds to a genuinely revised claim (a different, still-checkable
    # number) rather than a claim disappearing. In THIS benchmark's single-claim-per-item
    # design, an unparseable round already drops the whole item (see below) -- there is no
    # "claim count drops from 1 to 0 but the item survives" case to hide -- so this field is
    # the closest honest analogue: it exposes the raw claimed value trajectory for review,
    # rather than asserting a claim-count metric this benchmark's parser doesn't produce.

    for round_i in range(k_max + 1):  # round 0 = initial answer, then up to k_max revisions
        chain_text, cost = call_model(model_key, item["image_path"], turns, api_key)
        total_cost += cost or 0.0
        turns.append({"role": "assistant", "text": chain_text})

        parsed = pilot.parse_chain(chain_text)
        if parsed is None:
            return None, total_cost  # unparseable chain -- drop, same as every other experiment

        claimed_values.append(parsed["value"])

        consistent = check_oracle(modality, item, parsed)
        if consistent is None:
            return None, total_cost  # oracle couldn't evaluate (e.g. no usable reference) -- drop

        if round_i == 0:
            before_consistent = consistent
        after_consistent = consistent
        rounds_used = round_i

        if consistent:
            break  # Algorithm 1 line 4: V empty -> break
        if round_i == k_max:
            break  # residual violation after K rounds -- report as-is, no more revisions

        turns.append({"role": "user", "text": VIOLATION_MESSAGE.format(unit_hint=UNIT_HINT[modality])})

    return {
        "modality": modality,
        "model": model_key,
        "source_file": item["source_file"],
        "before_consistent": bool(before_consistent),
        "after_consistent": bool(after_consistent),
        "rounds_used": rounds_used,
        "claimed_values": claimed_values,
    }, total_cost


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30, help="items per (model, modality) cell, per seed")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--k", type=int, default=MAX_ROUNDS_DEFAULT, help="max CGSV revision rounds")
    ap.add_argument("--modalities", nargs="*", default=["xrd", "spectrum"])
    ap.add_argument("--models", nargs="*", default=list(MODELS.keys()))
    ap.add_argument("--out", default="experiments/exp4_results.jsonl")
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set.")

    total_cost = 0.0
    all_records = []
    with open(args.out, "w") as out_f:
        for modality in args.modalities:
            for model_key in args.models:
                for seed in range(args.seeds):
                    t0 = time.time()
                    items = pilot.MODALITY_BUILDERS[modality](args.n, seed=4000 + seed * 100)
                    recs = []
                    for item in items:
                        rec, cost = run_cgsv_item(model_key, modality, item, api_key, args.k)
                        total_cost += cost
                        if rec is not None:
                            recs.append(rec)
                            out_f.write(json.dumps(rec) + "\n")
                            out_f.flush()
                    all_records.extend(recs)
                    n = len(recs)
                    pcr_before = sum(1 for r in recs if r["before_consistent"]) / max(n, 1)
                    pcr_after = sum(1 for r in recs if r["after_consistent"]) / max(n, 1)
                    print(
                        f"[{modality:10s}/{model_key:6s}/seed={seed}] n={n} "
                        f"PCR_before={pcr_before:.3f} PCR_after={pcr_after:.3f} "
                        f"(cost_so_far=${total_cost:.4f}) ({time.time()-t0:.1f}s)",
                        flush=True,
                    )

    print(f"\nTotal records: {len(all_records)}")
    print(f"Total API cost: ${total_cost:.4f}")
    print(f"Written to: {args.out}")


if __name__ == "__main__":
    main()
