"""
exp10_violation_taxonomy.py
==============================
REVISION_PLAN.md Phase 2, item 20 (audit EX8): categorize the TYPES of
physical-consistency violation found, not just their rate. Reuses the
already-human-reviewed "real violation" cases from Experiment 1's Half-B
manual review (xrd.txt / sem.txt, the exported verdicts from
experiments/halfB_review_{xrd,sem}.html) -- only cases a human already
confirmed are genuine violations (verdict == "real"), matched back to their
full chain_text via halfB_fired_cases.jsonl's deterministic file-order
mapping (case N == the Nth fired=True record for that modality, 1-indexed,
per halfB_report.py's render order -- confirmed directly: 78 "real" XRD
cases here matches CLAUDE.md's already-reported 78/101 precision figure).

SPECTRUM IS DELIBERATELY EXCLUDED. spectrum.txt's review (103 cases) predates
the Phase 0 spectrum-oracle fix (genuine-local-maximum requirement); the
CURRENT halfB_fired_cases.jsonl has 495 fired spectrum records (not 103) --
confirmed directly, 2026-07-19 -- because the oracle fix changed which
claims fire at all (CLAUDE.md SS19: 392/575 records flipped). The case-number
mapping for spectrum is therefore for a population that no longer exists;
building a taxonomy from it would silently mix up which chains the review
verdicts actually apply to. This must wait for the fresh spectrum Half-B
review that CLAUDE.md's own "Not yet done" list already flags as outstanding
-- not re-derived here from a stale mapping.

DFT families (stability/metallicity/magnetism) are ALSO excluded: their
stability.txt/metallicity.txt/magnetism.txt reviews are explicitly marked
stale in CLAUDE.md SS19 (predate the Mustafa-driven oracle redesign), and the
corrected re-review is a standing blocking item, not done yet.

Method: send each real-violation chain (XRD, SEM only) to a cheap API model
(Gemini 2.5 Flash Lite, reused from every other experiment here) with an
OPEN-ENDED categorization prompt (not a fixed pre-written list of categories
-- forcing a fixed taxonomy before seeing the data risks fabricating
categories the data doesn't actually support). A second pass then clusters
the free-text category labels the model produced into a small final taxonomy
by exact/near string match, and reports frequency + one example chain per
category.

Run: python3 experiments/exp10_violation_taxonomy.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pilot_dft  # noqa: E402  (reuse run_text_api_openrouter)

FIRED_CASES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "halfB_fired_cases.jsonl")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CATEGORIZE_PROMPT = """A vision-language model was asked to read a physical measurement off a plot (an XRD diffractogram \
or an SEM micrograph with a scale bar) and state a claim. A human reviewer has already confirmed this specific claim \
is a REAL physical-consistency violation (not a false positive) -- your job is only to classify WHY it is wrong, not \
whether it is wrong.

MODALITY: {modality}
TASK PROMPT GIVEN TO THE MODEL: {prompt}
MODEL'S FULL REASONING CHAIN: {chain_text}

In 2-5 words, name the SPECIFIC failure mode this reasoning chain shows (e.g. "misread gridline scale", "picked wrong \
peak/feature", "arithmetic error in the estimate", "confused axis units", "hallucinated a value not in the image", \
"off-by-one-order-of-magnitude"). Be specific and consistent -- if you see the same underlying mistake pattern again, \
use the SAME short label you would have used before. End your response with EXACTLY one line:
CATEGORY: <your 2-5 word label>
"""

_CATEGORY_RE = re.compile(r"CATEGORY:\s*\**_*\s*(.+)", re.IGNORECASE)


def load_real_violation_cases(modality, review_path):
    fired = []
    with open(FIRED_CASES_PATH) as f:
        for line in f:
            r = json.loads(line)
            if r.get("modality") == modality and r.get("fired"):
                fired.append(r)
    with open(review_path) as f:
        reviews = {r["case"]: r["verdict"] for r in json.load(f)["reviews"]}
    if len(reviews) != len(fired):
        raise RuntimeError(
            f"{modality}: review file has {len(reviews)} cases but current fired-cases population "
            f"has {len(fired)} -- case-number mapping is STALE, do not proceed (see module docstring)."
        )
    real = [fired[i] for i in range(len(fired)) if reviews.get(i + 1) == "real"]
    return real


def categorize(cases, api_key, model="google/gemini-2.5-flash-lite"):
    labeled = []
    cost = 0.0
    for i, c in enumerate(cases):
        prompt = CATEGORIZE_PROMPT.format(
            modality=c["modality"], prompt=c["prompt"][:600], chain_text=c["chain_text"]
        )
        try:
            text, call_cost = pilot_dft.run_text_api_openrouter(prompt, api_key, model=model)
        except Exception as e:
            print(f"    item {i} call failed: {e}", flush=True)
            continue
        cost += call_cost or 0.0
        m = _CATEGORY_RE.search(text or "")
        if m:
            label = m.group(1).strip().rstrip(".")
        else:
            # Model frequently skips the "CATEGORY:" prefix and just returns
            # the short label directly (confirmed on a live sample,
            # 2026-07-19) -- fall back to the last non-empty line if it's
            # short enough to plausibly be a label, rather than discarding.
            lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
            label = lines[-1].rstrip(".") if lines and len(lines[-1]) <= 60 else "UNPARSED"
        labeled.append({**c, "category_raw": label})
        if (i + 1) % 20 == 0:
            print(f"    {i+1}/{len(cases)} labeled (cost=${cost:.4f})", flush=True)
    return labeled, cost


CLUSTER_PROMPT = """You are given a list of short failure-mode labels that a model produced for individual model \
reasoning-chain errors on a {modality} task. Many labels describe the SAME underlying failure mode in different \
words (e.g. "misread gridline scale", "Misread tick mark scale", and "misread x-axis tickmarks" are all the same \
underlying mistake). Group these labels into a SMALL number of canonical categories (aim for 4-8 categories total \
-- do not create a separate category for every distinct wording).

