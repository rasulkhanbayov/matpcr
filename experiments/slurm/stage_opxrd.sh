#!/bin/bash
# Fetch opXRD (real experimental powder XRD patterns, CC-BY-4.0) onto Panther.
# Source: Zenodo record 15298026 (confirmed correct/complete copy per
# CLAUDE.md 2026-07-04 -- an earlier copy from a different source was
# truncated, missing HKUST+LBNL entirely).
#
# Usage:
#   export MATPCR_DATA_ROOT=/export/home/<user>/matpcr_data   # or wherever
#   bash experiments/slurm/stage_opxrd.sh
#
# Run this on a shared physical server (10.4.64.27/28) or as a Slurm job with
# network access, NOT on the compute nodes mid-job -- it's a one-time ~few-GB
# download, not part of the hot path. The repo's pilot.py/exp*.py scripts
# read opXRD from <repo_root>/opxrd (a symlink into MATPCR_DATA_ROOT is fine).

set -euo pipefail

MATPCR_DATA_ROOT="${MATPCR_DATA_ROOT:?Set MATPCR_DATA_ROOT first, see experiments/slurm/README.md}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ZENODO_RECORD=15298026
DEST="$MATPCR_DATA_ROOT/opxrd"

mkdir -p "$DEST"
echo "=== Fetching opXRD file list from Zenodo record $ZENODO_RECORD ==="
curl -fsSL "https://zenodo.org/api/records/$ZENODO_RECORD" -o /tmp/opxrd_record.json

python3 - "$DEST" <<'PYEOF'
import hashlib, json, os, sys, urllib.request

dest = sys.argv[1]
with open("/tmp/opxrd_record.json") as f:
    record = json.load(f)

files = record.get("files", [])
if not files:
    sys.exit("No files found in Zenodo record metadata -- check the record ID is still correct.")

print(f"Found {len(files)} file(s) in the record.")


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


failures = []
for entry in files:
    url = entry["links"]["self"]
    name = entry["key"]
    # Zenodo's checksum field is "md5:<hex>"
    expected_md5 = entry.get("checksum", "").replace("md5:", "")
    out_path = os.path.join(dest, name)

    if os.path.exists(out_path):
        if expected_md5:
            print(f"  {name}: already present, verifying checksum ...")
            actual = md5_of(out_path)
            if actual == expected_md5:
                print(f"  {name}: checksum OK, skipping re-download")
                continue
            print(f"  {name}: CHECKSUM MISMATCH (expected {expected_md5}, got {actual}) "
                  f"-- likely a partial/corrupt file from an earlier interrupted download "
                  f"(e.g. killed by the login node's watchdog). Re-downloading.")
            os.remove(out_path)
        else:
            print(f"  {name}: already present (no checksum published), skipping re-download")
            continue

    print(f"  downloading {name} ...")
    urllib.request.urlretrieve(url, out_path)

    if expected_md5:
        actual = md5_of(out_path)
        if actual != expected_md5:
            print(f"  {name}: CHECKSUM MISMATCH after download (expected {expected_md5}, got {actual})")
            failures.append(name)
            continue
        print(f"  {name}: downloaded and checksum verified")
    else:
        print(f"  done: {out_path}")

if failures:
    sys.exit(f"Checksum mismatch after download on {len(failures)} file(s): {failures} "
              f"-- do not proceed until fixed (network issue or Zenodo record problem).")
PYEOF

echo "=== Extracting any archives ==="
cd "$DEST"
for f in *.zip; do
  [ -e "$f" ] || continue
  echo "Extracting $f ..."
  unzip -o -q "$f"
done
for f in *.tar.gz *.tgz; do
  [ -e "$f" ] || continue
  echo "Extracting $f ..."
  tar xzf "$f"
done

echo "=== Symlinking into repo (pilot.py/exp*.py expect <repo_root>/opxrd) ==="
ln -sfn "$DEST" "$REPO_ROOT/opxrd"

N_FILES=$(find "$DEST" -iname 'pattern_*.json' | wc -l)
echo "=== Done. $N_FILES pattern_*.json files found under $DEST ==="
echo "CLAUDE.md's verified count was 92,552 -- if this number is far off,"
echo "re-check the Zenodo record contents before trusting the data."
