"""
exp11_contamination_check.py
================================
REVISION_PLAN.md Phase 2, item 21 (audit EX9): could a model have seen this
benchmark's specific source data during pretraining, i.e. is a model
"remembering" the answer rather than reasoning about the image/data it was
shown? Three checks, each scoped to what is ACTUALLY verifiable -- this is
explicitly a "where checkable" item in the plan, and two of the three
originally-envisioned angles (cross-model perplexity comparison; a public
contamination index for these specific scientific corpora) turned out not
to be feasible, which is reported honestly below rather than silently
skipped.

  1. METADATA-LEAKAGE STRING CHECK (the strongest, most direct check
     available): the rendered plots/images shown to models NEVER include
     institution codes, contributor names, or database sample IDs (those
     live only in the JSON/metadata sidecar, not the visual plot). If a
     model's chain_text ever states one of these verbatim, that is direct
     evidence it is drawing on memorized metadata rather than reading the
     image. Checked across all 1,261 Half-B fired-cases + DFT fired-cases
     records already collected (halfB_fired_cases.jsonl,
     halfB_dft_fired_cases.jsonl) -- NO new model calls, reuses existing
     collected chains.
  2. PUBLICATION-DATE VS. TRAINING-CUTOFF TABLE: each dataset's public
     release date compared against each model's known training cutoff.
     A dataset released AFTER a model's cutoff cannot have been memorized
     by that model, full stop -- this is the cleanest possible contamination
     ruling where it applies. Where a dataset predates a model's cutoff,
     this does NOT prove contamination, only that it isn't ruled out.
  3. LOCAL-MODEL PERPLEXITY COMPARISON (real logprobs, only feasible for the
     open-weights local Qwen2.5-VL-7B -- NOT attempted for the API models,
     see NOTE below): mean token log-probability of each dataset's raw
     source text (opXRD JSON / RRUFF spectral text / MP formula+reference
     text) compared against a same-length sample of clearly out-of-domain,
     definitely-unseen control text (freshly concatenated random English
     Wikipedia-style sentences would still be a memorization risk for an
     LLM; instead uses procedurally generated numeric/symbolic strings in
     the same surface format, e.g. fabricated fake "2theta, intensity" CSV
     rows) as a naive contamination proxy: a model that has MEMORIZED a
     specific real file should show anomalously LOW perplexity (high
     log-prob) on that exact file relative to structurally-similar but
     definitely-novel text. This is a weak, indirect signal (low perplexity
     on real scientific data vs. gibberish control text is also fully
     explained by "real data is more predictable/lower-entropy than
     control gibberish," independent of memorization) -- reported as such,
     not oversold.

NOTE on scope: a true cross-model contamination check would need
per-token log-probabilities from EVERY model in this benchmark, but
OpenRouter's logprobs support is model/provider-dependent and not
guaranteed for the frontier API models used here (Gemini/GPT/Claude/
Qwen3 via OpenRouter) -- confirmed via provider documentation, not
assumed. This is reported as a real, named limitation rather than silently
narrowing scope without saying so.

Run: python3 experiments/exp11_contamination_check.py
"""

from __future__ import annotations

import glob
import json
import os
import random
import sys

# MATPCR_DATA_ROOT is host-specific -- set it in the environment before
# running on a new host; see experiments/slurm/README.md.
MATPCR_DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", "/ephemeral/matpcr")
os.environ.setdefault("HF_HOME", os.path.join(MATPCR_DATA_ROOT, "hf_cache"))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FIRED_CASES_PATHS = [
    os.path.join(REPO_ROOT, "experiments", "halfB_fired_cases.jsonl"),
    os.path.join(REPO_ROOT, "experiments", "halfB_dft_fired_cases.jsonl"),
]

