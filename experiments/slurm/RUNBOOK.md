# Panther run commands — ordered, copy-pasteable

Everything you actually type on Panther, in order. Each step names the file
it's built on. See `README.md` in this directory for the "why" behind each
choice; this file is just the command sequence.

**Current status (2026-08-01): Panther access confirmed, OpenRouter key
available (repo root `.env`, gitignored). No Materials Project key yet** —
so Tier 1 (XRD/SEM/spectrum, everything except the 3 DFT-grounded oracles)
can run now; Tier 2 (stability/metallicity/magnetism) is blocked until an
MP key is generated at next-gen.materialsproject.org. Sections below are
marked Tier 1 / Tier 2 accordingly.

---

## 0. One-time: access and connection

```
# On the QCRI VPN or HBKU-QCRI network:
ssh <username>@panther-login.qcri.org
```

## 1. One-time: environment setup

Run on a **shared physical server**, not the login node (login node kills
long-running processes):

```
ssh <username>@10.4.64.27
cd /export/home/<username>          # your shared home
git clone <matpcr-repo-url> matpcr  # or: cd matpcr if already present
cd matpcr

bash experiments/slurm/setup_env.sh
```

This installs Miniconda (if not already present) to `$HOME/miniconda3`,
creates a `matpcr` conda env (Python 3.10), and installs
`experiments/slurm/requirements-main.txt`. **Log out and back in once** after
first-time Miniconda install, then re-run `setup_env.sh` if the env didn't
activate cleanly.

Set your data root once, in your shell profile so it persists:

```
echo 'export MATPCR_DATA_ROOT=/export/home/<username>/matpcr_data' >> ~/.bashrc
source ~/.bashrc
mkdir -p "$MATPCR_DATA_ROOT" logs
```

**API keys — how this repo actually stores them (confirmed 2026-08-01):**
- OpenRouter key: a single bare line (no `KEY=` prefix) in `.env` at the
  repo root. Already gitignored — confirm it made it over when you copied
  the repo to Panther (it will NOT be in a `git clone`, since it's
  untracked; copy it separately, e.g. `scp .env <user>@panther-login...:matpcr/.env`).
- Materials Project key (once you have one): store it the same bare-line
  way, at `~/.matpcr_secrets/mp_api_key` (NOT inside the repo):
  ```
  mkdir -p ~/.matpcr_secrets
  echo '<your-mp-key>' > ~/.matpcr_secrets/mp_api_key
  chmod 600 ~/.matpcr_secrets/mp_api_key
  ```

Every job script below sources `experiments/slurm/load_secrets.sh`, which
reads both files in this exact format and exports `OPENROUTER_API_KEY` /
`MP_API_KEY`. You don't need to export them by hand.

(Optional, only if re-running the MatterChat baseline — Phase 2 item 16):

```
python3 -m venv ~/matpcr_matterchat_venv
source ~/matpcr_matterchat_venv/bin/activate
pip install -r experiments/slurm/requirements-matterchat.txt
deactivate
```

## 2. One-time: smoke test both partitions

Confirm account/QOS/module access works before anything real:

```
cd /export/home/<username>/matpcr
mkdir -p logs
sbatch -p gpu-A100 -A a100_hbku -q a100_hbku_qos \
  experiments/slurm/smoketest.sbatch cuda12.1/toolkit/12.1.1

sbatch -p gpu-H200 -A h200_hbku -x crirdchpxd005 -q h200_hbku_qos \
  experiments/slurm/smoketest.sbatch cuda12.6/toolkit/12.6.2

squeue -u <username>
cat logs/matpcr_smoketest_*.out
```

Expect a clean `nvidia-smi` table, a Python version line, and
`Smoke test OK on <hostname>` in each log.

## 3. One-time: stage the datasets (Tier 1 — needs no API key)

Run on the shared physical server (network-bound, not GPU-bound):

```
export MATPCR_DATA_ROOT=/export/home/<username>/matpcr_data   # if not in ~/.bashrc already
source ~/miniconda3/etc/profile.d/conda.sh && conda activate matpcr

bash experiments/slurm/stage_opxrd.sh
bash experiments/slurm/stage_nffa.sh
bash experiments/slurm/stage_rruff.sh
```

Each script prints a verified count at the end — cross-check against
CLAUDE.md's documented totals (opXRD: 92,552 patterns; NFFA: 18,424 images;
RRUFF excellent_unoriented: 11,415 files) before trusting the data.

