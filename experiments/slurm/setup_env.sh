#!/bin/bash
# One-time environment setup for MatPCR on Panther.
#
# IMPORTANT (per the Panther guide): run this on one of the shared physical
# servers (10.4.64.27 or 10.4.64.28), NOT on panther-login.qcri.org -- the
# login node auto-kills long-running user processes (including a long conda
# install), and is meant only for submitting/viewing Slurm jobs. Both share
# the same home directory as the compute nodes, so an env set up there is
# immediately usable in sbatch scripts.
#
# Usage:
#   ssh <user>@10.4.64.27          # or .28
#   cd /export/home/<user>/matpcr   # this repo, same path as on the login node
#   bash experiments/slurm/setup_env.sh
#
# Safe to re-run -- skips steps that already succeeded.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONDA_ROOT="${MATPCR_CONDA_ROOT:-$HOME/miniconda3}"
ENV_NAME="${MATPCR_CONDA_ENV:-matpcr}"

echo "=== MatPCR Panther environment setup ==="
echo "Repo root:   $REPO_ROOT"
echo "Conda root:  $CONDA_ROOT"
echo "Env name:    $ENV_NAME"
echo

# --- 1. Install Miniconda to the shared home if not already present -------
if [ ! -d "$CONDA_ROOT" ]; then
  echo "--- Installing Miniconda to $CONDA_ROOT ---"
  curl -fsSL -o /tmp/miniconda_installer.sh \
    https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
  bash /tmp/miniconda_installer.sh -b -p "$CONDA_ROOT"
  rm -f /tmp/miniconda_installer.sh
  echo "Miniconda installed. You must log out and log back in once (per the"
  echo "Panther guide) before it's picked up in new shells/Slurm jobs."
else
  echo "--- Miniconda already present at $CONDA_ROOT, skipping install ---"
fi

source "$CONDA_ROOT/etc/profile.d/conda.sh"

# --- 2. Create the main env -------------------------------------------------
if ! conda env list | grep -q "^$ENV_NAME "; then
  echo "--- Creating conda env '$ENV_NAME' (Python 3.10, matches the version"
  echo "    this project was validated on) ---"
  conda create -y -n "$ENV_NAME" python=3.10
else
  echo "--- Conda env '$ENV_NAME' already exists, skipping create ---"
fi

conda activate "$ENV_NAME"

echo "--- Installing tesseract (system binary, not pip-installable) ---"
# pytesseract (in requirements-main.txt) is only a Python wrapper -- it needs
# the actual `tesseract` binary on PATH. There's no sudo/apt access as a
# regular cluster user, so install via conda-forge instead. Confirmed as a
# real gap on Panther (2026-08-05): sem_scalebar_extractor.py's OCR call
# crashed every SEM-modality item with TesseractNotFoundError, which only
# surfaced partway through a real sweep (XRD ran fine first) rather than at
# setup time.
conda install -y -c conda-forge tesseract

echo "--- Installing main requirements ---"
pip install -r "$REPO_ROOT/experiments/slurm/requirements-main.txt" \
  --extra-index-url https://download.pytorch.org/whl/cu121

echo
echo "=== Main env ready. Activate with: ==="
echo "    source $CONDA_ROOT/etc/profile.d/conda.sh && conda activate $ENV_NAME"
echo
echo "=== MatterChat baseline (optional, separate venv) ==="
echo "Only needed if re-running the MatterChat domain-evaluee baseline"
echo "(Phase 2 item 16). Skipped by default since it's a heavier, separate"
echo "install with old pinned deps that conflict with the main env. To set"
echo "it up:"
echo "    python3 -m venv \$HOME/matpcr_matterchat_venv"
echo "    source \$HOME/matpcr_matterchat_venv/bin/activate"
echo "    pip install -r $REPO_ROOT/experiments/slurm/requirements-matterchat.txt"
echo
echo "=== Materials Project API key ==="
echo "Not set up by this script (it's a secret, generated per-user at"
echo "next-gen.materialsproject.org). Export it before running any DFT-oracle"
echo "script: export MP_API_KEY=..."
echo "Store it in a file OUTSIDE the repo (e.g. \$HOME/.matpcr_secrets/.env),"
echo "never commit it."
echo
echo "=== Next step ==="
echo "Set MATPCR_DATA_ROOT (see experiments/slurm/README.md) and run the"
echo "data-staging scripts in experiments/slurm/stage_*.sh before any real job."
