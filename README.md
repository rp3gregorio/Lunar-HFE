# Lunar-HFE

Code, data and results for

> Gregorio, R. P., Larsson, R., Kamada, A., Yamada, T., Kuroda, T., & Kasai, Y. (2026).
> Difference of the lunar regolith thermal conductivity $K_d$ at the Apollo 15 and 17
> heat-flow boreholes from global model values. Submitted to *Geophysical Research Letters*.

The standard lunar thermal model of Hayne et al. (2017) gives the whole Moon one
deep regolith conductivity, $K_d = 3.4$ mW m⁻¹ K⁻¹. This repository
recalibrates $K_d$ at the Apollo 15 and 17 heat-flow boreholes. At each site the
model's albedo and $K_d$ are fitted together to three measurements: the
equilibrium temperatures of the sensors below 80 cm, the mean surface
temperature, and the annual-wave thermal diffusivity of Langseth et al. (1976).

| | Apollo 15 | Apollo 17 |
|---|---|---|
| albedo $A^*$ | 0.136 [0.128, 0.145] | 0.137 [0.135, 0.140] |
| $K_d^*$ (mW m⁻¹ K⁻¹) | 4.87 [4.29, 5.47] | 5.89 [5.26, 6.51] |

The brackets are 95% bootstrap intervals
([`joint_albedo_fit.json`](code/results/joint_albedo_fit.json)). The global
value is rejected at both sites (likelihood ratio, $p = 9\times10^{-7}$ and
$10^{-14}$).

## Running it

You need Python 3.10 or newer (`python3 --version`; the one that comes with
macOS is 3.9).

```bash
git clone https://github.com/rp3gregorio/Lunar-HFE.git
cd Lunar-HFE
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,mcmc]"
jupyter lab code/notebooks/
```

The study is in three notebooks in `code/notebooks/`:

| Notebook | What it does | Time |
|---|---|---|
| `1_run_analysis.ipynb` | runs every analysis step in order and writes the results to `code/results/` | see below |
| `2_letter_results.ipynb` | rebuilds Table 1, draws Figures 3 and 4, and puts each number of the letter next to the value the results give (355 values) | a few minutes |
| `3_supporting_information.ipynb` | does the same for every number of the 14 SI tables (848 values) and draws SI Figures S5–S7 | a few minutes |

The repository ships every result, so notebooks 2 and 3 work straight after
installing. To recompute the results first, set `MODE` in the first code cell
of notebook 1 and run all its cells:

| `MODE` | What runs | Time |
|---|---|---|
| `"show"` (default) | nothing is recomputed; each step reports its stored result | a minute |
| `"quick"` | the short steps, and the fast forms of the long ones | about 45 min |
| `"full"` | every step from scratch, as for the paper | about 6 h on a six-core laptop |

For a full run, also set `DOWNLOAD = True` in section 1.5 (three steps need the
Diviner data). Before each step the notebook prints which step of the run it
is, how long the rest of the run should take and when it should end; the long
steps draw progress bars with their own time left. A full run first copies the
current results into `code/results/before_full_run/`, and its last section
compares every new results file with that copy (run times aside); each should
be identical.

Then run notebooks 2 and 3. Each ends by counting its checks; all 1,203
values should match. The other figures of the paper illustrate the data and
the method (Figures 1 and 2, SI Figures S1–S4); `make figures` draws them.

To install the exact package versions used for the paper, run
`pip install -r requirements-lock.txt` and then `pip install -e .`.

### Optional downloads

Two public data sets are not in the repository: the
Diviner surface temperatures (about 310 MB, for SI Table S13) and the LOLA
elevation map (33 MB, for SI Figure S1). Without them every other step runs,
and the steps that need them show their stored results. The notebook
downloads the Diviner data when you set `DOWNLOAD = True` in section 1.5 of notebook 1;
[`code/data/README.md`](code/data/README.md) gives the commands.

### Without Jupyter

The same scripts run from the `Makefile`:

```bash
make test        # unit tests of the physics code (under a minute)
make analysis    # every analysis step, in order (about 6 h)
make figures     # every figure of the paper, written to figures/
make notebook    # run the three notebooks, the analysis in "show" mode, as a check
```

After a full run, `git diff --stat code/results` shows which results changed.
Normally only run times, the recorded commit and the row order inside
`joint_mcmc_grid.npz` do.

## Layout

| Folder | Contents |
|---|---|
| `code/src/lunar/` | the model, as a Python package: `properties.py` ($K$, $\rho$, $c_p$), `solver.py` (the heat equation, Crank-Nicolson), `equilibrium.py` (the periodic steady state, by the anchor method), `config.py` (site values and solver settings) |
| `code/pipeline/compute/` | one script per analysis; each writes one file in `code/results/` |
| `code/pipeline/figures/` | the figure scripts, which read `code/results/` and write to `figures/` |
| `code/results/` | the stored results; [its README](code/results/README.md) maps each file to the paper |
| `code/data/` | inputs: the Apollo record, SPICE kernels and site maps; [its README](code/data/README.md) gives the sources |
| `code/notebooks/` | the three notebooks: run the analysis, check the letter, check the SI |
| `code/tests/` | unit tests |
| `code/cpp/` | a C++ copy of the solver, used to check the Python one (SI Table S3) |

The first lines of each script in `code/pipeline/` say what it does, and the
`Makefile` lists every analysis step with its run time.

## Citation

Please cite the paper and this repository (`CITATION.cff`; Zenodo concept
DOI [10.5281/zenodo.22183100](https://doi.org/10.5281/zenodo.22183100)).

## License

The code is under the MIT License ([`LICENSE`](LICENSE)); the results and
the documentation are under CC BY 4.0 ([`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0)).
The Apollo heat-flow record comes from the NASA Planetary Data System
(St. Clair et al., 2020, with the data restored by Nagihara et al., 2018).
