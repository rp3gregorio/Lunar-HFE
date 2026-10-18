# Results

Every number in the paper is read from one of these files. Each is written by
one script in `code/pipeline/compute/` (run by `make aux` or `code/notebooks/run_everything.ipynb`).
Rerunning a script overwrites its file; `git diff code/results` then shows
whether anything changed.

| File | Written by | In the paper (v2.0-jgr numbering) |
|---|---|---|
| `stability_windows.json` | `compute_stability_windows.py` | Sec. 2.1; SI Table S1 |
| `kd_retrieval_results.json` | `retrieve_kd.py` | the fixed-albedo, temperature-only retrieval; input to the steps below |
| `common_epoch_sensitivity.json` | `compute_common_epoch.py` | the common 1974 window (Secs. 3.3, 3.5; SI Table S5, epoch row) |
| `diviner_closure.json`, `review_diagnostics.json` | `compute_diviner_closure.py`, `compute_review_diagnostics.py` | Diviner comparison inputs; Fig 1 (swing depth) |
| `albedo_diagnostics.json`, `albedo_sensitivity.json`, `albedo_anchor.json` | the three `compute_albedo_*.py` | Sec. 3.4 (a fixed albedo); SI Table S7 |
| **`joint_albedo_fit.json`** (+ `joint_albedo_fit_cache.npz`, the grid of model runs) | **`compute_joint_albedo_fit.py`** | **Sec. 3.3, Table 1** ($A^*$, $K_d^*$, intervals); Sec. 3.2 (temperatures only); Fig 4; the bootstrap contrast (Sec. 4.2) |
| `subset_fits.json` | `compute_subset_fits.py` | Secs. 3.1, 3.2, Table 1 and Fig 3 (each probe and each thermometer type on its own) |
| `joint_valley.json` | `compute_joint_valley.py` | Sec. 3.4; SI Table S10 |
| `joint_probe_checks.json` | `compute_joint_probe_checks.py` | Sec. 3.4 (the ±5 K test), Sec. 4.2 (the transient diffusivities); SI Table S9 |
| `joint_block_bootstrap.json` | `compute_joint_block_bootstrap.py` | Sec. 2.3; SI Table S5 |
| `joint_numerics_certification.json` | `certify_joint_numerics.py` | Sec. 2.2; SI Table S3; Table 2, solver row |
| `joint_fit_sensitivities.json` | `compute_joint_fit_sensitivities.py` | SI Table S5 (error budget); the pooled comparison (Sec. 4.2); SI Tables S5, S12; SI Fig S5 |
| `joint_fit_checks.json` | `compute_joint_fit_checks.py` | Table 2 (RMSE, bias, $\kappa$; Martinez & Siegler); Fig 4 and Sec. 3.3; Secs. 3.1, 3.2 (each sensor minus the fit); Sec. 3.5 (probe split, hold-out); Sec. 4.1 (effective conductivity) |
| `martinez_density_fit.json` | `compute_martinez_density.py` | Sec. 4.3 (the Martinez & Siegler model with its density fitted); SI Table S4 |
| `joint_diviner.json` | `compute_joint_diviner.py` | Sec. 3.4; SI Table S13; SI Fig S6 |
| `gradient_epochs.json` | `compute_gradient_epochs.py` | Sec. 3.3; SI Table S2 |
| `joint_chi_density.json` | `compute_joint_chi_density.py` | Sec. 4.3; SI Table S14; Table 2, $\chi$ row |
| `likelihood_ratio.json` | `compute_likelihood_ratio.py` | every $p$ value: Tables 1, 2; Secs. 3.3, 4.2, 4.3; SI Tables S7, S14 |
| `annual_wave.json` (+ `annual_wave_model.npz`) | `compute_annual_wave.py` | Sec. 3.4; Fig 6; SI Table S11 |
| `own_diffusivity_fit.json` | `compute_own_diffusivity_fit.py` | Secs. 3.5, 4.2; SI Table S11, lower block |
| `annual_wave_surface_test.json` | `compute_annual_wave_surface_test.py` | Secs. 3.4, 4.4; SI Table S11 |
| `transient_warming.json` | `compute_transient_warming.py` | Secs. 3.3–3.5, 4.4; SI Table S8 |
| `joint_mcmc.json` (+ `joint_mcmc_grid.npz`, `joint_mcmc_chains.npz`) | `compute_joint_mcmc.py` | Secs. 3.5, 4.2, 4.3; Fig 7; SI Table S6 |
| `cpp_benchmark.json`, `speedup_benchmark.json` | `benchmark_cpp.py`, `benchmark_speedup.py` | SI Table S3 (C++ row); `optional_performance.ipynb` |
| `abstract_mean_surface_T.json` | `make_context_map_figure.py` (computed once, then reused) | SI Fig S1 (globe colours) |
