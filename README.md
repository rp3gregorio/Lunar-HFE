# apollo-hfe-kd-retrieval

The deep-regolith thermal conductivity $K_d$ at the Apollo 15 and 17
Heat-Flow Experiment (HFE) boreholes, from the restored 1971–1977 record.

This is the reproducibility repository for the paper:

> Gregorio, Larsson, Kamada, Yamada, Kuroda & Kasai (2026), *Difference of the Lunar
> Regolith Thermal Conductivity $K_d$ at the Apollo 15 and 17 Heat-Flow Boreholes from
> Global Model Values*, in preparation for **JGR: Planets**.

## What it does

At each borehole the Hayne et al. (2017) conductivity model $K(T,z)$ is kept,
and its deep conductivity $K_d$ is fitted **together with the effective surface
albedo** to three measurements made there: the equilibrium temperatures of the
meter-scale sensors, the measured mean surface temperature, and the annual-wave
thermal diffusivity of Langseth et al. (1976). The joint fit
([`compute_joint_albedo_fit.py`](code/pipeline/compute/compute_joint_albedo_fit.py) →
[`joint_albedo_fit.json`](code/results/joint_albedo_fit.json)) gives

| | Apollo 15 | Apollo 17 |
|---|---|---|
| fitted albedo $A^*$ | 0.136 [0.128, 0.145] | 0.137 [0.135, 0.140] |
| $K_d^*$ (mW m⁻¹ K⁻¹) | 4.87 [4.29, 5.47] | 5.89 [5.26, 6.51] |

(95% bootstrap intervals.) The Moon-wide $K_d = 3.4$ of Hayne et al. (2017) is
rejected at both sites (likelihood-ratio $p = 9\times10^{-7}$ and $10^{-14}$;
[`likelihood_ratio.json`](code/results/likelihood_ratio.json)). The two sites
are consistent with one value of about 5–6.

## Running it: one notebook

[`code/notebooks/run_everything.ipynb`](code/notebooks/run_everything.ipynb)
runs the whole study. Choose a mode in its first cell, then **Run All**:

| Mode | What runs | Time |
|---|---|---|
| `"show"` (default) | nothing; the stored results are read | minutes |
| `"quick"` | the short steps, and the long ones in their fast form | about 45 min |
| `"full"` | everything from scratch, as for the paper | about 6 h (six-core laptop) |

```bash
git clone https://github.com/rp3gregorio/Lunar-HFE.git
cd Lunar-HFE
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,mcmc]"
jupyter lab code/notebooks/run_everything.ipynb
```

The notebook has five parts: (1) setup checks and optional downloads; (2) every
analysis step, in the order the steps need each other; (3) every figure of the
letter and the SI; (4) the paper section by section, with each number of the
letter next to the value the repository gives (✓ / ✗); (5) a summary of all
the checks (274 values, all matching).

Two optional notebooks go deeper: `optional_anchor_method.ipynb` (how the
solver reaches its steady state) and `optional_performance.ipynb` (the solver
in Python against C++). [`code/notebooks/README.md`](code/notebooks/README.md)
lists the script behind every step.

## Without Jupyter

The same steps run from the `Makefile` (`make help` lists them):

```bash
make install        # the lunar package + dependencies
make test           # unit tests of the physics code
make retrieve aux   # every analysis, in order (about 6 h)
make figures        # the paper's figures -> figures/
make notebooks      # run run_everything.ipynb as a check ("show" mode)
```

[`documents/notes/REPRODUCING.md`](documents/notes/REPRODUCING.md) is the
step-by-step recipe, including the two optional downloads (Diviner, LOLA).
After a full run, `git diff --stat code/results` shows whether any result
changed.

## How the code is organised

| Where | What |
|---|---|
| `code/src/lunar/` | the physics, as an installed package: `properties.py` ($K$, $\rho$, $c_p$), `solver.py` (the heat equation), `equilibrium.py` (the flux-anchored solver), `config.py` (every site value and setting), `notebook.py` (runs the steps from the notebook) |
| `code/pipeline/compute/` | one script per analysis; each writes one file in `code/results/` |
| `code/pipeline/figures/` | the figure scripts; `make_joint_figures.py` draws most of the paper's figures |
| `code/results/` | every result the paper reports ([`README.md`](code/results/README.md) maps each file to the paper) |
| `code/data/` | inputs: the Apollo record, SPICE kernels, site maps |
| `code/tests/` | unit tests of the physics code |
| `code/cpp/` | an independent C++ copy of the solver (SI Table S3) |
| `code/notebooks/` | `run_everything.ipynb`, and two optional notebooks |

Data flow one way: `code/data/` → `code/pipeline/compute/` →
`code/results/` → `code/pipeline/figures/` → `figures/`. See
[`STRUCTURE.md`](STRUCTURE.md) for the full map.

## Citing this work

```bibtex
@article{gregorio2026,
  author  = {Gregorio, R.~P. and Larsson, R. and Kamada, A. and Yamada, T. and Kuroda, T. and Kasai, Y.},
  title   = {Difference of the Lunar Regolith Thermal Conductivity $K_d$
             at the Apollo 15 and 17 Heat-Flow Boreholes from Global Model Values},
  journal = {Journal of Geophysical Research: Planets},
  year    = {2026},
  doi     = {TBD}
}
```

`CITATION.cff` is provided for GitHub's citation widget.

## Licenses

- **Code** (`code/src/`, `code/pipeline/`, `code/tests/`, `code/notebooks/`, `code/cpp/`):
  MIT License ([`LICENSE`](LICENSE))
- **Figures, documentation and results** (`figures/`, `documents/`, `code/results/`):
  CC-BY-4.0 ([`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0))
- **Bundled HFE data** (`code/data/apollo/`): public domain via NASA PDS-Geosciences
  (Nagihara et al., 2018)
