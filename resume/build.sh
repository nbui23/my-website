#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Building all resume variants..."

pdflatex -interaction=nonstopmode -jobname="Norman_Bui_Resume"      general.tex
pdflatex -interaction=nonstopmode -jobname="Norman_Bui_Resume_SWE"  swe.tex
pdflatex -interaction=nonstopmode -jobname="Norman_Bui_Resume_AIML" aiml.tex
pdflatex -interaction=nonstopmode -jobname="Norman_Bui_Resume_QA"   qa.tex

rm -f *.aux *.log *.out *.synctex.gz

echo ""
echo "Done. PDFs generated:"
ls -1 *.pdf
