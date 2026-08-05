#!/bin/bash -l
# Runs Experiment 2's DFT-grounded columns (stability/metallicity/magnetism)
# -- the counterpart to job_exp2_pcr_sweep.sbatch's geometric modalities.
# BLOCKED until MP_API_KEY is obtained (next-gen.materialsproject.org) and
# experiments/slurm/stage_materials_project.sh has been run.
#
# Submit: sbatch experiments/slurm/job_exp2_dft.sbatch [n_per_cell] [n_seeds]

#SBATCH -J matpcr_exp2_dft
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
: "${MP_API_KEY:?MP_API_KEY not set -- see experiments/slurm/load_secrets.sh for setup instructions. This job is BLOCKED until a Materials Project key is obtained.}"
export MATPCR_DATA_ROOT

nvidia-smi

N="${1:-30}"
SEEDS="${2:-3}"
OUT="experiments/exp2_dft_results_panther_$(date +%Y%m%d).jsonl"

echo "=== Experiment 2 DFT columns: n=$N/cell, seeds=$SEEDS, modalities=stability,metallicity,magnetism ==="
echo "=== Results -> $OUT ==="
echo "=== NOTE: report these as provisional -- Mustafa's DFT Half-B sign-off is still pending. ==="

python3 experiments/exp2_pcr_sweep.py \
  --n "$N" \
  --seeds "$SEEDS" \
  --modalities stability metallicity magnetism \
  --out "$OUT" \
  --resume

echo "=== Done. Aggregate with experiments/exp2_aggregate.py, and flag every"
echo "    reported number as provisional per the standing OVERRIDE note. ==="
