#!/bin/bash
# Source this (don't execute it directly) to export API keys from .env files
# into the current shell, for use by any of the run_*.sbatch / job_*.sbatch
# scripts or interactive sessions.
#
# Usage:
#   source experiments/slurm/load_secrets.sh
#
# Reads:
#   <repo_root>/.env               -- bare OpenRouter key, ONE line, no "KEY="
#                                      prefix (this is the format the repo's
#                                      own .env is in -- confirmed directly).
#   ~/.matpcr_secrets/mp_api_key    -- bare Materials Project key, same format,
#                                      OPTIONAL (only needed for the 3
#                                      DFT-grounded oracles / halfB_collect_dft.py
#                                      / mp_fetch_reference_data.py).
#
# Never commit either file. <repo_root>/.env is already gitignored
# (confirmed: .gitignore lines 3-5 cover .env, *.env, **/secrets/**).

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [ -f "$REPO_ROOT/.env" ]; then
  export OPENROUTER_API_KEY="$(tr -d '[:space:]' < "$REPO_ROOT/.env")"
  echo "Loaded OPENROUTER_API_KEY from $REPO_ROOT/.env (${#OPENROUTER_API_KEY} chars)"
else
  echo "WARNING: $REPO_ROOT/.env not found -- OPENROUTER_API_KEY not set." >&2
  echo "API-model calls (Gemini/GPT-4o/Claude/etc via OpenRouter) will be skipped." >&2
fi

MP_KEY_FILE="$HOME/.matpcr_secrets/mp_api_key"
if [ -f "$MP_KEY_FILE" ]; then
  export MP_API_KEY="$(tr -d '[:space:]' < "$MP_KEY_FILE")"
  echo "Loaded MP_API_KEY from $MP_KEY_FILE (${#MP_API_KEY} chars)"
else
  echo "NOTE: $MP_KEY_FILE not found -- MP_API_KEY not set." >&2
  echo "DFT-grounded oracle scripts (stability/metallicity/magnetism) need this;" >&2
  echo "everything else (XRD/SEM/spectrum) works fine without it." >&2
  echo "To set it up: mkdir -p ~/.matpcr_secrets && echo '<your-mp-key>' > $MP_KEY_FILE && chmod 600 $MP_KEY_FILE" >&2
fi
