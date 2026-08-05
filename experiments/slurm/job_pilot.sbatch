#!/bin/bash -l
# Runs the PILOT (feasibility check, not a paper number) on the 3 image
# modalities (XRD/SEM/spectrum) using the local Qwen2.5-VL-7B model + the
# OpenRouter API model. Needs OPENROUTER_API_KEY only -- no Materials
# Project key needed (DFT modalities are excluded by pilot.py's own default).
#
# Prerequisites:
#   - MATPCR_DATA_ROOT set, conda env set up (setup_env.sh already run).
#   - opXRD/NFFA/RRUFF staged (stage_opxrd.sh / stage_nffa.sh / stage_rruff.sh).
#   - .env with the OpenRouter key present at the repo root (source
#     load_secrets.sh before submitting, or let this script do it -- see below).
#
# Submit: sbatch experiments/slurm/job_pilot.sbatch [n_per_modality]

#SBATCH -J matpcr_pilot
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

N="${1:-15}"
OUT="experiments/pilot_results_panther_$(date +%Y%m%d).jsonl"

echo "=== Running pilot: n=$N per modality, xrd/sem/spectrum, local+api ==="
echo "=== Results -> $OUT ==="

python3 experiments/pilot.py \
  --n "$N" \
  --modalities xrd sem spectrum \
  --models local api \
  --out "$OUT"

echo "=== Done. Check parse-success rate per (modality, model) in $OUT before"
echo "    trusting the pipeline is working end-to-end on this new host. ==="
