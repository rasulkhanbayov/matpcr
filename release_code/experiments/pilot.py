"""
pilot.py
========
PILOT stage (matpcr_runbook.txt, before Experiment 1): run 50-100 items per
modality through ONE local model + ONE API model. Confirm the model's chain
EXPOSES a checkable quantity and that a parser can extract it; if not, fix
the prompt. This is NOT Experiment 1 (no injected violations, no PCR table
placed in the paper) -- it is a feasibility/prompt-engineering check.

Modalities covered (real data, matching what's actually on disk):
  - XRD:      opXRD real patterns, rendered as a diffractogram PNG, model
              asked to state the 2theta position of the strongest peak.
  - SEM:      NFFA-EUROPE real micrographs, model asked to state the size
              (in the scale bar's unit) of a described feature.
  - Spectrum: RRUFF real Raman spectra, rendered as a PNG, model asked to
              state the Raman shift (cm^-1) of the strongest peak.

Models:
  - Local:  Qwen/Qwen2.5-VL-7B-Instruct (transformers, this machine's A100).
  - API:    google/gemini-2.5-flash-lite via OpenRouter (cheap, vision-capable;
            picked deliberately for a small credit budget -- see CLAUDE.md).

Each item's chain is parsed with a permissive regex for a
"<number> <unit>"-shaped claim. Parse success/failure is the PILOT's real
metric -- NOT whether the claim is correct (that's Experiment 1's job).

Run: python3 experiments/pilot.py --n 10 --modalities xrd sem spectrum
"""

from __future__ import annotations

import os

# Must be set before any huggingface_hub/transformers import, and set here
# explicitly rather than relying on shell env -- an earlier host had
# conflicting HF_HOME exports from prior sessions/other users (confirmed:
# ~/.bashrc had two different paths, and the actual env resolved to a THIRD,
# unrelated path that didn't even exist as a distinct mount). Setting it here
# is the only reliable way to guarantee the local model downloads somewhere
# with real space instead of failing or landing on a small root disk.
# MATPCR_DATA_ROOT is host-specific (the old /ephemeral/matpcr root was on a
# machine that no longer exists) -- set it in the environment before running
# on a new host; see experiments/slurm/README.md.
MATPCR_DATA_ROOT = os.environ.get("MATPCR_DATA_ROOT", "/ephemeral/matpcr")
os.environ["HF_HOME"] = os.path.join(MATPCR_DATA_ROOT, "hf_cache")

import argparse
import glob
import json
import random
import re
import sys
import threading
import time

import numpy as np

# matplotlib's Agg backend keeps global mutable figure-stack state that is
# NOT thread-safe. exp2_pcr_sweep.py's call_with_hard_timeout backstop can
# leave a daemon thread running past its timeout (by design -- it must not
# block the main thread); if that thread is still inside requests/networking
# code while the main thread starts building the next item batch, there is
# no overlap. But if a future caller ever touches matplotlib from a
# background thread, or two builders somehow run concurrently, this lock
# prevents corrupting the shared Agg canvas state (root cause of a real
# 2026-07-17 crash: "AttributeError: '_idat' object has no attribute
# 'fileno'" inside PIL's PNG writer, consistent with two savefig calls
# racing on the same global canvas).
_MPL_LOCK = threading.Lock()

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

OPXRD_ROOT = os.path.join(REPO_ROOT, "opxrd")
NFFA_ROOT = os.path.join(MATPCR_DATA_ROOT, "nffa", "extracted")
RRUFF_ROOT = os.path.join(MATPCR_DATA_ROOT, "rruff", "extracted")

SCRATCH_IMG_DIR = os.environ.get(
    "MATPCR_SCRATCH_IMG_DIR", os.path.join(MATPCR_DATA_ROOT, "pilot_images")
)
os.makedirs(SCRATCH_IMG_DIR, exist_ok=True)


