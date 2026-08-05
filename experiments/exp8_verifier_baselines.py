"""
exp8_verifier_baselines.py
============================
REVISION_PLAN.md Phase 2, item 17 (audit EX1): baselines for the released
verifier (Experiment 5). The fine-tuned verifier's AUC numbers (0.858
in-distribution, ~0.50-0.58 held-out per CLAUDE.md SS16/19) only mean
something relative to what a simpler approach gets on the SAME items. Two
baselines, run on the identical splits exp5_train_verifier.py used (same
make_split() logic, same seed=0, same exp5_verifier_dataset.jsonl):

  1. ZERO-SHOT LLM-AS-JUDGE: no training at all -- an API model (Gemini 2.5
     Flash Lite, reused from every other experiment in this repo) is shown
     each item's input_text + chain_text and asked whether it contains a
     physical-consistency violation, with a confidence 0-100. This tests
     whether a frontier model's own physics judgment, with zero oracle
     supervision, matches or beats a small fine-tuned classifier.
  2. SELF-CONFIDENCE / LOG-PROB: uses the already-loaded local Qwen2.5-VL-7B
     to compute the token-level log-probability of the chain's own
     FINAL_ANSWER span, on the theory that a model reasoning toward a
     physically-wrong answer will (maybe) show measurably different
     token-level confidence than one reasoning toward a correct one. This is
     a genuinely free signal (no extra generation, just a forward pass) and
     a natural comparison point for "does the model know when it's wrong."

A third baseline (an off-the-shelf process reward model, PRM) was
INTENTIONALLY NOT ATTEMPTED: every widely-used open PRM (Qwen2.5-Math-PRM-7B,
PRM800K-tuned variants, MedPRM) is trained for a specific domain (math,
medicine) with step-labeled training data in that domain's own notation.
There is no general-purpose or physics/materials-science PRM publicly
available (checked directly, 2026-07-19) -- applying a math-trained PRM's
step-scorer to XRD/SEM/spectrum/DFT reasoning chains would be an
uninterpretable domain mismatch, not a meaningful baseline, so this is
reported as "not applicable" rather than forced.

Scope: runs on ALL 6 held-out-modality test splits (matching Experiment 5's
table) plus the in-distribution random split, using the SAME
exp5_verifier_dataset.jsonl and the SAME make_split() function imported
directly from exp5_train_verifier.py -- no re-implementation, no risk of a
subtly different split.

Run: python3 experiments/exp8_verifier_baselines.py --baselines judge selfconf
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

import numpy as np

# MATPCR_DATA_ROOT is host-specific -- set it in the environment before
# running on a new host; see experiments/slurm/README.md.
MATPCR_DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", "/ephemeral/matpcr")
os.environ.setdefault("HF_HOME", os.path.join(MATPCR_DATA_ROOT, "hf_cache"))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import roc_auc, precision_recall_f1, expected_calibration_error  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exp5_train_verifier import make_split  # noqa: E402
import pilot_dft  # noqa: E402

DATASET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp5_verifier_dataset.jsonl")
MODALITY_ORDER = ["xrd", "sem", "spectrum", "stability", "metallicity", "magnetism"]

JUDGE_PROMPT_TEMPLATE = """You are auditing a model's reasoning chain for PHYSICAL-CONSISTENCY violations only \
-- not whether the final answer is the objectively "best" one, but whether the chain's own stated reasoning \
and final claim are physically self-consistent given the task.

TASK CONTEXT: {input_text}

REASONING CHAIN TO AUDIT:
{chain_text}

