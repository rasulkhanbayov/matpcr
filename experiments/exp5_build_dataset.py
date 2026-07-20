"""
exp5_build_dataset.py
=======================
Experiment 5 (matpcr_runbook.txt): consolidate every real (input, chain,
oracle-label) record already collected across Experiments 1/2/3/4 into one
unified verifier-training corpus. Reuses existing data -- no new model
calls, no new oracle definitions.

Sources (all real, oracle-checked records with full chain_text already on disk):
  - experiments/halfB_fired_cases.jsonl       (xrd, sem, spectrum -- despite the
    filename, this file contains BOTH consistent and inconsistent records, since
    halfB_collect.py logs every checked item, not only fired ones)
  - experiments/halfB_dft_fired_cases.jsonl   (stability, metallicity, magnetism;
    same "despite the name, both classes present" property)

Each output record: {modality, constraint_type, input_text, chain_text, violation, source_id}
  - input_text: a short, image-free description of the item's constraint context
    (what the claim is being checked against), matching the manuscript's
    "from the input and chain alone" framing -- the verifier never sees the
    original image, only text.
  - violation: 1 if oracle_consistent is False, else 0.
  - source_id: the item's parent source (source_file for XRD/SEM/spectrum,
    material_id for the DFT claim types). Added per the supervisor audit's BL2
    finding: without this, the random 80/20 in-distribution split in
    exp5_train_verifier.py cannot be verified as disjoint at the item/parent
    level, and (with multiple model records per source item across
    Experiments 2/3/4 all feeding this same file) a record-level split can
    silently place two records of the SAME underlying item in both train and
    test, leaking item identity and inflating the in-distribution number.

Run: python3 experiments/exp5_build_dataset.py
"""

from __future__ import annotations

import json
import os
import random

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOMETRIC_PATH = os.path.join(REPO_ROOT, "experiments", "halfB_fired_cases.jsonl")
DFT_PATH = os.path.join(REPO_ROOT, "experiments", "halfB_dft_fired_cases.jsonl")
OUT_PATH = os.path.join(REPO_ROOT, "experiments", "exp5_verifier_dataset.jsonl")

MODALITY_INPUT_TEMPLATES = {
    "xrd": "Modality: X-ray diffraction (XRD) pattern. Task: state the 2theta position "
           "(degrees) of the strongest peak.",
    "sem": "Modality: scanning electron microscope (SEM) image. Task: read the scale bar "
           "and estimate the size of the largest visible feature.",
    "spectrum": "Modality: Raman spectrum. Task: state the Raman shift (cm-1) of the "
                "strongest peak.",
    "stability": "Modality: DFT-grounded materials claim (text-only). Task: judge whether "
                 "the given chemical composition is thermodynamically STABLE or UNSTABLE.",
    "metallicity": "Modality: DFT-grounded materials claim (text-only). Task: judge whether "
                   "the given chemical composition is METALLIC or NONMETALLIC.",
    "magnetism": "Modality: DFT-grounded materials claim (text-only). Task: judge whether "
                 "the given chemical composition is MAGNETIC or NONMAGNETIC.",
}


def build_geometric_records():
    records = []
    if not os.path.exists(GEOMETRIC_PATH):
        return records
    with open(GEOMETRIC_PATH) as f:
        for line in f:
            r = json.loads(line)
            modality = r["modality"]
            input_text = MODALITY_INPUT_TEMPLATES[modality]
            records.append({
                "modality": modality,
                "constraint_type": modality,
                "input_text": input_text,
                "chain_text": r["chain_text"],
                "violation": 0 if r["oracle_consistent"] else 1,
                "source_id": r["source_file"],
            })
    return records


def build_dft_records():
    records = []
    if not os.path.exists(DFT_PATH):
        return records
    with open(DFT_PATH) as f:
        for line in f:
            r = json.loads(line)
            claim_type = r["claim_type"]
            input_text = MODALITY_INPUT_TEMPLATES[claim_type] + f" Composition: {r['formula']}."
            records.append({
                "modality": claim_type,
                "constraint_type": claim_type,
                "input_text": input_text,
                "chain_text": r["chain_text"],
                "violation": 0 if r["oracle_consistent"] else 1,
                "source_id": r["material_id"],
            })
    return records


def main():
    records = build_geometric_records() + build_dft_records()
    rng = random.Random(0)
    rng.shuffle(records)

    with open(OUT_PATH, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    from collections import Counter
    c = Counter((r["modality"], r["violation"]) for r in records)
    print(f"Total records: {len(records)}")
    for modality in MODALITY_INPUT_TEMPLATES:
        n_clean = c.get((modality, 0), 0)
        n_viol = c.get((modality, 1), 0)
        print(f"  {modality:12s} clean={n_clean:4d} violation={n_viol:4d} total={n_clean+n_viol:4d}")
    print(f"\nWritten to: {OUT_PATH}")


if __name__ == "__main__":
    main()