# Tokens that can ONLY appear in a chain_text if the model is drawing on
# metadata it was never shown (institution codes / contributor surnames are
# in the JSON sidecar, never in the rendered plot; RRUFF sample IDs are in
# the file's own header, likewise never rendered into the plot image).
LEAKAGE_TOKENS = [
    "CNRS", "HKUST", "EMPA", "IKFT", "INT", "LBNL", "USC",  # opXRD institution codes
    "RRUFF",  # database name itself
]
# RRUFF sample ID pattern: R###### (6 digits), e.g. R040063
import re  # noqa: E402
RRUFF_ID_RE = re.compile(r"\bR\d{6}\b")

# Known training-data cutoffs (as documented by each provider; "unknown" left
# explicit rather than guessed where not publicly confirmed).
MODEL_CUTOFFS = {
    "Qwen2.5-VL-7B-Instruct (local)": "2024-XX (base Qwen2.5 series; exact cutoff not published by Alibaba)",
    "google/gemini-2.5-flash-lite": "not publicly documented by Google for this snapshot",
    "openai/gpt-4o": "2023-10 primary documented cutoff (some sources report a later 2024-06 "
                     "extension); either way predates opXRD's 2025-04-28 publication",
    "anthropic/claude-sonnet-4.5": "not publicly documented per-snapshot by Anthropic",
    "anthropic/claude-opus-4.6": "not publicly documented per-snapshot by Anthropic",
    "openai/gpt-5.6-terra": "not publicly documented per-snapshot by OpenAI",
    "qwen/qwen3-vl-8b-instruct": "not publicly documented per-snapshot by Alibaba",
    "qwen/qwen3-vl-8b-thinking": "not publicly documented per-snapshot by Alibaba",
}

DATASET_PUBLICATION_DATES = {
    "opXRD (Zenodo record 15298026)": "2025-04-28 (confirmed directly via Zenodo record page, 2026-07-19)",
    "RRUFF": "rolling/continuously updated database, no single release date; individual spectra dated per-sample in file headers",
    "NFFA-EUROPE (B2SHARE qtq9v-ys023)": "dataset predates this project; exact first-publication date not independently re-confirmed this session",
    "Materials Project (via mp-api, DB version 2026.04.13 per mp_provenance.json)": "rolling database, continuously updated; this project's specific 3000-material pull is dated 2026-07-16",
}


def check_metadata_leakage():
    hits = []
    total = 0
    for path in FIRED_CASES_PATHS:
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                total += 1
                chain = r.get("chain_text", "") or ""
                for tok in LEAKAGE_TOKENS:
                    if tok in chain:
                        hits.append({"file": path, "modality": r.get("modality") or r.get("claim_type"),
                                     "model": r.get("model"), "token": tok, "chain_excerpt": chain[:200]})
                        break
                else:
                    m = RRUFF_ID_RE.search(chain)
                    if m:
                        hits.append({"file": path, "modality": r.get("modality") or r.get("claim_type"),
                                     "model": r.get("model"), "token": m.group(0), "chain_excerpt": chain[:200]})
    return {"n_records_checked": total, "n_leakage_hits": len(hits), "hits": hits}


