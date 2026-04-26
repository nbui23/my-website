#!/bin/bash
set -e
cd "$(dirname "$0")"

mkdir -p swe aiml qa

echo "Building all resume variants..."

pdflatex -interaction=nonstopmode -jobname="Norman_Bui_Resume" general.tex
pdflatex -interaction=nonstopmode -output-directory=swe  -jobname="Norman_Bui_Resume" swe.tex
pdflatex -interaction=nonstopmode -output-directory=aiml -jobname="Norman_Bui_Resume" aiml.tex
pdflatex -interaction=nonstopmode -output-directory=qa   -jobname="Norman_Bui_Resume" qa.tex

rm -f *.aux *.log *.out *.synctex.gz
rm -f swe/*.aux  swe/*.log  swe/*.out  swe/*.synctex.gz
rm -f aiml/*.aux aiml/*.log aiml/*.out aiml/*.synctex.gz
rm -f qa/*.aux   qa/*.log   qa/*.out   qa/*.synctex.gz

echo ""
echo "Done. PDFs:"
ls -1 Norman_Bui_Resume.pdf swe/Norman_Bui_Resume.pdf aiml/Norman_Bui_Resume.pdf qa/Norman_Bui_Resume.pdf
