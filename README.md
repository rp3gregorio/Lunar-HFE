# apollo-hfe-kd-retrieval

Per-site retrieval of the lunar deep-regolith thermal conductivity $K_d$ at the
Apollo 15 and 17 Heat-Flow Experiment (HFE) boreholes from the restored
1971–1977 record.

This is the reproducibility repository for the paper:

> Gregorio, Larsson, Yamada & Kasai (2026), *Difference of Lunar Regolith
> Thermal Conductivity $K_d$ at the Apollo 15 and 17 Heat-Flow Boreholes*,
> submitted to **JGR: Planets**.

## What it does

We retrieve the deep-regolith thermal conductivity $K_d$ separately at each
Apollo HFE borehole by holding the Hayne (2017) $K(T,z)$ functional form fixed
and sweeping $K_d$ against the deep-sensor RMSE. The retrieval yields

- $K_{d,\text{A15}}^{*} = 4.58^{+1.33}_{-0.28}$ mW m⁻¹ K⁻¹
- $K_{d,\text{A17}}^{*} = 8.12^{+0.49}_{-0.61}$ mW m⁻¹ K⁻¹

(1σ non-parametric bootstrap, $N_\text{boot}=1500$, conditional on the
published basal heat fluxes; inter-site contrast 3.31, 95% CI [0.37, 4.58],
p ≈ 0.011). The forward model is solved to a certified periodic steady
state (see `src/lunar/equilibrium.py` and `docs/notes/FLAG_REPORT.md`).

These per-site values reduce the meter-scale-sensor RMSE relative to the
published global $K_d = 3.4$ (halving it at Apollo 17) and supply the
meter-scale $T(z)$ boundary condition needed by sub-surface
radiative-transfer retrievals.

## Reproducing the paper

The full reproduction recipe is in [`docs/REPRODUCING.md`](docs/REPRODUCING.md).
There is a `Makefile` with one-word entry points — run `make help` to list
them. Short version:

```bash
git clone https://github.com/rp3gregorio/Lunar-HFE.git
cd Lunar-HFE
python3 -m venv .venv && source .venv/bin/activate
make install                 # editable install of the `lunar` package + dev deps
python pipeline/fetch_diviner.py  # ~310 MB from PDS-Geosciences (one-time)

make retrieve                # core retrieval + bootstrap  -> results/*.json
make aux                     # all sensitivity sweeps, model selection, MCMC, closure
make figures                 # regenerate every figure (paper + guidebook) -> results/figures/
make paper                   # compile all PDFs
# or simply:  make all
```

Prefer notebooks? `jupyter lab notebooks/` and run the five in order
(they call the same pipeline). Prefer scripts? Each file under
`pipeline/compute/` and `pipeline/figures/` runs standalone.

### How the code is organised (start here)

All configuration and the physics engine live in the **`src/lunar/` package**;
the **`pipeline/`** scripts are thin command-line drivers that call it. There is
exactly one definition of everything:

| Where | What |
|---|---|
| `src/lunar/config.py` | **single source of truth** — site table (`SITES`), grid, Hayne bundle, solver + sweep settings |
| `src/lunar/constants.py` | cited physical constants |
| `src/lunar/properties.py` | conductivity / density / specific-heat models |
| `src/lunar/grid.py`, `solver.py`, `equilibrium.py` | the 1-D heat-equation engine |
| `src/lunar/plotting/style.py` | shared figure palette + layout helpers |
| `pipeline/compute/` | retrieval, bootstrap, sensitivity sweeps, MCMC (write `results/*.json`) |
| `pipeline/figures/` | figure generators; `pipeline/make_all_figures.py` runs them all |

New to the code? Read the full developer guidebook in
[`docs/guidebook/`](docs/guidebook/) (`guidebook.tex`; build the PDF with
`make paper`) — physics derivations from first principles, module reference,
data flow, and worked recipes.

Then run the 5 notebooks in order:

| Notebook | Produces |
|---|---|
| `00_setup.ipynb` | Dependency check, data integrity check |
| `01_methods.ipynb` | Figs 1–3, Table 1 (parameters) |
| `02_retrieval.ipynb` | Per-site $K_d^*$ retrieval, bootstrap CIs, error budget |
| `03_results.ipynb` | Figs 4–8 (mean-T, $K_d$ sweep, bootstrap, thermal profiles, Diviner closure), Tables 2–3 |
| `04_discussion.ipynb` | Figs 9–10 (robustness, $\alpha$-sweep), Table 4 |

Optional: [`equilibrium_demo.ipynb`](notebooks/equilibrium_demo.ipynb) is a
standalone demonstration (not part of the reproduction set) that a long
brute-force spin-up converges onto the fast flux-anchored solver — it
parallelises the independent runs across CPU cores.

Each notebook is idempotent: re-running it overwrites the corresponding
figures and any JSON it produces in `results/`. The canonical retrieval JSON
([`results/kd_retrieval_results.json`](results/kd_retrieval_results.json)) is committed for
direct verification.

## Repository layout

```
Lunar-HFE/
├── src/lunar/              # 1-D heat solver + conductivity models (the engine)
├── pipeline/
│   ├── compute/            # batch retrieval + sensitivity sweeps (write results/*.json)
│   └── figures/            # matplotlib figure generators (write results/figures/)
├── notebooks/              # 5 reproduction notebooks (run in order)
├── data/
│   ├── apollo/             # HFE 1971–1977 record (Nagihara 2018, bundled)
│   ├── diviner/            # GCP cache (fetched on demand)
│   └── spice/              # SPICE kernels (DE440, lunar frames)
├── results/                # canonical JSON results + figures/ (single source of truth)
├── paper/
│   └── letter/             # the manuscript: LaTeX source + compiled PDF (figures/ -> results/figures)
├── tests/                  # pytest suite (run with `pytest`)
└── docs/
    ├── guidebook/          # guidebook.tex/pdf — full teaching + developer guide
    ├── notes/              # REPRODUCING.md, FLAG_REPORT.md, NUMBA_VS_CPP_*.md
    └── slides/             # progress deck + assets
```

## Citing this work

If you use this code or data, please cite both the paper and the repository:

```bibtex
@article{gregorio2026,
  author  = {Gregorio, R.~P. and Larsson, R. and Yamada, T. and Kasai, Y.},
  title   = {Difference of Lunar Regolith Thermal Conductivity $K_d$
             at the Apollo 15 and 17 Heat-Flow Boreholes},
  journal = {Journal of Geophysical Research: Planets},
  year    = {2026},
  doi     = {TBD}
}
```

`CITATION.cff` is provided for GitHub's automatic citation widget.

## Licenses

- **Code** (`src/lunar/`, `pipeline/`, `tests/`, `notebooks/`): MIT License
  (see [`LICENSE`](LICENSE))
- **Paper text, figures, and tabular results** (`paper/`, `results/figures/`):
  Creative Commons Attribution 4.0 International (CC-BY-4.0)
  (see [`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0))
- **Bundled HFE data** (`data/apollo/`): public domain via NASA PDS-Geosciences
  (Nagihara et al. 2018 release)

## Contact

R. P. Gregorio · `rp3gregorio@gmail.com`
Kasai Laboratory, Institute of Science Tokyo
