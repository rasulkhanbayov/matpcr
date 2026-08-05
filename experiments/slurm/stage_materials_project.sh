#!/bin/bash
# Pull real Materials Project reference data (energy_above_hull, band_gap,
# total_magnetization, nsites) for the 3 DFT-grounded oracles.
# Requires a MP_API_KEY -- generate a new one at next-gen.materialsproject.org
# (the old key lived only in the wiped /tmp/matpcr_secrets/.env on the
# previous host and is not recoverable).
#
# Usage:
#   export MATPCR_DATA_ROOT=/export/home/<user>/matpcr_data
#   export MP_API_KEY=...          # from a file OUTSIDE the repo, never commit
#   bash experiments/slurm/stage_materials_project.sh [n_materials]
#
# This does NOT need a GPU -- run it on the shared physical server or the
# login node's Slurm-submission shell, not inside a gpu-A100/gpu-H200 job.

set -euo pipefail

MATPCR_DATA_ROOT="${MATPCR_DATA_ROOT:?Set MATPCR_DATA_ROOT first, see experiments/slurm/README.md}"
MP_API_KEY="${MP_API_KEY:?Set MP_API_KEY first (generate at next-gen.materialsproject.org)}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
N="${1:-3000}"

mkdir -p "$MATPCR_DATA_ROOT/mp_data"

echo "=== Pulling $N materials from Materials Project ==="
cd "$REPO_ROOT"
python3 experiments/mp_fetch_reference_data.py --n "$N" --retrieval_date "$(date +%Y-%m-%d)"

echo "=== Done. Provenance recorded to \$MATPCR_DATA_ROOT/mp_data/mp_provenance.json ==="
echo "Per Dr. Mustafa's review: describe these as STANDARDIZED COMPUTATIONAL"
echo "REFERENCES in any writeup, not experimental ground truth."
