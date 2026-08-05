#!/bin/bash -l
# Retrain the released verifier (Experiment 5) with a pinned training seed,
# so the released artifact is bit-reproducible. Addresses audit blocking
# item: the original weights lived only on the old host's /ephemeral (wiped)
# and are unrecoverable in their exact original form; this produces a fresh,
# reproducible copy suitable for public release.
#
# Prerequisites:
#   - MATPCR_DATA_ROOT set (see experiments/slurm/README.md) and the conda
#     env from setup_env.sh activated.
#   - experiments/exp5_verifier_dataset.jsonl present (already in the repo --
#     no new model calls needed to build it, per CLAUDE.md SS16).
#
# Submit: sbatch experiments/slurm/job_verifier_retrain.sbatch
# Runtime: all 13 splits (1 random + 6 held-out-modality + 6 held-out-constraint)
# took well under an hour on the old A100 per CLAUDE.md SS16 -- comfortably
# inside gpu-A100's 3-day cap.

#SBATCH -J matpcr_verifier_retrain
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
source experiments/slurm/load_secrets.sh 2>/dev/null || true  # not needed for this job, sourced for consistency

MATPCR_DATA_ROOT="${MATPCR_DATA_ROOT:-/export/home/rakh90100/matpcr_data}"
export MATPCR_DATA_ROOT
export MATPCR_WEIGHTS_ROOT="$MATPCR_DATA_ROOT/verifier_weights_$(date +%Y%m%d)"

nvidia-smi

TRAIN_SEED="${MATPCR_TRAIN_SEED:-0}"
OUT="experiments/exp5_results_panther_$(date +%Y%m%d).jsonl"

echo "=== Retraining verifier, all 13 splits, train_seed=$TRAIN_SEED ==="
echo "=== Weights -> $MATPCR_WEIGHTS_ROOT ==="
echo "=== Results -> $OUT ==="

python3 experiments/exp5_train_verifier.py \
  --split all \
  --train_seed "$TRAIN_SEED" \
  --out "$OUT"

echo "=== Done. Compare $OUT against experiments/exp5_results.jsonl (existing,"
echo "    committed results) to confirm the retrain reproduces the reported"
echo "    numbers before treating \$MATPCR_WEIGHTS_ROOT as the release candidate. ==="
