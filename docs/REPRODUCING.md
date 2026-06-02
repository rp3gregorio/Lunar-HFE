# Reproducing the paper

This document walks through every step from a fresh clone to a compiled
PDF identical to the submitted manuscript.

## Prerequisites

- **Python 3.10+** (`python3 --version`)
- **Git** (any recent version)
- **LaTeX** (for the final paper compile only — TeX Live 2023+ or MacTeX)
- ~1 GB free disk space (code + data)
- ~1 hour wall time for full reproduction on a recent laptop

## Step 1 — Clone

```bash
git clone https://github.com/rp3gregorio/Lunar-HFE.git
cd apollo-hfe-kd-retrieval
```

## Step 2 — Install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

`pip install -e ".[dev]"` installs the `lunar` package in editable mode
plus the development extras (`pytest`, `jupyterlab`, `matplotlib`).

If you want the *exact* dependency versions used to produce the
published figures, use the lock file instead:

```bash
pip install -r requirements-lock.txt
pip install -e .
```

## Step 3 — Fetch Diviner GCP data

```bash
python scripts/fetch_diviner.py
```

This downloads ~310 MB of public PDS data (only the two lat-bands needed
for Apollo 15 and 17 surface-T closure). Files land under
`data/diviner/gcp/` and are reused on subsequent runs.

The Apollo HFE record is bundled directly under `data/apollo/`; no
download is needed for it.

## Step 4 — Run the test suite

```bash
pytest -q
```

All tests should pass in under a minute. If they don't, stop and check
your Python/numpy versions before proceeding.

## Step 5 — Run the notebooks

Open Jupyter Lab and run the five notebooks in order:

```bash
jupyter lab notebooks/
```

| Notebook | Wall time | Produces |
|---|---|---|
| `00_setup.ipynb` | <1 min | sanity check, data integrity |
| `01_methods.ipynb` | 2-3 min | Figs 1-4, Table 1 |
| `02_retrieval.ipynb` | ~5 min (fast); ~60 min full | per-site K_d sweep + bootstrap + Q_b sensitivity; writes `output/kd_retrieval_results.json`. Heavy auxiliary sweeps for Table 3 are opt-in (`RUN_AUXILIARY = True`). |
| `03_results.ipynb` | 3-5 min | Figs 5-9, Tables 2-3 |
| `04_discussion.ipynb` | 2-3 min | Figs 10-11, Table 4 |

End-to-end on the fast path: about **15 minutes**. The canonical
auxiliary JSONs already ship with the repo, so the slow auxiliary
sweeps (~60 min) are rarely needed unless you change inputs.

Each notebook is **idempotent**: re-running it overwrites the same
output files. Notebooks read the canonical JSON results from
`output/`, so once `02_retrieval.ipynb` has run once, subsequent
notebooks can be re-run independently for figure tuning.

## Step 6 — Compile the manuscript

```bash
cd paper/letter
latexmk -pdf letter.tex
```

The compiled `letter.pdf` should match the submitted manuscript
byte-for-byte modulo figure regeneration timestamps.

## Verification

The repository ships with the canonical JSON results
([`output/kd_retrieval_results.json`](../output/kd_retrieval_results.json)). To
verify that your run reproduces them:

```bash
python -c "
import json, math
shipped = json.loads(open('output/kd_retrieval_results.json').read())
print('A15 K_d* =', shipped['A15']['kd_star'] * 1e3, 'mW m^-1 K^-1')
print('A17 K_d* =', shipped['A17']['kd_star'] * 1e3, 'mW m^-1 K^-1')
assert math.isclose(shipped['A15']['kd_star'] * 1e3, 4.86, abs_tol=0.01)
assert math.isclose(shipped['A17']['kd_star'] * 1e3, 11.23, abs_tol=0.01)
print('Headline values verified.')
"
```

## Troubleshooting

**`pip install -e` fails on macOS with SciPy build errors**: install via
`pip install --only-binary=:all: -e .[dev]` to force the prebuilt wheels.

**SPICE kernel download fails**: the SPICE ephemeris files are fetched
on demand by `lunar/ephem.py`. If your network blocks the JPL/NAIF
mirror, set `SPICE_KERNEL_DIR` to a local directory containing the
DE440 kernel and the NAIF lunar/earth PCK.

**Diviner download SSL error**: `scripts/fetch_diviner.py` retries with
SSL verification disabled (PDS data is public, this is safe).

**LaTeX missing font / package**: install a complete TeX distribution
(TeX Live 2023+ or MacTeX). Partial installations like BasicTeX will
fail on Times New Roman + microtype + lineno.

## Citing

See [`CITATION.cff`](../CITATION.cff) and the bottom of the main
[README](../README.md).