LABELS (with how many times each exact wording occurred):
{label_list}

Respond with ONLY a JSON object mapping EVERY label string above (exactly as given) to ONE short canonical category \
name of your choosing (reuse the SAME canonical name for labels that describe the same failure mode). Example \
format: {{"label one": "canonical category A", "label two": "canonical category A", "label three": "canonical category B"}}
No other text, just the JSON object.
"""


def cluster_labels_semantic(labeled, modality, api_key, model="google/gemini-2.5-flash-lite"):
    """First pass (categorize()) is intentionally open-ended per-item, which
    produces many near-synonymous wordings of the same failure mode rather
    than a usable taxonomy (confirmed directly, 2026-07-19: XRD's first pass
    produced 30 distinct raw labels for 78 items, with obvious duplicates
    like "misread gridline scale" / "Misread tick mark scale" / "misread
    x-axis tickmarks" scattered across 1-count singleton buckets). This
    second pass sends the DISTINCT raw labels (not every record -- cheap,
    one call regardless of n) to the same model and asks it to group them
    into a small canonical taxonomy, which is then applied back to every
    record via its raw label."""
    raw_counts = Counter(l["category_raw"] for l in labeled)
    label_list = "\n".join(f'- "{lbl}" (x{n})' for lbl, n in raw_counts.most_common())
    prompt = CLUSTER_PROMPT.format(modality=modality, label_list=label_list)
    text, cost = pilot_dft.run_text_api_openrouter(prompt, api_key, model=model)
    text = (text or "").strip()
    # Strip markdown code fences if present.
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        mapping = json.loads(text)
    except Exception:
        mapping = {}
    return mapping, cost


def build_taxonomy(labeled, mapping):
    canon_of = {}
    for l in labeled:
        raw = l["category_raw"]
        canon_of[raw] = mapping.get(raw, raw)  # fall back to raw label if the clustering call missed it
    by_canon = {}
    for l in labeled:
        by_canon.setdefault(canon_of[l["category_raw"]], []).append(l)
    taxonomy = []
    for canon, examples in sorted(by_canon.items(), key=lambda kv: -len(kv[1])):
        taxonomy.append({
            "category": canon,
            "count": len(examples),
            "frac": len(examples) / len(labeled),
            "raw_labels_merged": sorted(set(e["category_raw"] for e in examples)),
            "example_source_file": examples[0]["source_file"],
            "example_chain_text": examples[0]["chain_text"],
        })
    return taxonomy


def main():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set.")

    results = {}
    total_cost = 0.0
    for modality, review_file in [("xrd", "xrd.txt"), ("sem", "sem.txt")]:
        review_path = os.path.join(REPO_ROOT, review_file)
        cases = load_real_violation_cases(modality, review_path)
        print(f"[{modality}] {len(cases)} human-confirmed real violations to categorize")
        labeled, cost = categorize(cases, api_key)
        total_cost += cost
        mapping, cluster_cost = cluster_labels_semantic(labeled, modality, api_key)
        total_cost += cluster_cost or 0.0
        taxonomy = build_taxonomy(labeled, mapping)
        results[modality] = {"n_violations": len(cases), "n_labeled": len(labeled), "taxonomy": taxonomy}
        print(f"[{modality}] taxonomy ({len(taxonomy)} categories):")
        for t in taxonomy:
            print(f"    {t['category']}: {t['count']} ({t['frac']:.1%})")

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp10_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nTotal API cost: ${total_cost:.4f}")
    print(f"Written to: {out_path}")
    print("\nSpectrum and all 3 DFT families excluded -- their existing human reviews are stale "
          "against the current (corrected) oracle's fired-case population; see module docstring.")


if __name__ == "__main__":
    main()