# ----------------------------------------------------------------------------
# Item builders per modality: return (image_path, prompt_text, ground_truth_context)
# ----------------------------------------------------------------------------
def build_xrd_items(n: int, seed: int = 0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rng = random.Random(seed)
    files = sorted(glob.glob(os.path.join(OPXRD_ROOT, "CNRS", "pattern_*.json")))
    rng.shuffle(files)

    items = []
    for fp in files:
        if len(items) >= n:
            break
        try:
            with open(fp, encoding="utf-8", errors="replace") as f:
                d = json.load(f)
            two_theta = np.asarray(d["two_theta_values"], dtype=float)
            intensities = np.asarray(d["intensities"], dtype=float)
            if two_theta.size < 10:
                continue
        except Exception:
            continue

        img_path = os.path.join(SCRATCH_IMG_DIR, f"xrd_{os.path.basename(fp)}.png")
        with _MPL_LOCK:
            fig, ax = plt.subplots(figsize=(8, 5), dpi=120)
            ax.plot(two_theta, intensities, linewidth=0.8, color="black")
            ax.set_xlabel("2theta (degrees)")
            ax.set_ylabel("Intensity")
            ax.set_title("XRD pattern")
            ax.set_xticks(np.arange(0, two_theta.max() + 10, 10))
            ax.grid(True, axis="x", linestyle=":", alpha=0.5)
            fig.savefig(img_path, bbox_inches="tight")
            plt.close(fig)

        prompt = (
            "This image shows an X-ray diffraction (XRD) pattern: 2theta (degrees) on the "
            "x-axis vs intensity on the y-axis. Identify the SINGLE strongest peak (the "
            "tallest one). Read its 2theta position carefully by finding exactly where the "
            "PEAK'S APEX (highest point) sits on the x-axis -- do not just say the axis "
            "starts near there; look at the gridlines/tick marks to estimate the value as "
            "precisely as you can, to one decimal place. State it as a number followed by "
            "'deg', e.g. '28.4 deg'. Give your reasoning briefly, then end with a line: "
            "FINAL_ANSWER: <value> deg"
        )
        items.append({"modality": "xrd", "image_path": img_path, "prompt": prompt, "source_file": fp})
    return items


def build_sem_items(n: int, seed: int = 0):
    rng = random.Random(seed)
    categories = sorted(os.listdir(NFFA_ROOT))
    all_files = []
    for cat in categories:
        cat_dir = os.path.join(NFFA_ROOT, cat)
        all_files.extend(glob.glob(os.path.join(cat_dir, "*.jpg")))
    rng.shuffle(all_files)

    items = []
    for fp in all_files[: n * 2]:
        if len(items) >= n:
            break
        prompt = (
            "This is a scanning electron microscope (SEM) image. It includes an instrument "
            "info bar (usually at the bottom) with a scale bar showing a real-world length "
            "(e.g. '10 um' or '2 um'). Read the scale bar's stated length and unit. Then "
            "estimate the size of the main/largest visible feature in the micrograph, using "
            "the scale bar to convert from pixels to real units. Give your reasoning briefly. "
            "Your final answer MUST be a SINGLE plain number (not a range like '800-1000', "
            "pick your best single estimate) and MUST be plain text with no LaTeX/markdown "
            "formatting (no \\[ \\] or \\text{} or $ signs). End with EXACTLY this format on "
            "its own line: FINAL_ANSWER: <value> <unit>  (e.g. 'FINAL_ANSWER: 3.5 um')"
        )
        items.append({"modality": "sem", "image_path": fp, "prompt": prompt, "source_file": fp})
    return items


def build_spectrum_items(n: int, seed: int = 0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rng = random.Random(seed)
    files = sorted(glob.glob(os.path.join(RRUFF_ROOT, "*Raman_Data_Processed*.txt")))
    rng.shuffle(files)

    items = []
    for fp in files:
        if len(items) >= n:
            break
        xs, ys = [], []
        try:
            with open(fp, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("##"):
                        continue
                    parts = line.split(",")
                    if len(parts) != 2:
                        continue
                    xs.append(float(parts[0]))
                    ys.append(float(parts[1]))
        except Exception:
            continue
        if len(xs) < 10:
            continue

        img_path = os.path.join(SCRATCH_IMG_DIR, f"raman_{os.path.basename(fp)}.png")
        with _MPL_LOCK:
            fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
            ax.plot(xs, ys, linewidth=0.8, color="black")
            ax.set_xlabel("Raman shift (cm-1)")
            ax.set_ylabel("Intensity")
            ax.set_title("Raman spectrum")
            fig.savefig(img_path, bbox_inches="tight")
            plt.close(fig)

        prompt = (
            "This image shows a Raman spectrum: Raman shift (cm-1) on the x-axis vs "
            "intensity on the y-axis. Identify the SINGLE strongest peak (the tallest one). "
            "State its Raman shift as a number followed by 'cm-1', e.g. '520 cm-1'. Give "
            "your reasoning briefly, then end with a line: FINAL_ANSWER: <value> cm-1"
        )
        items.append({"modality": "spectrum", "image_path": img_path, "prompt": prompt, "source_file": fp})
    return items


MODALITY_BUILDERS = {
    "xrd": build_xrd_items,
    "sem": build_sem_items,
    "spectrum": build_spectrum_items,
}


# ----------------------------------------------------------------------------
# Parser: extract the FINAL_ANSWER line's number + unit.
#
# Tolerant of real deviations seen in this pilot's actual model output, not
# hypothetical ones: "Final Answer" (space, not underscore) instead of
# "FINAL_ANSWER"; a RANGE ("800-1000 nm") instead of a single number -- take
# the range's midpoint rather than failing, since the model did state a
# checkable band, just not in the single-number format asked for; LaTeX
# wrapping ("\[ \text{Final Answer: } 15 \, \mu\text{m} \]") around the
# answer -- strip common LaTeX control sequences before matching instead of
# rejecting the line outright.
# ----------------------------------------------------------------------------
FINAL_ANSWER_RE = re.compile(
    r"FINAL[_ ]ANSWER[:\}]*\s*([\d.]+)\s*(?:[-–]\s*([\d.]+)\s*)?"
    r"(deg|cm-1|u\s*m|µ\s*m|μ\s*m|nm|mm)",
    re.IGNORECASE,
)

_LATEX_STRIP_RE = re.compile(r"\\[a-zA-Z]+|[{}\[\]$]|\\,")
_LATEX_MU_RE = re.compile(r"\\mu")


def parse_chain(text: str):
    # \mu IS the unit's Greek-letter prefix (e.g. "\mu\text{m}" -> "um") --
    # substitute it BEFORE the generic LaTeX-command strip below, which would
    # otherwise delete "\mu" as if it were inert formatting and leave a bare,
    # unmatchable "m" (confirmed directly: this exact case was silently
    # dropped before this substitution was added).
    cleaned = _LATEX_MU_RE.sub("u", text)
    cleaned = _LATEX_STRIP_RE.sub(" ", cleaned)
    m = FINAL_ANSWER_RE.search(cleaned)
    if not m:
        return None
    lo = float(m.group(1))
    hi = float(m.group(2)) if m.group(2) else None
    value = (lo + hi) / 2 if hi is not None else lo
    unit = re.sub(r"\s+", "", m.group(3).lower())
    if unit == "μm":
        unit = "µm"
    return {"value": value, "unit": unit, "was_range": hi is not None}


# ----------------------------------------------------------------------------
# Model runners
# ----------------------------------------------------------------------------
_LOCAL_MODEL = None
_LOCAL_PROCESSOR = None


def run_local_qwen(image_path: str, prompt: str, max_new_tokens: int = 600) -> str:
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
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    text = _LOCAL_PROCESSOR.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = _LOCAL_PROCESSOR(text=[text], images=[image], return_tensors="pt").to("cuda:0")
    out = _LOCAL_MODEL.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    result = _LOCAL_PROCESSOR.batch_decode(
        out[:, inputs.input_ids.shape[1] :], skip_special_tokens=True
    )
    return result[0]


def run_api_openrouter(image_path: str, prompt: str, api_key: str, model: str = "google/gemini-2.5-flash-lite") -> str:
    import base64
    import mimetypes
    import requests

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    # The MIME type MUST match the real file format, not be hardcoded to
    # PNG. Confirmed as a real production bug (2026-07-10): NFFA-EUROPE SEM
    # images are real JPEGs, but this function always declared
    # "data:image/png" -- Gemini/GPT-4o silently tolerated the mismatch, but
    # Claude correctly validates the declared MIME type against the actual
    # image bytes and rejected every single SEM call with a 400 (visible
    # only once the sweep reached Claude+SEM; XRD/spectrum are genuinely PNG
    # since they're matplotlib-rendered, so this bug was invisible there).
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        mime_type = "image/png"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                ],
            }
        ],
        "max_tokens": 700,
    }
    # requests' (connect, read) timeout tuple reliably bounds BOTH phases.
    # A real production run hung for >1hr on a stalled response-body read
    # despite urllib.request.urlopen(timeout=60) being set -- confirmed via
    # `ss -tnp`: socket sat in CLOSE-WAIT with unread bytes, meaning urllib's
    # timeout only covered the connect phase in this environment, not a
    # stalled read after headers arrived. requests' read timeout is enforced
    # per socket .recv() call, which is what actually bounds this failure
    # mode -- see exp2_pcr_sweep.py's call_with_hard_timeout docstring for
    # the full incident (a thread-based backstop was tried first and also
    # failed: the underlying blocking call doesn't respect thread joins,
    # it just leaks threads while the real socket read stays stuck).
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=(10, 60),
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"], data.get("usage", {}).get("cost", None)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10, help="items per modality")
    ap.add_argument("--modalities", nargs="*", default=["xrd", "sem", "spectrum"])
    ap.add_argument("--models", nargs="*", default=["local", "api"])
    ap.add_argument("--out", default="experiments/pilot_results.jsonl")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if "api" in args.models and not api_key:
        print("WARNING: OPENROUTER_API_KEY not set in environment; skipping API model.")
        args.models = [m for m in args.models if m != "api"]

    all_items = []
    for mod in args.modalities:
        items = MODALITY_BUILDERS[mod](args.n, seed=args.seed)
        print(f"{mod}: built {len(items)} items")
        all_items.extend(items)

    total_cost = 0.0
    n_parse_ok = {}
    n_total = {}

    with open(args.out, "w") as out_f:
        for item in all_items:
            for model_key in args.models:
                key = (item["modality"], model_key)
                n_total[key] = n_total.get(key, 0) + 1
                t0 = time.time()
                try:
                    if model_key == "local":
                        chain_text = run_local_qwen(item["image_path"], item["prompt"])
                        cost = 0.0
                    else:
                        chain_text, cost = run_api_openrouter(item["image_path"], item["prompt"], api_key)
                        cost = cost or 0.0
                        total_cost += cost
                except Exception as e:
                    chain_text = f"__ERROR__: {e}"
                    cost = 0.0
                elapsed = time.time() - t0

                parsed = parse_chain(chain_text)
                if parsed is not None:
                    n_parse_ok[key] = n_parse_ok.get(key, 0) + 1

                record = {
                    "modality": item["modality"],
                    "model": model_key,
                    "source_file": item["source_file"],
                    "chain_text": chain_text,
                    "parsed": parsed,
                    "cost_usd": cost,
                    "elapsed_s": elapsed,
                }
                out_f.write(json.dumps(record) + "\n")
                out_f.flush()
                print(
                    f"[{item['modality']}/{model_key}] parsed={parsed} "
                    f"cost=${cost:.6f} t={elapsed:.1f}s"
                )

    print("\n" + "=" * 70)
    print("PILOT summary: parser-extraction success rate per (modality, model)")
    print("=" * 70)
    for key in sorted(n_total.keys()):
        ok = n_parse_ok.get(key, 0)
        tot = n_total[key]
        print(f"  {key[0]:10s} / {key[1]:6s}: {ok}/{tot} ({100*ok/tot:.0f}%) chains exposed a parseable claim")
    print(f"\nTotal API cost this run: ${total_cost:.4f}")
    print(f"Results written to: {args.out}")


if __name__ == "__main__":
    main()
