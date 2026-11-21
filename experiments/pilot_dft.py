"""
pilot_dft.py
============
PILOT check for the DFT-grounded modality (never piloted before this --
CLAUDE.md explicitly noted this was blocked pending Materials Project data,
which is now in hand). Confirms a model can expose a checkable claim for
each of the 3 DFT-grounded oracles from a chemical formula alone (text/LLM
input, not image -- matches the manuscript's "structure or text (LLM) input"
category, distinct from the image-based XRD/SEM/spectrum pilot).

Three claim types, one prompt each, real Materials Project formulas:
  - Stability:   is this composition thermodynamically stable (on the hull)?
  - Metallicity: is this composition metallic (zero band gap) or not?
  - Magnetism:   does this composition have zero or nonzero net magnetization?

This is a PILOT -- confirms parseable claims come out, does NOT compare
against the real MP reference yet (that's halfB_collect_dft.py's job).

Run: python3 experiments/pilot_dft.py --n 15
"""

from __future__ import annotations

import os

# MATPCR_DATA_ROOT is host-specific -- set it in the environment before
# running on a new host; see experiments/slurm/README.md.
MATPCR_DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", "/ephemeral/matpcr")
os.environ["HF_HOME"] = os.path.join(MATPCR_DATA_ROOT, "hf_cache")

import argparse
import json
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pilot  # noqa: E402  reuse run_local_qwen / run_api_openrouter

MP_DATA_PATH = os.path.join(MATPCR_DATA_ROOT, "mp_data", "mp_reference_batch.jsonl")

PROMPTS = {
    "stability": (
        "Consider the material with chemical composition {formula}. Based on your knowledge "
        "of materials chemistry, do you expect this composition to be THERMODYNAMICALLY STABLE "
        "(i.e., on or very close to the convex hull of stable phases for this chemical system)? "
        "You MUST choose exactly one of two options -- STABLE or UNSTABLE (treat any borderline "
        "or metastable case as UNSTABLE, since it is not clearly on the hull). Keep your reasoning "
        "SHORT (2-4 sentences) -- give your best judgment even if you are uncertain, do not "
        "extensively hedge or discuss what data would be needed. End with EXACTLY one line: "
        "FINAL_ANSWER: STABLE or FINAL_ANSWER: UNSTABLE"
    ),
    "metallicity": (
        "Consider the material with chemical composition {formula}. Based on your knowledge of "
        "materials chemistry, do you expect this composition to be METALLIC (zero or near-zero "
        "electronic band gap) or a SEMICONDUCTOR/INSULATOR (finite band gap)? Give brief "
        "reasoning, then end with EXACTLY one line: "
        "FINAL_ANSWER: METALLIC or FINAL_ANSWER: NONMETALLIC"
    ),
    "magnetism": (
        "Consider the material with chemical composition {formula}. Based on your knowledge of "
        "materials chemistry, do you expect this composition to have a NONZERO net magnetic "
        "moment (i.e. be magnetic) or ZERO net magnetization (non-magnetic)? If you judge it "
        "MAGNETIC, also give your best estimate of the magnitude of the total magnetization "
        "per atom, in Bohr magnetons per atom (a rough order-of-magnitude guess is fine -- "
        "state only the MAGNITUDE, never a sign, since the sign of a computed magnetic moment "
        "is an arbitrary choice of axis, not a physical property to guess). Keep your reasoning "
        "SHORT (2-4 sentences) -- give your best judgment even for chemically ambiguous cases "
        "(e.g. a rare-earth/lanthanide element next to a transition metal), do not extensively "
        "hedge or discuss what data would be needed. Give brief "
        "reasoning, then end with EXACTLY one line in one of these two formats: "
        "FINAL_ANSWER: NONMAGNETIC  or  FINAL_ANSWER: MAGNETIC, <value> muB/atom "
        "(e.g. 'FINAL_ANSWER: MAGNETIC, 1.5 muB/atom')"
    ),
}

