# Canva poster build

Regenerates `../aogs_poster_canva.pptx` — the A0-portrait, Canva-importable
redesign of the AOGS poster (native text boxes + PNG figures, fully editable
after import; drag the .pptx onto canva.com to import).

1. `.venv/bin/python layout_gen.py`  — renders figs/ from the vector PDFs,
   emits layout.json + preview.png (geometry QA; asserts no overlaps)
2. `python3 build_pptx.py` — layout.json → ../aogs_poster_canva.pptx

Numbers trace to poster_numbers.tex; edit text in layout_gen.py only.
