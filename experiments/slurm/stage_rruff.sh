#!/bin/bash
# Fetch RRUFF Raman spectra (excellent_unoriented grade -- highest quality
# tier used by this project) onto Panther.
# Source: https://www.rruff.net/zipped_data_files/raman/ (direct from
# rruff.net, not a Zenodo/HF mirror). NO formal license exists for this
# dataset (confirmed 2026-07-05) -- citation is mandatory, not optional
# (Lafuente, Downs, Yang & Stone 2015). Do not describe this as "CC-BY" or
# any specific SPDX license anywhere downstream.
#
# Usage:
#   export MATPCR_DATA_ROOT=/export/home/<user>/matpcr_data
#   bash experiments/slurm/stage_rruff.sh

set -euo pipefail

MATPCR_DATA_ROOT="${MATPCR_DATA_ROOT:?Set MATPCR_DATA_ROOT first, see experiments/slurm/README.md}"
DEST="$MATPCR_DATA_ROOT/rruff"
ZIP_NAME="excellent_unoriented.zip"
URL="https://www.rruff.net/zipped_data_files/raman/$ZIP_NAME"

mkdir -p "$DEST/extracted"

if [ -f "$DEST/$ZIP_NAME" ]; then
  echo "=== $ZIP_NAME already downloaded, skipping fetch ==="
else
  echo "=== Downloading $URL ==="
  curl -fL --retry 3 -o "$DEST/$ZIP_NAME" "$URL"
fi

echo "=== Extracting ==="
cd "$DEST"
unzip -o -q "$ZIP_NAME" -d extracted/

N_FILES=$(find extracted/ -type f | wc -l)
echo "=== Done. $N_FILES files extracted under $DEST/extracted ==="
echo "CLAUDE.md's verified count for this grade: 11,415 files (RAW + Processed"
echo "pairs). Files use Windows CRLF line endings -- harmless in Python"
echo "text-mode reads, confirmed working by this project's own oracle checks."
echo
echo "REMINDER: cite Lafuente, Downs, Yang & Stone (2015), 'The power of"
echo "databases: the RRUFF project', and any external contributor named in"
echo "individual records, per the standing no-formal-license finding."