ANSWER_RE = re.compile(
    r"FINAL[_ ]ANSWER[:\*]*\s*[\*_]*\s*(STABLE|UNSTABLE|METALLIC|NONMETALLIC|NONMAGNETIC)",
    re.IGNORECASE,
)

# Magnetism gets its own regex: MAGNETIC is always followed by a magnitude claim
# (tolerant of "muB/atom", "mu_B/atom", "\mu_B" LaTeX, missing "/atom", a bare
# number). NONMAGNETIC has no magnitude and is matched by the generic ANSWER_RE
# above (there is nothing to estimate for a claimed-zero moment).
MAGNETIC_RE = re.compile(
    r"FINAL[_ ]ANSWER[:\*]*\s*[\*_]*\s*MAGNETIC\s*,?\s*([\d.]+)",
    re.IGNORECASE,
)


def parse_dft_chain(text: str):
    # Tolerant of markdown bold around the answer (e.g. "**Final Answer:**
    # UNSTABLE" or "Final Answer: **UNSTABLE**") -- confirmed directly as a
    # real model output pattern in the DFT pilot; a plain "FINAL_ANSWER:\s*"
    # regex missed these because "*" is not whitespace.
    #
    # Magnetism is checked FIRST: a MAGNETIC answer carries a magnitude
    # ("FINAL_ANSWER: MAGNETIC, 1.5 muB/atom") that the generic ANSWER_RE
    # below does not match (it only recognizes bare classification words,
    # MAGNETIC deliberately excluded from it -- see module top). Returning a
    # bare "MAGNETIC" string here for backward compatibility with existing
    # stability/metallicity callers that expect parse_dft_chain to return a
    # plain label; use parse_magnetism_chain for the classification+magnitude
    # pair that the corrected oracle actually needs.
    mm = MAGNETIC_RE.search(text)
    if mm:
        return "MAGNETIC"
    m = ANSWER_RE.search(text)
    if not m:
        return None
    return m.group(1).upper()


def parse_magnetism_chain(text: str):
    """Magnetism-specific parse: returns (classification, magnitude_or_None).
    classification is "MAGNETIC"/"NONMAGNETIC"/None (unparseable).
    magnitude is the claimed |magnetization| in muB/atom for a MAGNETIC
    classification (None if the chain claimed MAGNETIC but gave no parseable
    number -- treated as a classification-only claim, matching
    magnetism_magnitude_consistent's claimed_magnitude=None path), or always
    None for NONMAGNETIC (nothing to estimate for a claimed-zero moment).
    """
    mm = MAGNETIC_RE.search(text)
    if mm:
        return "MAGNETIC", float(mm.group(1))
    m = ANSWER_RE.search(text)
    if m and m.group(1).upper() == "NONMAGNETIC":
        return "NONMAGNETIC", None
    if re.search(r"FINAL[_ ]ANSWER[:\*]*\s*[\*_]*\s*MAGNETIC\b", text, re.IGNORECASE):
        return "MAGNETIC", None  # claimed MAGNETIC but no parseable magnitude
    return None, None


