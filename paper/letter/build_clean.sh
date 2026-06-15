#!/usr/bin/env bash
# ---------------------------------------------------------------------
# One-command CLEAN (flattened) build of the letter for printing.
#
# Produces letter_clean.pdf -- the markup-free version (no green
# additions, no struck-out old text, no notes).
#
# Usage:   ./build_clean.sh        (from paper/letter/)
# Requires: a LaTeX install (latexmk + pdflatex + bibtex).
# ---------------------------------------------------------------------
set -e
cd "$(dirname "$0")"

echo "Building clean, printable letter_clean.pdf ..."
latexmk -pdf -interaction=nonstopmode letter_clean.tex

echo
echo "Done -> $(pwd)/letter_clean.pdf"
