#!/bin/bash -l
# Re-collect DFT magnetism Half-B fired cases after the Gemini prompt fix
# (experiments/pilot_dft.py's magnetism prompt now asks for short,
# non-hedging reasoning + a raised token budget, fixing a truncation bug
# that disproportionately hit ambiguous rare-earth/transition-metal
# formulas). Confirms the fix actually raises Gemini's magnetism parse
# rate before treating any new magnetism numbers as final.
#
# Prerequisites:
#   - MATPCR_DATA_ROOT set, conda env activated, MP_API_KEY exported.
#   - experiments/slurm/stage_materials_project.sh already run (needs
#     $MATPCR_DATA_ROOT/mp_data/mp_reference_batch.jsonl to exist).
#   - An OpenRouter API key available to pilot.py/pilot_dft.py's
#     run_api_openrouter (check how the repo's existing scripts read it --
#     historically an env var / a .env file OUTSIDE the repo, never committed).
#
# This is a CPU/API-bound job (Gemini is a remote API call for its half; the
# local half uses Qwen2.5-VL-7B, which DOES need the GPU) -- kept on
# gpu-A100 rather than gpu-H200 since it's a short job, not one that needs
# H200's extra memory.
#
# Submit: sbatch experiments/slurm/job_magnetism_recollect.sbatch

#SBATCH -J matpcr_magnetism_recollect
#SBATCH -o logs/%x_%j.out
#SBATCH -e logs/%x_%j.err
#SBATCH -p gpu-A100
#SBATCH --gres=gpu:1
#SBATCH -c 4
#SBATCH --mem=16000
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

OUT="experiments/halfB_dft_fired_cases_magnetism_refix_$(date +%Y%m%d).jsonl"

echo "=== Re-collecting magnetism Half-B fired cases (target >=100) ==="
echo "=== Results -> $OUT ==="

python3 experiments/halfB_collect_dft.py \
  --claim_types magnetism \
  --target 100 \
  --out "$OUT"

echo "=== Done. Compare this run's parse-success rate against the original"
echo "    (pre-fix) collection to confirm the truncation fix actually helped,"
echo "    before regenerating the magnetism review page from $OUT. ==="