def run_text_local_qwen(prompt: str, max_new_tokens: int = 700) -> str:
    """Text-only variant of pilot.run_local_qwen (no image input needed for
    this modality)."""
    import torch
    from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor

    if pilot._LOCAL_MODEL is None:
        model_id = "Qwen/Qwen2.5-VL-7B-Instruct"
        # MATPCR_LOCAL_DEVICE / MATPCR_LOCAL_DTYPE override the original A100 setting
        # (cuda:0, bfloat16), e.g. to run on CPU in float32 where no bf16-capable GPU exists.
        pilot._LOCAL_MODEL = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_id, torch_dtype=getattr(torch, os.environ.get("MATPCR_LOCAL_DTYPE", "bfloat16")),
            device_map=os.environ.get("MATPCR_LOCAL_DEVICE", "cuda:0")
        )
        pilot._LOCAL_PROCESSOR = AutoProcessor.from_pretrained(model_id)

    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    text = pilot._LOCAL_PROCESSOR.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = pilot._LOCAL_PROCESSOR(text=[text], return_tensors="pt").to(os.environ.get("MATPCR_LOCAL_DEVICE", "cuda:0"))
    out = pilot._LOCAL_MODEL.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    result = pilot._LOCAL_PROCESSOR.batch_decode(out[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)
    return result[0]


def run_text_api_openrouter(prompt: str, api_key: str, model: str = "google/gemini-2.5-flash-lite",
                             max_tokens: int = 1500):
    import requests

    # max_tokens raised 1000->1500 (2026-08-01): Gemini's magnetism prompt in
    # particular was truncating before FINAL_ANSWER on chemically ambiguous
    # formulas (rare-earth + transition-metal compositions -- the model
    # hedges much more there, same failure class as the earlier
    # stability-prompt truncation). The prompt wording above now also asks
    # explicitly for short, non-hedging reasoning; this token bump is
    # defense-in-depth, matching the two-part fix that worked for stability.
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }
    # See pilot.py's run_api_openrouter for why requests' (connect, read)
    # timeout tuple is used instead of urllib -- urllib's timeout did not
    # reliably bound a stalled response-body read in this environment,
    # confirmed directly via a >1hr production hang.
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=(10, 60),
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"], data.get("usage", {}).get("cost", None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=15)
    ap.add_argument("--claim_types", nargs="*", default=["stability", "metallicity", "magnetism"])
    ap.add_argument("--models", nargs="*", default=["local", "api"])
    ap.add_argument("--out", default="experiments/pilot_dft_results.jsonl")
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if "api" in args.models and not api_key:
        print("WARNING: OPENROUTER_API_KEY not set; skipping API model.")
        args.models = [m for m in args.models if m != "api"]

    with open(MP_DATA_PATH) as f:
        materials = [json.loads(line) for line in f][: args.n]

    total_cost = 0.0
    n_parse_ok = {}
    n_total = {}

    with open(args.out, "w") as out_f:
        for claim_type in args.claim_types:
            for m in materials:
                prompt = PROMPTS[claim_type].format(formula=m["formula_pretty"])
                for model_key in args.models:
                    key = (claim_type, model_key)
                    n_total[key] = n_total.get(key, 0) + 1
                    t0 = time.time()
                    try:
                        if model_key == "local":
                            chain_text = run_text_local_qwen(prompt)
                            cost = 0.0
                        else:
                            chain_text, cost = run_text_api_openrouter(prompt, api_key)
                            cost = cost or 0.0
                            total_cost += cost
                    except Exception as e:
                        chain_text = f"__ERROR__: {e}"
                        cost = 0.0
                    elapsed = time.time() - t0

                    parsed = parse_dft_chain(chain_text)
                    if parsed is not None:
                        n_parse_ok[key] = n_parse_ok.get(key, 0) + 1

                    record = {
                        "claim_type": claim_type,
                        "model": model_key,
                        "material_id": m["material_id"],
                        "formula": m["formula_pretty"],
                        "chain_text": chain_text,
                        "parsed": parsed,
                        "cost_usd": cost,
                        "elapsed_s": elapsed,
                    }
                    out_f.write(json.dumps(record) + "\n")
                    out_f.flush()
                    print(f"[{claim_type}/{model_key}] {m['formula_pretty']}: parsed={parsed} cost=${cost:.6f}")

    print("\n" + "=" * 70)
    print("PILOT summary (DFT modality): parser-extraction success rate")
    print("=" * 70)
    for key in sorted(n_total.keys()):
        ok = n_parse_ok.get(key, 0)
        tot = n_total[key]
        print(f"  {key[0]:12s} / {key[1]:6s}: {ok}/{tot} ({100*ok/tot:.0f}%)")
    print(f"\nTotal API cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