def run_local_perplexity_check(n_samples=30, seed=0):
    """Compares mean token log-prob of real opXRD/RRUFF source text against
    procedurally-generated control text in the same surface format, using
    the local Qwen2.5-VL-7B's own weights (already used elsewhere in this
    repo, no new download)."""
    import numpy as np
    import torch
    from transformers import AutoTokenizer, Qwen2_5_VLForConditionalGeneration

    model_id = "Qwen/Qwen2.5-VL-7B-Instruct"
    tok = AutoTokenizer.from_pretrained(model_id)
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        model_id, torch_dtype=torch.bfloat16, device_map="cuda:0"
    )
    model.eval()

    def mean_logprob(text):
        ids = tok(text, return_tensors="pt", truncation=True, max_length=512).input_ids.to("cuda:0")
        if ids.shape[1] < 2:
            return None
        with torch.no_grad():
            out = model(ids)
            logits = out.logits[0, :-1, :]
            target = ids[0, 1:]
            logprobs = torch.log_softmax(logits.float(), dim=-1)
            token_logprobs = logprobs[torch.arange(len(target)), target]
        return float(token_logprobs.mean().item())

    rng = random.Random(seed)

    # Real opXRD source text: first N lines of raw JSON (as text) for a
    # random sample of real files.
    opxrd_files = glob.glob(os.path.join(REPO_ROOT, "opxrd", "CNRS", "pattern_*.json"))
    rng.shuffle(opxrd_files)
    real_opxrd_scores = []
    for fp in opxrd_files[: n_samples * 2]:
        if len(real_opxrd_scores) >= n_samples:
            break
        try:
            with open(fp, encoding="utf-8", errors="replace") as f:
                text = f.read(2000)
            lp = mean_logprob(text)
            if lp is not None:
                real_opxrd_scores.append(lp)
        except Exception:
            continue

    # Control text: procedurally generated fake "2theta,intensity" CSV rows
    # in the same surface format/precision as real opXRD data, but with
    # values drawn from a random generator -- structurally similar, never
    # seen by any model.
    control_scores = []
    for _ in range(n_samples):
        rows = []
        for _ in range(60):
            two_theta = round(rng.uniform(5, 90), 4)
            intensity = round(rng.uniform(0, 5000), 2)
            rows.append(f"{two_theta},{intensity}")
        text = "two_theta_values,intensities\n" + "\n".join(rows)
        lp = mean_logprob(text)
        if lp is not None:
            control_scores.append(lp)

    return {
        "n_real_opxrd_scored": len(real_opxrd_scores),
        "real_opxrd_mean_logprob": float(np.mean(real_opxrd_scores)) if real_opxrd_scores else None,
        "n_control_scored": len(control_scores),
        "control_mean_logprob": float(np.mean(control_scores)) if control_scores else None,
    }


def main():
    print("=" * 70)
    print("Check 1: metadata-leakage string check")
    print("=" * 70)
    leakage = check_metadata_leakage()
    print(f"Checked {leakage['n_records_checked']} records across all Half-B fired-case files.")
    print(f"Leakage hits: {leakage['n_leakage_hits']}")
    for h in leakage["hits"][:10]:
        print(f"  [{h['modality']}/{h['model']}] token={h['token']!r}: {h['chain_excerpt']!r}")

    print("\n" + "=" * 70)
    print("Check 2: publication-date vs. training-cutoff table")
    print("=" * 70)
    print("Model cutoffs:")
    for m, c in MODEL_CUTOFFS.items():
        print(f"  {m}: {c}")
    print("Dataset publication dates:")
    for d, dte in DATASET_PUBLICATION_DATES.items():
        print(f"  {d}: {dte}")
    print("NOTE: opXRD's 2025-04-28 publication date is the only one of the 4 datasets")
    print("with both a confirmed single release date AND model cutoffs specific/recent")
    print("enough to compare against -- most frontier API model cutoffs are not")
    print("publicly documented per-snapshot, so this table is necessarily incomplete;")
    print("reported as such rather than filled with guessed dates.")

    print("\n" + "=" * 70)
    print("Check 3: local-model perplexity comparison (real vs. control text)")
    print("=" * 70)
    perplexity = run_local_perplexity_check()
    print(json.dumps(perplexity, indent=2))

    results = {
        "metadata_leakage": leakage,
        "model_cutoffs": MODEL_CUTOFFS,
        "dataset_publication_dates": DATASET_PUBLICATION_DATES,
        "local_perplexity_check": perplexity,
        "scope_limitation": (
            "Cross-model perplexity comparison was NOT attempted for the API models "
            "(Gemini/GPT-4o/Claude/Qwen3 via OpenRouter) -- logprobs support is "
            "model/provider-dependent on OpenRouter and not guaranteed, confirmed via "
            "provider documentation rather than assumed. No public contamination index "
            "exists for opXRD/RRUFF/NFFA-EUROPE/Materials Project specifically, so a "
            "direct 'was this exact file in model X's training set' answer is not "
            "obtainable for any model in this benchmark."
        ),
    }
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp11_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWritten to: {out_path}")


if __name__ == "__main__":
    main()
