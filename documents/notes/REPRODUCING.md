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
cd Lunar-HFE
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
python code/pipeline/fetch_diviner.py
```

This downloads ~310 MB of public PDS data (only the two lat-bands needed
for Apollo 15 and 17 surface-T closure). Files land under
`code/data/diviner/gcp/` and are reused on subsequent runs.

The Apollo HFE record is bundled directly under `code/data/apollo/`; no
download is needed for it.

## Step 4 — Run the test suite

```bash
pytest -q
```

All tests should pass in under a minute. If they don't, stop and check
your Python/numpy versions before proceeding.

## Step 5 — Run the notebooks

Open Jupyter Lab and run the seven notebooks in order:

```bash
jupyter lab code/notebooks/
```

| Notebook | Wall time | Produces |
|---|---|---|
| `00_setup.ipynb` | <1 min | sanity check, data integrity |
| `01_methods.ipynb` | 2-3 min | Figs 1-3 & 5, Table 1 |
| `02_anchor_method.ipynb` | 2-3 min | the flux-anchored solver, explained + animated |
| `03_retrieval.ipynb` | ~5 min (fast); ~90-100 min full | per-site K_d sweep + bootstrap + Q_b sensitivity; writes `code/results/kd_retrieval_results.json`. Heavy auxiliary sweeps for Table 3 are opt-in (`RUN_AUXILIARY = True`). |
| `04_results.ipynb` | 3-5 min | Figs 6-9 & 12, Tables 2-3 |
| `05_discussion.ipynb` | 2-3 min | Figs 10-11, Tables 4-5 |
| `06_performance.ipynb` | 2-3 min | the solver kernel in C++ (agreement + speedup), then the K_d retrieval run live (tqdm progress) |

End-to-end on the fast path: about **15 minutes**. The canonical
auxiliary JSONs already ship with the repo, so the slow auxiliary
sweeps (~90-100 min) are rarely needed unless you change inputs.

Each notebook is **idempotent**: re-running it overwrites the same
output files. Notebooks read the canonical JSON results from
`code/results/`, so once `03_retrieval.ipynb` has run once, subsequent
notebooks can be re-run independently for figure tuning.

## Step 5b — The joint (albedo, K_d) retrieval: the paper's headline

Since v1.2-jgr the paper's values come from fitting the effective albedo and
K_d together to three in-situ measurements (sensor temperatures, measured
surface mean, Langseth et al. 1976 annual-wave diffusivity). These scripts
take the albedo explicitly, so they do not depend on the config albedo:

```bash
python code/pipeline/compute/compute_joint_albedo_fit.py          # ~25 min (5 workers): Table 1, Figs 3-5
python code/pipeline/compute/compute_joint_valley.py              # seconds: Table 2 (what the diffusivity adds)
python code/pipeline/compute/compute_joint_block_bootstrap.py     # ~1 min: probe-grouped bootstrap (Text S8)
python code/pipeline/compute/compute_joint_fit_sensitivities.py   # ~90 min (5 workers): Tables 3-4, Fig 6
python code/pipeline/compute/compute_joint_fit_checks.py          # ~1 min, after the sensitivities
python code/pipeline/compute/compute_joint_diviner.py             # ~3 min: Text S10
python code/pipeline/figures/make_joint_figures.py                # Figs 3-6, S4, S5
```

`compute_joint_albedo_fit.py --reuse` re-analyses the committed grid
(`code/results/joint_albedo_fit_cache.npz`) in seconds; the sensitivity
script accepts `--reuse` once its own cache exists.

## Step 6 — Compile the manuscript

```bash
cd documents/jgr/letter
latexmk -pdf letter.tex
```

The compiled `letter.pdf` should match the submitted manuscript
byte-for-byte modulo figure regeneration timestamps.

## Verification

The repository ships with the canonical JSON results. To verify the
headline joint retrieval
([`code/results/joint_albedo_fit.json`](../../code/results/joint_albedo_fit.json)):

```bash
python -c "
import json, math
r = json.loads(open('code/results/joint_albedo_fit.json').read())['sites']
for s, kd, A in (('A15', 4.87, 0.136), ('A17', 5.89, 0.137)):
    b = r[s]['with_diffusivity']['best']
    print(s, 'K_d* =', round(b['kd_star_mW'], 2), 'mW m^-1 K^-1, A* =', round(b['A'], 4))
    assert math.isclose(b['kd_star_mW'], kd, abs_tol=0.01) and math.isclose(b['A'], A, abs_tol=0.0006)
print('Headline values verified.')
"
```

`code/results/kd_retrieval_results.json` holds the temperature-only
retrieval at the fixed (fitted) config albedos, a diagnostic since v1.2-jgr.

## Troubleshooting

**`pip install -e` fails on macOS with SciPy build errors**: install via
`pip install --only-binary=:all: -e .[dev]` to force the prebuilt wheels.

**SPICE kernel download fails**: the SPICE ephemeris files are fetched
on demand by `code/src/lunar/ephem.py`. If your network blocks the JPL/NAIF
mirror, set `SPICE_KERNEL_DIR` to a local directory containing the
DE440 kernel and the NAIF lunar/earth PCK.

**Diviner download SSL error**: `code/pipeline/fetch_diviner.py` retries with
SSL verification disabled (PDS data is public, this is safe).

**LaTeX missing font / package**: install a complete TeX distribution
(TeX Live 2023+ or MacTeX). Partial installations like BasicTeX will
fail on Times New Roman + microtype + lineno.

## Citing

See [`CITATION.cff`](../../CITATION.cff) and the bottom of the main
[README](../../README.md).
