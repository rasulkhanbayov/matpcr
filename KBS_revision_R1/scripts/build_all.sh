#!/bin/bash
# Build every revision deliverable from KBS_revision_R1/revised/ :
#   build/highlighted/matpcr_snjnl.pdf        changes in blue (\rev)
#   build/clean/matpcr_snjnl_clean.pdf        same source, highlighting off
#   build/highlighted/matpcr_SI.pdf           supplementary information
#   build/latexdiff/matpcr_snjnl_latexdiff.pdf  original vs revised (cross-check)
#   figures_300dpi/Figure_N.png               every figure as a separate raster file (clean colours)
# Usage: bash scripts/build_all.sh   (needs pdflatex/bibtex/latexdiff on PATH or TEXBIN set; pdftoppm via POPPLER)
set -euo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEXBIN="${TEXBIN:-/export/home/rakh90100/tools/texlive/bin/x86_64-linux}"
POPPLER="${POPPLER:-/export/home/rakh90100/miniconda3/envs/matpcr_tex/bin}"
PY="${PY:-/export/home/rakh90100/miniconda3/envs/matpcr_rev/bin/python}"
export PATH="$TEXBIN:$PATH"

latex_build() {  # dir jobname texfile [preamble-def]
  local d=$1 job=$2 tex=$3 pre=${4:-}
  (cd "$d"
   for i in 1 2 3 4; do
     if [ $i = 2 ]; then bibtex "$job" >/dev/null 2>&1 || true
     else pdflatex -interaction=nonstopmode -jobname="$job" "${pre}\\input{$tex}" >/dev/null 2>&1 || true; fi
   done
   if grep -q "^!" "$job.log"; then echo "ERROR in $job:"; grep -n "^!" "$job.log" | head; exit 1; fi
   echo "$job: $(grep 'Output written' "$job.log" | sed 's/.*(\(.*\)).*/\1/')")
}

H=$R/build/highlighted; C=$R/build/clean; D=$R/build/latexdiff
for d in "$H" "$C" "$D"; do rm -rf "$d"; mkdir -p "$d"
  cp "$R"/revised/submission/{matpcr_snjnl.tex,matpcr_SI.tex,matpcr_refs.bib,sn-jnl.cls,sn-nature.bst,si_tables_generated.tex} "$d"/
  cp -r "$R"/revised/figures "$d"/; done

latex_build "$H" matpcr_snjnl matpcr_snjnl
latex_build "$C" matpcr_snjnl_clean matpcr_snjnl '\def\cleanbuild{1}'
(cd "$H"; pdflatex -interaction=nonstopmode matpcr_SI.tex >/dev/null 2>&1; pdflatex -interaction=nonstopmode matpcr_SI.tex >/dev/null 2>&1
 grep -q "^!" matpcr_SI.log && { echo "ERROR in SI"; exit 1; }; echo "matpcr_SI: $(grep 'Output written' matpcr_SI.log | sed 's/.*(\(.*\)).*/\1/')")

# normalize figure paths in the original (the revision switched to \graphicspath + bare names; not a content change)
sed -e 's#{figures/oracle_examples/new_#{new_#g' -e 's#\\usepackage{graphicx}#\\usepackage{graphicx}\n\\graphicspath{{figures/oracle_examples/}{figures/}{./}}#' \
  "$R/original/submission/matpcr_snjnl.tex" > "$D/original_pathnorm.tex"
latexdiff --type=CFONT --math-markup=whole \
  --config="PICTUREENV=(?:picture|DIFnomarkup|tikzpicture|tabular|algorithmic)[\w\d*@]*" \
  "$D/original_pathnorm.tex" "$R/revised/submission/matpcr_snjnl.tex" > "$D/matpcr_snjnl_latexdiff.tex" 2>/dev/null
latex_build "$D" matpcr_snjnl_latexdiff matpcr_snjnl_latexdiff

rm -rf "$R/figures_300dpi"
"$PY" "$R/scripts/export_figures.py" --tex "$R/revised/submission/matpcr_snjnl.tex" --out_dir "$R/figures_300dpi" \
  --pdflatex "$TEXBIN/pdflatex" --pdftoppm "$POPPLER/pdftoppm" --clean
