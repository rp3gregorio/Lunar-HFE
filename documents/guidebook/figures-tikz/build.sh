#!/usr/bin/env bash
# Rebuild one or all standalone TikZ figures.
#
# Usage:
#   ./build.sh                 # rebuild every *_standalone.tex
#   ./build.sh eqnflow         # rebuild just eqnflow_standalone.tex
#   ./build.sh pipeline        # rebuild just pipeline_standalone.tex
#
# Output PDFs land next to the .tex files (one tightly-cropped page each).
set -euo pipefail
cd "$(dirname "$0")"

build_one() {
  local name="$1"
  local tex="${name}_standalone.tex"
  [[ -f "$tex" ]] || { echo "no such figure: $name"; return 1; }
  echo ">> $tex"
  pdflatex -interaction=nonstopmode -halt-on-error "$tex" >/dev/null
  rm -f "${name}_standalone".{aux,log,out}
  echo "   ok -> ${name}_standalone.pdf"
}

if [[ $# -eq 0 ]]; then
  for f in *_standalone.tex; do
    build_one "${f%_standalone.tex}"
  done
else
  for name in "$@"; do
    build_one "$name"
  done
fi
