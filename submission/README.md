# Difference of Lunar Regolith Thermal Conductivity *K*<sub>d</sub> at the Apollo 15 and 17 Heat-Flow Boreholes

Self-contained manuscript package for the JGR:Planets letter (Gregorio et al.),
retrieving the deep regolith thermal conductivity *K*<sub>d</sub> per site at the
Apollo 15 and 17 heat-flow boreholes.

**Everything needed to compile the letter PDF is in this folder** — no external
paths, no code required. The figures are pre-rendered PDFs; the Python/C++ code
that generates them and runs the retrieval lives in the main repository (link
below).

## Authors
Ramon III P. Gregorio, Richard Larsson, Takayoshi Yamada, Yasuko Kasai.
Correspondence: Yasuko Kasai — `kasai.y.aa@m.titech.ac.jp`.

## Contents
| File | What it is |
|------|-----------|
| `letter.tex` | Manuscript source (main file) |
| `letter_clean.tex` | Flattened build — compile this for the markup-free, submission-ready version |
| `supporting_information.tex` | Supporting Information source |
| `references.bib` | BibTeX bibliography |
| `letter.bbl`, `letter_clean.bbl` | Pre-built bibliography (compiles even without a BibTeX run) |
| `build_clean.sh` | One-command clean build (`./build_clean.sh`) |
| `figures/*.pdf` | All 13 figures, pre-rendered |
| `letter.pdf` | The compiled letter — open this to read without building |
| `letter_clean.pdf` | The compiled clean/flattened letter |
| `supporting_information.pdf` | The compiled Supporting Information |

## Build
Requires a LaTeX installation (TeX Live / MacTeX) with `latexmk`, `pdflatex`, and `bibtex`.

```bash
latexmk -pdf letter.tex          # working version (with change marks, if any)
latexmk -pdf letter_clean.tex    # clean, submission-ready version
```

On **Overleaf**: upload this folder, set the main document to `letter.tex`
(or `letter_clean.tex`), and click Recompile.

## Full project
The complete thermal-model code, data pipeline, figure generators, and
reproduction instructions are in the main repository:
<https://github.com/rp3gregorio/Lunar-HFE>
