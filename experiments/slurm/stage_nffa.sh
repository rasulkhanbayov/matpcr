#!/bin/bash
# Fetch NFFA-EUROPE SEM micrographs (real, CC-BY-4.0) onto Panther.
# Source: B2SHARE (EUDAT) record qtq9v-ys023, confirmed live via
# https://b2share.eudat.eu/api/records/qtq9v-ys023 (per CLAUDE.md 2026-07-05).
# 10 category .tar files, MD5-verified against the API's published checksums.
#
# Usage:
#   export MATPCR_DATA_ROOT=/export/home/<user>/matpcr_data
#   bash experiments/slurm/stage_nffa.sh

set -euo pipefail

MATPCR_DATA_ROOT="${MATPCR_DATA_ROOT:?Set MATPCR_DATA_ROOT first, see experiments/slurm/README.md}"
RECORD_ID="qtq9v-ys023"
DEST="$MATPCR_DATA_ROOT/nffa"

mkdir -p "$DEST/extracted"
echo "=== Fetching NFFA-EUROPE file list from B2SHARE record $RECORD_ID ==="
# File listings live at a SEPARATE endpoint from the main record (confirmed
# 2026-08-01 against the real API -- this is B2SHARE's v10 schema, which has
# no top-level "files" key on the record itself). Entries are under
# "entries", the download URL is links.content (not links.self -- that's
# just the file's metadata page), and checksum is already "md5:<hex>".
curl -fsSL "https://b2share.eudat.eu/api/records/$RECORD_ID/files" -o /tmp/nffa_files.json

python3 - "$DEST" <<'PYEOF'
import hashlib, json, os, sys, urllib.request

dest = sys.argv[1]
with open("/tmp/nffa_files.json") as f:
    listing = json.load(f)

entries = listing["entries"]
print(f"Found {len(entries)} file(s) in the record.")

failures = []
for entry in entries:
    name = entry["key"]
    url = entry["links"]["content"]
    expected_md5 = entry.get("checksum", "").replace("md5:", "")
    out_path = os.path.join(dest, name)

    if os.path.exists(out_path):
        print(f"  {name}: already downloaded, verifying checksum ...")
    else:
        print(f"  downloading {name} ...")
        urllib.request.urlretrieve(url, out_path)

    if expected_md5:
        h = hashlib.md5()
        with open(out_path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        actual = h.hexdigest()
        if actual != expected_md5:
            print(f"  MD5 MISMATCH for {name}: expected {expected_md5}, got {actual} "
                  f"-- likely a partial/corrupt file from an interrupted download. Re-downloading.")
            os.remove(out_path)
            print(f"  re-downloading {name} ...")
            urllib.request.urlretrieve(url, out_path)
            h2 = hashlib.md5()
            with open(out_path, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h2.update(chunk)
            actual2 = h2.hexdigest()
            if actual2 != expected_md5:
                print(f"  MD5 STILL MISMATCHED for {name} after re-download: expected {expected_md5}, got {actual2}")
                failures.append(name)
            else:
                print(f"  MD5 OK on retry: {name}")
        else:
            print(f"  MD5 OK: {name}")

if failures:
    sys.exit(f"Checksum mismatch on {len(failures)} file(s): {failures} -- do not proceed until fixed.")
print("All checksums verified.")
PYEOF

echo "=== Extracting .tar files ==="
cd "$DEST"
for f in *.tar; do
  [ -e "$f" ] || continue
  echo "Extracting $f into extracted/ ..."
  tar xf "$f" -C extracted/
done

echo "=== Done. Category counts under $DEST/extracted: ==="
for d in "$DEST"/extracted/*/; do
  cat=$(basename "$d")
  n=$(find "$d" -iname '*.jpg' -o -iname '*.jpeg' | wc -l)
  echo "  $cat: $n images"
done
echo "CLAUDE.md's verified totals: Biological 953, Films_Coated_Surface 308,"
echo "MEMS_devices_and_electrodes 4158, Nanowires 3656, Particles 3412,"
echo "Patterned_surface 3310, Porous_Sponge 171, Powder 895, Tips 1561,"
echo "Fibres 153 (18,424 total) -- cross-check against these before trusting."
echo
echo "Optional: once verified, delete the .tar files to save space:"
echo "  rm $DEST/*.tar"
