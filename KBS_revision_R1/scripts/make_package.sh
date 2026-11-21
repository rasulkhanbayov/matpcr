#!/bin/bash
# Assemble KBS_revision_R1/submission_package/ from the builds (run scripts/build_all.sh first).
#   source_flat/      LaTeX source for Editorial Manager: one flat folder, clean (no highlighting)
#   pdf/              highlighted, clean and latexdiff manuscript PDFs + SI PDF
#   figures/          every figure as a separate PNG (>= 300 dpi)
#   word/             response to reviewers, cover letter, highlights, CRediT, declaration, author agreement
set -euo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
P=$R/submission_package
rm -rf "$P"; mkdir -p "$P"/{source_flat,pdf,figures,word}

# regenerate the response (fills any newly computed values) and the Word files
PANDOC="${PANDOC:-/export/home/rakh90100/miniconda3/envs/matpcr_tex/bin/pandoc}"
(cd "$R/response"; python3 make_response.py
 for f in response_to_reviewers cover_letter highlights credit_author_statement declaration_of_interest author_agreement; do "$PANDOC" "$f.md" -o "$f.docx"; done
 export PATH="${TEXBIN:-/export/home/rakh90100/tools/texlive/bin/x86_64-linux}:$PATH"
 pdflatex -interaction=nonstopmode response_to_reviewers.tex >/dev/null 2>&1; pdflatex -interaction=nonstopmode response_to_reviewers.tex >/dev/null 2>&1
 grep -q "^!" response_to_reviewers.log && { echo "ERROR in response"; grep -n "^!" response_to_reviewers.log | head -3; exit 1; } || true)

S=$P/source_flat
{ echo '\def\cleanbuild{1}% final version: revision highlighting off'; cat "$R/revised/submission/matpcr_snjnl.tex"; } > "$S/matpcr_snjnl.tex"
cp "$R"/revised/submission/{matpcr_refs.bib,sn-jnl.cls,sn-nature.bst,matpcr_SI.tex,si_tables_generated.tex} "$S"/
cp "$R/build/clean/matpcr_snjnl_clean.bbl" "$S/matpcr_snjnl.bbl"
cp "$R"/revised/figures/oracle_examples/new_*_oracle_figure.pdf "$S"/
cp "$R/revised/figures/fig_precision_funnel.pdf" "$S"/

cp "$R/build/highlighted/matpcr_snjnl.pdf"            "$P/pdf/matpcr_revised_highlighted.pdf"
cp "$R/build/clean/matpcr_snjnl_clean.pdf"            "$P/pdf/matpcr_revised_clean.pdf"
cp "$R/build/latexdiff/matpcr_snjnl_latexdiff.pdf"    "$P/pdf/matpcr_original_vs_revised_latexdiff.pdf"
cp "$R/build/highlighted/matpcr_SI.pdf"               "$P/pdf/matpcr_SI_revised.pdf"
cp "$R"/figures_300dpi/Figure_*.png "$P/figures/"
cp "$R"/response/{response_to_reviewers,cover_letter,highlights,credit_author_statement,declaration_of_interest,author_agreement}.docx "$P/word/"
cp "$R/response/response_to_reviewers.tex" "$P/word/"
cp "$R/response/response_to_reviewers.pdf" "$P/pdf/"

# verify the flat source compiles on its own
T=$(mktemp -d); cp "$S"/* "$T"/
(cd "$T"; export PATH="${TEXBIN:-/export/home/rakh90100/tools/texlive/bin/x86_64-linux}:$PATH"
 for i in 1 2 3 4; do if [ $i = 2 ]; then bibtex matpcr_snjnl >/dev/null 2>&1 || true; else pdflatex -interaction=nonstopmode matpcr_snjnl.tex >/dev/null 2>&1 || true; fi; done
 pdflatex -interaction=nonstopmode matpcr_SI.tex >/dev/null 2>&1 || true; pdflatex -interaction=nonstopmode matpcr_SI.tex >/dev/null 2>&1 || true
 for j in matpcr_snjnl matpcr_SI; do
   if grep -q "^!" $j.log; then echo "flat source: ERROR in $j"; grep -n "^!" $j.log | head -3; exit 1; fi
   echo "flat source $j: $(grep 'Output written' $j.log | sed 's/.*(\(.*\)).*/\1/'), undefined refs/cites: $(grep -c 'undefined' $j.log || true)"
 done)
rm -rf "$T"
find "$P" -type f | sed "s#$P/##" | sort
