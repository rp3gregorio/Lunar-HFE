# Reproducing the paper

From a fresh copy of the repository to every number and figure of the letter
and its Supporting Information.

## Prerequisites

- **Python 3.10+** and **Git**
- About 1 GB of free disk space (more with the optional Diviner data)
- For SI Figure S2 only: **pdflatex** (TeX Live or MacTeX)
- Time: minutes to check the stored results; about 6 hours of wall time for
  the full analysis on a six-core laptop

## Step 1 — Get the code

```bash
git clone https://github.com/rp3gregorio/Lunar-HFE.git
cd Lunar-HFE
git checkout v1.5-jgr          # the version the paper names
```

## Step 2 — Install

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev,mcmc]"
```

This installs the `lunar` package (the physics) in editable mode, with the
notebook tools, the tests and the MCMC sampler. For the exact versions used for
the paper, use the lock file instead:

```bash
pip install -r requirements-lock.txt
pip install -e .
```

## Step 3 — Optional downloads

The Apollo record, the SPICE kernels and the site-map crops are in the
repository. Two public data sets are not, and are needed only to recompute the
steps that use them:

```bash
python code/pipeline/fetch_diviner.py     # ~310 MB: Diviner comparison (SI Table S11, SI Fig S5)
mkdir -p code/data/lola
curl -L -o code/data/lola/ldem_16.img https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_16.img   # 33 MB: SI Fig S1
```

Notebook `00_setup` can do both (`DOWNLOAD = True`).

## Step 4 — Run the tests

```bash
make test
```

The unit tests of the physics code pass in under a minute. If they do not,
check the Python and NumPy versions before going on.

## Step 5 — Run the analysis

**In the notebooks** (recommended):

```bash
jupyter lab code/notebooks/
```

Run `00_setup` to `05_annual_wave_and_posterior` in order. The first code cell
of each sets `MODE`: `"show"` reads the stored results (minutes), `"quick"`
runs the short steps and the fast form of the long ones (about 30 min),
`"full"` runs everything from scratch (about 6 h). Each notebook compares its
results with the numbers printed in the paper. `code/notebooks/README.md`
lists the script behind every step.

**Without Jupyter**, the same scripts in the same order:

```bash
make retrieve aux          # 24 steps, about 6 h; each prints its progress
```

The order matters: the joint fit (`compute_joint_albedo_fit.py`) reuses the
outputs of the steps before it, the error budget needs the solver
certification (`certify_joint_numerics.py`), and the likelihood-ratio tests
come after the error budget and the χ sweep. The `Makefile` lists every step
with its runtime and what it gives in the paper.

Three long steps have fast forms that re-analyse stored model runs:

```bash
python code/pipeline/compute/compute_joint_albedo_fit.py --reuse        # seconds (the grid is in git)
python code/pipeline/compute/compute_joint_fit_sensitivities.py --reuse # seconds, once its cache exists locally
python code/pipeline/compute/compute_joint_mcmc.py --sample             # ~1 min (the grid is in git)
```

## Step 6 — The figures

```bash
make figures
```

This writes the letter's Figures 1–6 and SI Figures S1–S4 and S6 to
`figures/`. SI Figure S5 is written by `compute_joint_diviner.py` (it needs
the Diviner data); SI Figure S1 needs the LOLA map and SI Figure S2 needs
pdflatex. The notebooks show every figure.

## Verification

The repository ships every result. After a full run,

```bash
git diff --stat code/results
```

shows which results files changed; for an unchanged run only run times and
the recorded git commit differ. To check the headline values directly:

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

`code/results/README.md` maps every results file to the tables and figures
it feeds.

## Troubleshooting

**`pip install -e` fails on macOS with SciPy build errors**: install the
prebuilt wheels with `pip install --only-binary=:all: -e ".[dev,mcmc]"`.

**Diviner download SSL error**: `fetch_diviner.py` retries with SSL
verification disabled (PDS data are public).

**A notebook step stops with "needs ... which is not downloaded"**: run the
download of Step 3, or keep the mode at `"show"` / `"quick"`, which use the
stored result.

**SI Figure S2 is not made**: install pdflatex (a full TeX Live or MacTeX).

## Citing

See [`CITATION.cff`](../../CITATION.cff) and the main [README](../../README.md).
