#!/bin/bash -l
# Runs Experiment 2 (main PCR sweep, fills the paper's Table 1) restricted
# to the 3 non-DFT modalities (xrd/sem/spectrum) -- these need only
# OPENROUTER_API_KEY, no Materials Project key. Run job_exp2_dft.sbatch
# separately once an MP_API_KEY is available for the stability/metallicity/
# magnetism columns.
#
# Prerequisites:
#   - MATPCR_DATA_ROOT set, conda env set up.
#   - opXRD/NFFA/RRUFF staged.
#   - .env with the OpenRouter key present at the repo root.
#
# Submit: sbatch experiments/slurm/job_exp2_pcr_sweep.sbatch [n_per_cell] [n_seeds]
#
# Cost/runtime note: the original 8-model x 6-modality x 3-seed sweep cost
# ~$5-13 in API calls total (CLAUDE.md SS13/SS19/SS20) -- this 3-modality
# subset will cost proportionally less. --resume is used so a killed/requeued
# job doesn't re-spend budget on cells already completed.

#SBATCH -J matpcr_exp2_sweep
#SBATCH -o logs/%x_%j.out
#SBATCH -e logs/%x_%j.err
#SBATCH -p gpu-A100
#SBATCH --gres=gpu:1
#SBATCH -c 8
#SBATCH --mem=32000
#SBATCH -A a100_hbku
#SBATCH -q a100_hbku_qos

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

module load cuda12.1/toolkit/12.1.1
source "${MATPCR_CONDA_ROOT:-$HOME/miniconda3}/etc/profile.d/conda.sh"
conda activate "${MATPCR_CONDA_ENV:-matpcr}"
source experiments/slurm/load_secrets.sh

MATPCR_DATA_ROOT="${MATPCR_DATA_ROOT:-/export/home/rakh90100/matpcr_data}"
export MATPCR_DATA_ROOT

nvidia-smi

N="${1:-30}"
SEEDS="${2:-3}"
# Fixed filename (not date-stamped) -- a date-stamped name broke --resume
# across a real multi-day run (2026-08-05): resubmitting on a later date
# would silently generate a NEW empty output file instead of resuming the
# previous day's partially-completed one. Override with a 3rd arg if you
# genuinely want a fresh file.
OUT="${3:-experiments/exp2_results_panther.jsonl}"

echo "=== Experiment 2 PCR sweep: n=$N/cell, seeds=$SEEDS, modalities=xrd,sem,spectrum ==="
echo "=== Results -> $OUT ==="

python3 experiments/exp2_pcr_sweep.py \
  --n "$N" \
  --seeds "$SEEDS" \
  --modalities xrd sem spectrum \
  --out "$OUT" \
  --resume

echo "=== Done. Aggregate with: python3 experiments/exp2_aggregate.py"
echo "    (edit its RESULTS_PATH to point at $OUT, or copy over the default) ==="