**Materials Project (Tier 2 — SKIP until you have an MP_API_KEY):**
```
mkdir -p ~/.matpcr_secrets
echo '<your-mp-key>' > ~/.matpcr_secrets/mp_api_key
chmod 600 ~/.matpcr_secrets/mp_api_key
source experiments/slurm/load_secrets.sh
bash experiments/slurm/stage_materials_project.sh 3000
```

## 4. Verify everything end-to-end before any real run

```
python3 matpcr_metrics.py    # the numpy-only smoke test — should pass cleanly
```

## 5. Tier 1 jobs — runnable now with just the OpenRouter key

### 5a. Pilot (feasibility check, ~15-30 min, cheap)

Confirms the pipeline actually works on this new host before spending real
budget on a full sweep:

```
cd /export/home/<username>/matpcr
sbatch experiments/slurm/job_pilot.sbatch 15
squeue -u <username>
tail -f logs/matpcr_pilot_*.out
```

Check the parse-success rate per (modality, model) in
`experiments/pilot_results_panther_<date>.jsonl` once done — should look
similar to CLAUDE.md §10b's original 100%/93%/100% pattern for
local/API x XRD/SEM/spectrum. A big drop means something broke in the
data-staging or env setup, not the underlying method.

### 5b. Experiment 2 — main PCR sweep, XRD/SEM/spectrum only

```
sbatch experiments/slurm/job_exp2_pcr_sweep.sbatch 30 3
```
(args: n_per_cell, n_seeds — defaults shown match the original paper run)

```
squeue -u <username>
tail -f logs/matpcr_exp2_sweep_*.out
```

Uses `--resume`, so if the job dies partway (network hiccup, node issue),
just resubmit the same command — it skips cells already ≥50% complete in
the output file rather than re-spending API budget.

### 5c. Verifier retrain with pinned seed (no API key needed at all)

Trains directly on the already-collected, committed
`experiments/exp5_verifier_dataset.jsonl` — no new model calls:

```
sbatch experiments/slurm/job_verifier_retrain.sbatch
tail -f logs/matpcr_verifier_retrain_*.out
```

When done, compare against the existing committed results:
```
python3 -c "
import json
old = [json.loads(l) for l in open('experiments/exp5_results.jsonl')]
new = [json.loads(l) for l in open('experiments/exp5_results_panther_$(date +%Y%m%d).jsonl')]
for o, n in zip(old, new):
    print(o['run_name'], 'old AUC=%.3f' % o['roc_auc'], 'new AUC=%.3f' % n['roc_auc'])
"
```
AUCs should match closely (small drift from CUDA nondeterminism is expected
and was already observed once in this project — CLAUDE.md §16's rerun note
— but should NOT differ qualitatively). If they match, the weights under
`$MATPCR_DATA_ROOT/verifier_weights_<date>/` are the release candidate.

## 6. Tier 2 jobs — BLOCKED until a Materials Project key exists

### 6a. Experiment 2 — DFT-grounded columns (stability/metallicity/magnetism)

```
# after stage_materials_project.sh has been run successfully:
sbatch experiments/slurm/job_exp2_dft.sbatch 30 3
```

### 6b. Gemini magnetism prompt fix — re-collect and check parse rate

```
sbatch experiments/slurm/job_magnetism_recollect.sbatch
tail -f logs/matpcr_magnetism_recollect_*.out
```

Check whether this run's Gemini magnetism parse-success rate improved over
the original (pre-fix) collection before regenerating the review page or
reporting any new magnetism number — the manual re-review is still the
standing blocking item regardless (CLAUDE.md §20/§19).

## 7. Anything else — build your own job

Use the generic templates for any other script in `experiments/`:

```
sbatch experiments/slurm/run_a100.sbatch experiments/some_script.py --some-flag
sbatch experiments/slurm/run_h200.sbatch experiments/some_script.py --some-flag
```

They don't source `load_secrets.sh` automatically — add
`source experiments/slurm/load_secrets.sh` after the `conda activate` line
if the script needs an API key.

Remember: don't default to re-running everything just because the hardware
is faster — see the "What to actually run here" section of `README.md` for
what's worth spending compute/API budget on right now.

## 8. Monitoring / cleanup

```
squeue -u <username>                    # what's running/queued
scancel <job-id>                        # cancel a specific job
cd /export/infrazone/panther-nvidia-smi && touch <node-name>   # manual nvidia-smi check on a node (don't script this — the guide asks you not to)
```
