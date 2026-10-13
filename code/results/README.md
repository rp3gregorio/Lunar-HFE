# Results

Every number in the paper is read from one of these files. Each is written by
one script in `code/pipeline/compute/` (run by `make aux` or the notebooks).
Rerunning a script overwrites its file; `git diff code/results` then shows
whether anything changed.

| File | Written by | In the paper |
|---|---|---|
| `stability_windows.json` | `compute_stability_windows.py` | Sec. 2.1; SI Table S2 |
| `kd_retrieval_results.json` | `retrieve_kd.py` | the fixed-albedo, temperature-only retrieval; input to the steps below |
| `common_epoch_sensitivity.json` | `compute_common_epoch.py` | the common 1974 window (Sec. 3.2; Table 3, epoch row) |
| `diviner_closure.json`, `review_diagnostics.json` | `compute_diviner_closure.py`, `compute_review_diagnostics.py` | Diviner comparison inputs; Fig 1 (swing depth) |
| `albedo_diagnostics.json`, `albedo_sensitivity.json`, `albedo_anchor.json` | the three `compute_albedo_*.py` | SI Table S4; the Hayne et al. (2017) benchmark (SI Table S5) |
| **`joint_albedo_fit.json`** (+ `joint_albedo_fit_cache.npz`, the grid of model runs) | **`compute_joint_albedo_fit.py`** | **Table 1** ($A^*$, $K_d^*$, intervals); Fig 4; the bootstrap contrast |
| `joint_valley.json` | `compute_joint_valley.py` | SI Table S9 |
| `joint_probe_checks.json` | `compute_joint_probe_checks.py` | Secs. 3.3, 4.1; SI Table S10 |
| `joint_block_bootstrap.json` | `compute_joint_block_bootstrap.py` | SI Table S6 caption |
| `joint_numerics_certification.json` | `certify_joint_numerics.py` | SI Table S5; Table 3, solver row |
| `joint_fit_sensitivities.json` | `compute_joint_fit_sensitivities.py` | Table 3 (error budget); Table 2 inputs; SI Table S13; SI Fig S6 |
| `joint_fit_checks.json` | `compute_joint_fit_checks.py` | Table 1 (RMSE, bias, $\kappa$; Martinez & Siegler); Sec. 4.2 (effective conductivity); hold-out, TG/TR |
| `joint_diviner.json` | `compute_joint_diviner.py` | SI Table S11; SI Fig S5 |
| `gradient_epochs.json` | `compute_gradient_epochs.py` | Secs. 3.1, 3.2; SI Table S3 |
| `joint_chi_density.json` | `compute_joint_chi_density.py` | Sec. 4.2; SI Table S14; Table 3, $\chi$ row |
| `likelihood_ratio.json` | `compute_likelihood_ratio.py` | every $p$ value: Tables 1, 2; Secs. 3.2, 4.1, 4.2; SI Tables S4, S14 |
| `annual_wave.json` (+ `annual_wave_model.npz`) | `compute_annual_wave.py` | Sec. 3.4; Fig 5; SI Table S12 |
| `own_diffusivity_fit.json` | `compute_own_diffusivity_fit.py` | Sec. 3.4; SI Table S12, lower block |
| `annual_wave_surface_test.json` | `compute_annual_wave_surface_test.py` | Sec. 4.4; SI Table S12 |
| `transient_warming.json` | `compute_transient_warming.py` | Secs. 3.2, 3.3, 4.3; SI Table S7 |
| `joint_mcmc.json` (+ `joint_mcmc_grid.npz`, `joint_mcmc_chains.npz`) | `compute_joint_mcmc.py` | Sec. 4.1; Fig 6; SI Table S8 |
| `cpp_benchmark.json`, `speedup_benchmark.json` | `benchmark_cpp.py`, `benchmark_speedup.py` | SI Table S5 (C++ row); notebook 06 |
| `abstract_mean_surface_T.json` | `make_context_map_figure.py` (computed once, then reused) | SI Fig S1 (globe colours) |
