"""
exp5_train_verifier.py
========================
Experiment 5 (matpcr_runbook.txt): fine-tune an open model on ORACLE labels
(no human labels) to predict whether a reasoning chain contains a physical
violation, from the input description + chain text alone. This is the
released, citable artifact.

Base model: Qwen2.5-0.5B-Instruct (decided 2026-07-11 -- small enough to
fine-tune/release/reproduce cheaply, sufficient capacity for a binary
classification task over structured chain text). LoRA fine-tune via peft,
sequence-classification head (binary: violation / clean), trained directly
on matpcr_metrics-compatible oracle labels from exp5_verifier_dataset.jsonl.

Three splits, each trained and evaluated independently (a real, separate model
per split, not one model sliced three ways -- required so "held-out modality"
genuinely means the model never saw that modality's chains during training):
  1. RANDOM (in-distribution): stratified 80/20 train/test over all 6 families
     pooled -- the baseline in-distribution performance number.
  2. HELD-OUT MODALITY: for each of the 6 modalities in turn, train on the
     other 5, test on the held-out one entirely. Reports whether the verifier
     generalizes to a modality it never saw a single example of.
  3. HELD-OUT CONSTRAINT TYPE: identical mechanism to (2) -- in this benchmark
     "constraint type" and "modality" are the same 6-way partition (each
     oracle family is its own constraint type), so this split answers the same
     generalization question from the runbook's other named axis using the
     same rotation; reported as its own table per the runbook's explicit ask
     for BOTH splits, but note in the manuscript that they coincide here.

Metrics: precision/recall/F1, ROC AUC, ECE (all from matpcr_metrics.py) on
each held-out test set.

Run: python3 experiments/exp5_train_verifier.py --split random
     python3 experiments/exp5_train_verifier.py --split modality --held_out xrd
     python3 experiments/exp5_train_verifier.py --split all   # runs everything
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
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matpcr_metrics import precision_recall_f1, roc_auc, expected_calibration_error, bootstrap_ci  # noqa: E402

DATA_PATH = os.environ.get(
    "EXP5_DATA_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "exp5_verifier_dataset.jsonl"),
)
MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
MODALITIES = ["xrd", "sem", "spectrum", "stability", "metallicity", "magnetism"]

WEIGHTS_ROOT = os.environ.get(
    "MATPCR_WEIGHTS_ROOT", os.path.join(MATPCR_DATA_ROOT, "verifier_weights")
)


def load_records():
    records = []
    with open(DATA_PATH) as f:
        for line in f:
            records.append(json.loads(line))
    return records


def format_text(r):
    return f"{r['input_text']}\n\nReasoning chain:\n{r['chain_text']}"


def make_split(records, mode, held_out=None, seed=0):
    """Returns (train_records, test_records).

    "random" is split at the SOURCE level, not the record level (fix for the
    supervisor audit's BL2 finding): experiments/halfB_fired_cases.jsonl and
    halfB_dft_fired_cases.jsonl can contain multiple records for the same
    underlying item (e.g. different models' claims about the same XRD
    pattern or the same material), all sharing one source_id. A record-level
    80/20 split can place two records of the SAME item in both train and
    test, leaking item identity into the "in-distribution" test set and
    inflating its AUC. Splitting at the source_id level guarantees no source
    item appears on both sides.
    """
    rng = np.random.default_rng(seed)
    if mode == "random":
        unique_sources = sorted(set(r["source_id"] for r in records))
        rng.shuffle(unique_sources)
        n_test_sources = max(1, int(0.2 * len(unique_sources)))
        test_sources = set(unique_sources[:n_test_sources])
        train = [r for r in records if r["source_id"] not in test_sources]
        test = [r for r in records if r["source_id"] in test_sources]
        return train, test
    elif mode in ("modality", "constraint"):
        assert held_out is not None
        train = [r for r in records if r["modality"] != held_out]
        test = [r for r in records if r["modality"] == held_out]
        return train, test
    raise ValueError(mode)


def train_and_eval(train_records, test_records, run_name: str, train_seed: int = 0):
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer, set_seed
    from peft import LoraConfig, get_peft_model, TaskType
    from torch.utils.data import Dataset

    # Pins torch/cuda/transformers RNG state so the released verifier is
    # bit-reproducible across re-runs, not just "equivalent" -- previously
    # only make_split()'s numpy RNG was seeded, leaving model init/LoRA
    # adapter init/dropout/data-loader shuffling all unpinned.
    set_seed(train_seed)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    class ChainDataset(Dataset):
        def __init__(self, records):
            self.records = records

        def __len__(self):
            return len(self.records)

        def __getitem__(self, idx):
            r = self.records[idx]
            enc = tokenizer(format_text(r), truncation=True, max_length=512, padding="max_length")
            enc["labels"] = r["violation"]
            return {k: torch.tensor(v) for k, v in enc.items()}

    train_ds = ChainDataset(train_records)
    test_ds = ChainDataset(test_records)

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_ID, num_labels=2, torch_dtype=getattr(torch, os.environ.get("EXP5_DTYPE", "bfloat16"))
    )
    model.config.pad_token_id = tokenizer.pad_token_id

    lora_config = LoraConfig(
        task_type=TaskType.SEQ_CLS,
        r=16, lora_alpha=32, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.to("cuda:0")

    out_dir = os.path.join(WEIGHTS_ROOT, run_name)
    os.makedirs(out_dir, exist_ok=True)

    args = TrainingArguments(
        output_dir=out_dir,
        num_train_epochs=int(os.environ.get("EXP5_EPOCHS", "4")),
        per_device_train_batch_size=8,
        per_device_eval_batch_size=16,
        learning_rate=2e-4,
        logging_steps=20,
        save_strategy="no",
        eval_strategy="no",
        report_to=[],
        # EXP5_DTYPE=float32 for GPUs without bf16 support (e.g. P100); default unchanged.
        bf16=os.environ.get("EXP5_DTYPE", "bfloat16") == "bfloat16",
        disable_tqdm=True,
    )
    trainer = Trainer(model=model, args=args, train_dataset=train_ds)
    trainer.train()
    # Persist the LoRA adapter + tokenizer (the original runs used save_strategy="no"
    # and never called save_pretrained, so no adapter weights were ever written).
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)

    model.eval()
    probs, preds, labels = [], [], []
    loader = torch.utils.data.DataLoader(test_ds, batch_size=16)
    with torch.no_grad():
        for batch in loader:
            batch = {k: v.to("cuda:0") for k, v in batch.items() if k != "labels"}
            logits = model(**batch).logits.float()
            p = torch.softmax(logits, dim=-1)[:, 1].cpu().numpy()
            probs.extend(p.tolist())
    labels = [r["violation"] for r in test_records]
    preds = [1 if p >= 0.5 else 0 for p in probs]

    prf = precision_recall_f1(preds, labels)
    auc = roc_auc(probs, labels)
    ece = expected_calibration_error(probs, labels)

    # free GPU memory before the next split trains
    del model
    torch.cuda.empty_cache()

    return {
        "run_name": run_name,
        "n_train": len(train_records),
        "n_test": len(test_records),
        "precision": prf["precision"],
        "recall": prf["recall"],
        "f1": prf["f1"],
        "roc_auc": auc,
        "ece": ece,
        "probs": probs,
        "labels": labels,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["random", "modality", "constraint", "all"], default="all")
    ap.add_argument("--held_out", default=None, help="modality/constraint name for a single held-out run")
    ap.add_argument("--out", default="experiments/exp5_results.jsonl")
    ap.add_argument("--train_seed", type=int, default=0,
                     help="Seeds torch/transformers training for bit-reproducible weights.")
    args = ap.parse_args()

    records = load_records()
    print(f"Loaded {len(records)} labeled records.")

    results = []
    runs = []
    if args.split in ("random", "all"):
        runs.append(("random", None))
    if args.split in ("modality", "all"):
        for m in MODALITIES:
            runs.append(("modality", m))
    if args.split in ("constraint", "all"):
        for m in MODALITIES:
            runs.append(("constraint", m))
    if args.split not in ("all",) and args.held_out is not None:
        runs = [(args.split, args.held_out)]

    with open(args.out, "a") as out_f:
        for mode, held_out in runs:
            run_name = f"{mode}" + (f"_heldout_{held_out}" if held_out else "")
            print(f"\n=== Training run: {run_name} ===")
            train_records, test_records = make_split(records, mode, held_out=held_out)
            print(f"  train={len(train_records)} test={len(test_records)}")
            result = train_and_eval(train_records, test_records, run_name, train_seed=args.train_seed)
            result["mode"] = mode
            result["held_out"] = held_out
            results.append(result)
            out_f.write(json.dumps(result) + "\n")
            out_f.flush()
            print(f"  precision={result['precision']:.3f} recall={result['recall']:.3f} "
                  f"F1={result['f1']:.3f} AUC={result['roc_auc']:.3f} ECE={result['ece']:.3f}")

    print(f"\nAll runs written to: {args.out}")


if __name__ == "__main__":
    main()