Does this chain's final claim violate a basic physical-consistency check for this task (e.g. a claimed peak \
position that doesn't match any real feature, a claimed size inconsistent with the stated scale, a stability/\
metallicity/magnetism claim inconsistent with the reasoning's own stated numbers)? Answer using EXACTLY this \
format on the last line:
VERDICT: <VIOLATION or CONSISTENT> CONFIDENCE: <0-100>
"""

_JUDGE_RE = re.compile(r"VERDICT:\s*\**\s*(VIOLATION|CONSISTENT)\**\s*CONFIDENCE:\s*(\d+)", re.IGNORECASE)


def run_llm_judge_baseline(test_records, api_key, model="google/gemini-2.5-flash-lite", limit=None):
    records = test_records if limit is None else test_records[:limit]
    probs, labels, n_parsed, n_total, cost = [], [], 0, 0, 0.0
    for i, r in enumerate(records):
        n_total += 1
        prompt = JUDGE_PROMPT_TEMPLATE.format(input_text=r["input_text"], chain_text=r["chain_text"])
        try:
            text, call_cost = pilot_dft.run_text_api_openrouter(prompt, api_key, model=model)
        except Exception as e:
            print(f"    [judge] item {i} call failed: {e}", flush=True)
            continue
        cost += call_cost or 0.0
        m = _JUDGE_RE.search(text or "")
        if not m:
            continue
        n_parsed += 1
        verdict, conf = m.group(1).upper(), float(m.group(2))
        p_violation = (conf / 100.0) if verdict == "VIOLATION" else (1.0 - conf / 100.0)
        probs.append(p_violation)
        labels.append(int(r["violation"]))
        if (i + 1) % 20 == 0:
            print(f"    [judge] {i+1}/{len(records)} (parsed {n_parsed}, cost=${cost:.4f})", flush=True)
    return probs, labels, n_parsed, n_total, cost


_LOCAL_MODEL = None
_LOCAL_TOKENIZER = None


def _load_local_text_model():
    global _LOCAL_MODEL, _LOCAL_TOKENIZER
    if _LOCAL_MODEL is not None:
        return
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    # Qwen2.5-VL-7B's underlying language-model weights are used text-only
    # here (no image) -- valid, since self-confidence over the chain's own
    # FINAL_ANSWER tokens is a property of the text alone; the same model is
    # already used elsewhere in this repo, no new download needed.
    model_id = "Qwen/Qwen2.5-VL-7B-Instruct"
    from transformers import Qwen2_5_VLForConditionalGeneration

    _LOCAL_TOKENIZER = AutoTokenizer.from_pretrained(model_id)
    _LOCAL_MODEL = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        model_id, torch_dtype=torch.bfloat16, device_map="cuda:0"
    )
    _LOCAL_MODEL.eval()


_FINAL_ANSWER_RE = re.compile(r"FINAL[_ ]ANSWER:?\s*\**_*\s*(.+)", re.IGNORECASE)


def _final_answer_span(chain_text):
    m = _FINAL_ANSWER_RE.search(chain_text)
    if not m:
        return None
    return m.group(0)


def run_self_confidence_baseline(test_records, limit=None):
    import torch

    _load_local_text_model()
    records = test_records if limit is None else test_records[:limit]
    probs, labels = [], []
    for i, r in enumerate(records):
        span = _final_answer_span(r["chain_text"])
        if span is None:
            continue
        prefix = r["chain_text"][: r["chain_text"].find(span)]
        full_ids = _LOCAL_TOKENIZER(prefix + span, return_tensors="pt").input_ids.to("cuda:0")
        prefix_ids = _LOCAL_TOKENIZER(prefix, return_tensors="pt").input_ids.to("cuda:0")
        n_prefix = prefix_ids.shape[1]
        if full_ids.shape[1] <= n_prefix:
            continue
        with torch.no_grad():
            # Calling the full VL model with only input_ids (no pixel_values)
            # is a valid text-only forward pass -- confirmed directly: logits
            # shape and top-k next-token predictions are sane for plain text
            # (e.g. "The sky is" -> "blue" as top completion).
            out = _LOCAL_MODEL(full_ids)
            logits = out.logits[0, n_prefix - 1 : -1, :]
            target_ids = full_ids[0, n_prefix:]
            logprobs = torch.log_softmax(logits.float(), dim=-1)
            token_logprobs = logprobs[torch.arange(len(target_ids)), target_ids]
            mean_logprob = token_logprobs.mean().item()
        # Higher confidence (higher mean log-prob) -> lower predicted P(violation)
        # under the naive "the model hedges when it's wrong" hypothesis.
        # Squash is a fixed logistic on the raw mean log-prob (not tuned
        # against labels -- would leak test info). NOTE: directly checked on
        # a 40-item sample (2026-07-19) and this hypothesis is FALSE here --
        # violation chains had HIGHER mean log-prob (-2.84) than clean chains
        # (-3.99), i.e. the model is more confident, not less, when it's
        # physically wrong. Kept as the naive/expected-direction baseline
        # deliberately -- an AUC well below 0.5 IS the finding (self-reported
        # token confidence is anti-correlated with correctness here), not a
        # sign bug to "fix" by flipping the formula.
        p_violation = float(1.0 / (1.0 + np.exp(mean_logprob)))
        probs.append(p_violation)
        labels.append(int(r["violation"]))
        if (i + 1) % 50 == 0:
            print(f"    [selfconf] {i+1}/{len(records)}", flush=True)
    return probs, labels


def bootstrap_auc_ci(probs, labels, n_boot=5000, alpha=0.05, seed=0):
    rng = np.random.default_rng(seed)
    probs = np.asarray(probs, float)
    labels = np.asarray(labels, int)
    n = probs.size
    if n == 0 or len(set(labels.tolist())) < 2:
        return float("nan"), (float("nan"), float("nan"))
    aucs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        lb = labels[idx]
        if len(set(lb.tolist())) < 2:
            continue
        aucs.append(roc_auc(probs[idx], lb))
    if not aucs:
        return roc_auc(probs, labels), (float("nan"), float("nan"))
    lo, hi = np.percentile(aucs, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return roc_auc(probs, labels), (float(lo), float(hi))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baselines", nargs="*", default=["judge", "selfconf"], choices=["judge", "selfconf"])
    ap.add_argument("--splits", nargs="*", default=["random"] + [f"modality:{m}" for m in MODALITY_ORDER])
    ap.add_argument("--judge_model", default="google/gemini-2.5-flash-lite")
    ap.add_argument("--limit", type=int, default=None, help="cap test items per split (cost control)")
    ap.add_argument("--out", default="experiments/exp8_results.jsonl")
    args = ap.parse_args()

    with open(DATASET_PATH) as f:
        records = [json.loads(line) for line in f]

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if "judge" in args.baselines and not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set (needed for --baselines judge).")

    results = []
    total_cost = 0.0
    with open(args.out, "w") as out_f:
        for split_spec in args.splits:
            if split_spec == "random":
                mode, held_out = "random", None
            else:
                mode, held_out = "modality", split_spec.split(":", 1)[1]
            _, test_records = make_split(records, mode, held_out=held_out, seed=0)
            split_name = split_spec

            if "judge" in args.baselines:
                t0 = time.time()
                probs, labels, n_parsed, n_total, cost = run_llm_judge_baseline(
                    test_records, api_key, model=args.judge_model, limit=args.limit
                )
                total_cost += cost
                auc, (lo, hi) = bootstrap_auc_ci(probs, labels)
                pred = [1 if p >= 0.5 else 0 for p in probs]
                prf = precision_recall_f1(pred, labels) if labels else {"precision": float("nan"), "recall": float("nan"), "f1": float("nan")}
                ece = expected_calibration_error(probs, labels) if labels else float("nan")
                rec = {
                    "baseline": "llm_judge", "split": split_name, "n_test": len(test_records),
                    "n_parsed": n_parsed, "n_total": n_total, "auc": auc, "auc_ci_lo": lo, "auc_ci_hi": hi,
                    **prf, "ece": ece, "cost_usd": cost,
                }
                results.append(rec)
                out_f.write(json.dumps(rec) + "\n")
                out_f.flush()
                print(f"[judge/{split_name}] n_parsed={n_parsed}/{len(test_records)} AUC={auc:.3f} "
                      f"[{lo:.3f},{hi:.3f}] P={prf['precision']:.3f} R={prf['recall']:.3f} F1={prf['f1']:.3f} "
                      f"ECE={ece:.3f} cost=${cost:.4f} ({time.time()-t0:.1f}s)", flush=True)

            if "selfconf" in args.baselines:
                t0 = time.time()
                probs, labels = run_self_confidence_baseline(test_records, limit=args.limit)
                auc, (lo, hi) = bootstrap_auc_ci(probs, labels)
                pred = [1 if p >= 0.5 else 0 for p in probs]
                prf = precision_recall_f1(pred, labels) if labels else {"precision": float("nan"), "recall": float("nan"), "f1": float("nan")}
                ece = expected_calibration_error(probs, labels) if labels else float("nan")
                rec = {
                    "baseline": "self_confidence", "split": split_name, "n_test": len(test_records),
                    "n_scored": len(labels), "auc": auc, "auc_ci_lo": lo, "auc_ci_hi": hi,
                    **prf, "ece": ece,
                }
                results.append(rec)
                out_f.write(json.dumps(rec) + "\n")
                out_f.flush()
                print(f"[selfconf/{split_name}] n_scored={len(labels)}/{len(test_records)} AUC={auc:.3f} "
                      f"[{lo:.3f},{hi:.3f}] P={prf['precision']:.3f} R={prf['recall']:.3f} F1={prf['f1']:.3f} "
                      f"ECE={ece:.3f} ({time.time()-t0:.1f}s)", flush=True)

    print(f"\nTotal API cost: ${total_cost:.4f}")
    print(f"Written to: {args.out}")
    print("\nNOTE: a third baseline (off-the-shelf process reward model / PRM) was "
          "intentionally not attempted -- no general-purpose or physics/materials PRM "
          "is publicly available; every widely-used open PRM is math- or medicine-"
          "specific, and applying one to these chains would be an uninterpretable "
          "domain mismatch, not a meaningful comparison. Report this as 'not applicable' "
          "in the manuscript, not as a skipped/missing result.")


if __name__ == "__main__":
    main()
