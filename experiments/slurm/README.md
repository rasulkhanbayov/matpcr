# Panther A100/H200 migration notes

**For the actual copy-pasteable command sequence, see `RUNBOOK.md` in this
directory.** This file explains the "why" behind each step; RUNBOOK.md is
the ordered "what to type."

Setup steps and templates for running MatPCR experiments on QCRI's Panther
Slurm cluster (`panther-login.qcri.org`), which has A100 (80GB) and H200
(141GB) GPUs in addition to the P100 (16GB) work has run on so far. See
"End Users Guide - Panther..." PDF at the repo root for the full reference;
this file only covers what's specific to this project.

None of the existing model-calling code (`pilot.py`, `pilot_dft.py`,
`exp5_train_verifier.py`) has P100-specific tuning (no reduced batch size,
no hardcoded 16GB memory assumptions) — it should run unmodified here, just
faster and with headroom for larger local models if that's ever wanted.

**Status (2026-08-01): Panther access confirmed. OpenRouter key available
(repo root `.env`, gitignored, bare-key format). No Materials Project key
yet** — Tier 1 work (XRD/SEM/spectrum, verifier retrain) can run now; Tier 2
work (the 3 DFT-grounded oracles) is blocked until an MP key is generated.
See `RUNBOOK.md` for the Tier 1/2 breakdown.

## One-time setup

1. **Access**: confirmed. Connect via the QCRI VPN or HBKU-QCRI network:
   `ssh <user>@panther-login.qcri.org`.
2. **Data location**: do NOT put opXRD (92,552 files) / NFFA-EUROPE (18,424
   images) / RRUFF on the regular home directory — that's exactly the
   "thousands of small files" case the Panther guide warns against. Set
   `MATPCR_DATA_ROOT` to somewhere on business-group shared storage, then run
   `stage_opxrd.sh` / `stage_nffa.sh` / `stage_rruff.sh` /
   `stage_materials_project.sh` (this directory) to fetch each dataset fresh
   — `/ephemeral/matpcr` (the old P100 host's data root) no longer exists,
   so this is a fresh pull, not a migration of existing files. For
   `/scratch` (3TB NVMe, high IOPS) staging at job start/end for hot-path
   reads during a running job, see `RUNBOOK.md`.
3. **Python env**: install Anaconda3 to the shared home
   (`/home/local/QCRI/<user>`, same as `/export/home/<user>`) via one of the
   shared physical servers (`10.4.64.27`/`10.4.64.28`), NOT the Panther login
   node (which auto-kills long-running user processes, including a
   long-running pip/conda install). Once installed there, it's visible from
   Slurm compute nodes without extra steps.
4. **Fragile pins — DONE**: `requirements-main.txt` includes `mp-api` +
   `emmet-core==0.85.1` (the newer emmet-core release candidates import
   `NotRequired` from `typing`, Python-3.11+-only — this pin avoids that on
   Python 3.10). `requirements-matterchat.txt` has the MatterChat isolated
   venv's pins (Mistral-7B-Instruct-v0.3 + CHGNet checkpoint versions from
   CLAUDE.md §20 item 16). Both installed by `setup_env.sh`.
