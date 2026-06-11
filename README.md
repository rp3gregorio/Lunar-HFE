# apollo-hfe-kd-retrieval

Per-site retrieval of the lunar deep-regolith thermal conductivity $K_d$ at the
Apollo 15 and 17 Heat-Flow Experiment (HFE) boreholes from the restored
1971–1977 record.

This is the reproducibility repository for the paper:

> Gregorio (2026), *Estimates of Lunar Regolith Thermal Conductivity $K_d$
> at Respective Apollo 15 and 17 Heat-Flow Boreholes*, submitted to **JGR:
> Planets**.

## What it does

We retrieve the deep-regolith thermal conductivity $K_d$ separately at each
Apollo HFE borehole by holding the Hayne (2017) $K(T,z)$ functional form fixed
and sweeping $K_d$ against the deep-sensor RMSE. The retrieval yields

- $K_{d,\text{A15}}^{*} = 4.86^{+1.12}_{-0.54}$ mW m⁻¹ K⁻¹
- $K_{d,\text{A17}}^{*} = 11.23^{+8.12}_{-0.77}$ mW m⁻¹ K⁻¹

(1σ non-parametric bootstrap, $N_\text{boot}=1500$, conditional on canonical
basal heat flux $Q_b$).

These per-site values reduce the deep-sensor RMSE by ~3–10× relative to the
published global $K_d = 3.4$ and supply the deep-$T(z)$ boundary condition
needed by sub-surface radiative-transfer retrievals.

## Reproducing the paper

The full reproduction recipe is in [`docs/REPRODUCING.md`](docs/REPRODUCING.md).
Short version:

```bash
git clone https://github.com/rp3gregorio/Lunar-HFE.git
cd Lunar-HFE
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python scripts/fetch_diviner.py     # ~310 MB from PDS-Geosciences
jupyter lab notebooks/
```

Then run the 5 notebooks in order:

| Notebook | Produces |
|---|---|
| `00_setup.ipynb` | Dependency check, data integrity check |
| `01_methods.ipynb` | Figs 1–3, Table 1 (parameters) |
| `02_retrieval.ipynb` | Per-site $K_d^*$ retrieval, bootstrap CIs, error budget |
| `03_results.ipynb` | Figs 4–8 (mean-T, $K_d$ sweep, bootstrap, thermal profiles, Diviner closure), Tables 2–3 |
| `04_discussion.ipynb` | Figs 9–10 (robustness, $\alpha$-sweep), Table 4 |

Each notebook is idempotent: re-running it overwrites the corresponding
figures and any JSON it produces in `output/`. The canonical retrieval JSON
([`output/kd_retrieval_results.json`](output/kd_retrieval_results.json)) is committed for
direct verification.

## Repository layout

```
Lunar-HFE/
├── lunar/                  # 1-D heat solver + conductivity models
├── scripts/
│   ├── pipeline/           # batch retrieval + sensitivity sweeps
│   └── figures/            # matplotlib figure generators (callable from CLI)
├── notebooks/              # 5 reproduction notebooks (run in order)
├── data/
│   ├── apollo/             # HFE 1971–1977 record (Nagihara 2018, bundled)
│   ├── diviner/            # GCP cache (fetched on demand)
│   └── spice/              # SPICE kernels (DE440, lunar frames)
├── output/                 # canonical JSON results
├── paper/
│   ├── letter/             # LaTeX source + figures + compiled PDF
│   └── appendix/           # supplemental figures
├── tests/                  # pytest suite (run with `pytest`)
└── docs/                   # REPRODUCING.md, FLAG_REPORT.md, code review
```

## Citing this work

If you use this code or data, please cite both the paper and the repository:

```bibtex
@article{gregorio2026,
  author  = {Gregorio, R.~P.},
  title   = {Estimates of Lunar Regolith Thermal Conductivity $K_d$
             at Respective Apollo 15 and 17 Heat-Flow Boreholes},
  journal = {Journal of Geophysical Research: Planets},
  year    = {2026},
  doi     = {TBD}
}
```

`CITATION.cff` is provided for GitHub's automatic citation widget.

## Licenses

- **Code** (`lunar/`, `scripts/`, `tests/`, `notebooks/`): MIT License
  (see [`LICENSE`](LICENSE))
- **Paper text, figures, and tabular results** (`paper/`, `output/figures/`):
  Creative Commons Attribution 4.0 International (CC-BY-4.0)
  (see [`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0))
- **Bundled HFE data** (`data/apollo/`): public domain via NASA PDS-Geosciences
  (Nagihara et al. 2018 release)

## Contact

R. P. Gregorio · `rp3gregorio@gmail.com`
Kasai Laboratory, Institute of Science Tokyo