5. **API keys**: OpenRouter key goes in `.env` at the repo root (bare key,
   one line, no `KEY=` prefix — already gitignored; copy it to Panther
   separately since `git clone` won't bring an untracked file). Materials
   Project key (once obtained) goes at `~/.matpcr_secrets/mp_api_key`, same
   bare format, outside the repo. `experiments/slurm/load_secrets.sh`
   sources both correctly and exports `OPENROUTER_API_KEY`/`MP_API_KEY` --
   every `job_*.sbatch` script in this directory already sources it.
5. **Smoke test** (do this before anything real):
   ```
   mkdir -p logs
   sbatch -p gpu-A100 -A a100_hbku -q a100_hbku_qos \
     experiments/slurm/smoketest.sbatch cuda12.1/toolkit/12.1.1
   sbatch -p gpu-H200 -A h200_hbku -x crirdchpxd005 -q h200_hbku_qos \
     experiments/slurm/smoketest.sbatch cuda12.6/toolkit/12.6.2
   ```
   Check `squeue` for correct account/QOS, then `logs/matpcr_smoketest_<jobid>.out`
   for a clean `nvidia-smi` + `python3 --version` + the OK line.

## Submitting real jobs

**Concrete, ready-to-run jobs** (see `RUNBOOK.md` for the full sequence):

| Script | Tier | Needs | What it does |
|---|---|---|---|
| `job_pilot.sbatch` | 1 | OpenRouter key | Feasibility check on XRD/SEM/spectrum, local+API |
| `job_exp2_pcr_sweep.sbatch` | 1 | OpenRouter key | Main PCR sweep, XRD/SEM/spectrum columns |
| `job_verifier_retrain.sbatch` | 1 | neither (uses committed data) | Retrains the released verifier, pinned seed |
| `job_exp2_dft.sbatch` | 2 | MP key | Main PCR sweep, DFT-grounded columns |
| `job_magnetism_recollect.sbatch` | 2 | MP key + OpenRouter | Re-collects magnetism cases after the prompt fix |

For anything else, use the generic templates directly:
```
sbatch experiments/slurm/run_a100.sbatch experiments/some_script.py --some-flag
sbatch experiments/slurm/run_h200.sbatch experiments/some_script.py --some-flag
```
Add `source experiments/slurm/load_secrets.sh` after the `conda activate`
line inside the template if the script you're running needs an API key.

Adjust `-c`/`--mem`/`--gres=gpu:N` in any script (or via `sbatch` CLI
overrides) to the job's actual needs — per the guide, requesting a full
node's memory while using one GPU on a multi-GPU node wastes the other GPUs
for everyone else.

Per-user caps: 4 concurrent jobs on `gpu-A100`, 4 on `gpu-H200` (16 with the
`H200_16GPUs`/`h200_qos_16_gpus` account+QOS, but that queue is preemptable
by normal H200 jobs after a 6-hour grace period — only use it for jobs that
can checkpoint, per the Panther guide's SIGUSR1/SIGTERM pattern).

Max runtime is 3 days on both partitions. None of this project's experiment
scripts have historically run anywhere near that long, so this is unlikely
to bite — but if a from-scratch full 6-family Half-A/Half-B + 8-model PCR
sweep is ever re-run end-to-end in one job, plan the extension-request email
in advance rather than discovering the cutoff mid-run.

## What to actually run here — don't default to "rerun everything"

Per project decision (2026-08-01): before spending Panther time, decide
which of these is actually wanted, rather than blindly re-running old
experiments just because faster hardware is available.

**Both code fixes below are DONE (2026-08-01) — only the actual Panther run
remains:**

- **Verifier retrain with pinned seeds** (addresses a real blocking item):
  `exp5_train_verifier.py`'s `train_and_eval()` now calls
  `transformers.set_seed(train_seed)` before model/LoRA init, and `main()`
  takes a `--train_seed` flag (default 0). Run via
  `experiments/slurm/job_verifier_retrain.sbatch` (see `RUNBOOK.md` §5c) to
  produce a bit-reproducible weights release candidate — the original
  weights were lost when `/ephemeral` was wiped and are unrecoverable in
  their original form.
- **Gemini magnetism-prompt truncation fix**: `pilot_dft.py`'s magnetism
  prompt now explicitly asks for short (2-4 sentence), non-hedging reasoning
  even on chemically ambiguous formulas (matching the wording that already
  fixed the earlier stability-prompt truncation), and
  `run_text_api_openrouter`'s `max_tokens` was raised 1000→1500 as
  defense-in-depth. Run via
  `experiments/slurm/job_magnetism_recollect.sbatch` (see `RUNBOOK.md` §6b)
  to re-collect and confirm the parse-success rate actually improved before
  reporting any new magnetism number.
- **GPT-4o's spectrum low-n anomaly**: NOT GPU-bound (GPT-4o is an API
  model) — Panther compute doesn't help here directly; keep this on the
  plain-investigation track.
- **Statistical work** (item-level clustering for p-values/CIs, Holm/BH
  multiple-comparisons correction): no GPU needed at all, can happen any time.
- **New/larger local models**: A100 (80GB) / H200 (141GB) newly enables
  comparing against a larger local base model than Qwen2.5-VL-7B/0.5B if the
  team wants that — not required by anything currently open, just a real new
  capability this hardware unlocks.

**All 15 scripts under `experiments/` that hardcoded `/ephemeral/matpcr/...`
paths (HF cache, MP data, NFFA/RRUFF roots, verifier weights) now read from
a `MATPCR_DATA_ROOT` env var instead** (defaulting to the old path so nothing
changes for anyone still on the old host) — set it before running anything,
see step 1 of `RUNBOOK.md`.

After any re-run, append results to CLAUDE.md in the same style as the
existing §13-20 entries (numbers + what changed + why), so the project's
documentation discipline carries forward onto the new hardware.
