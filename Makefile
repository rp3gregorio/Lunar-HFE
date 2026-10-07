# =====================================================================
#  Lunar-HFE — one-stop commands. Run `make help` for the list.
# =====================================================================
PY := python3

# The manuscripts (JGR letter + guidebook, GEDES abstract/thesis/defense, AOGS
# poster) are NOT in this repository — it ships the code, the shared figures
# and the reproduction notes only. They live in the document set pointed at by
# LUNAR_DOCS, which carries its own Makefile providing `paper` and `clean`.
#
# Default: the sibling `Others/` folder — the working layout is
#     Lunar-HFE/github/    (this repository)
#     Lunar-HFE/Others/    (the document set)
# Resolved relative to THIS Makefile, so moving the pair keeps it working.
LUNAR_DOCS ?= $(abspath $(dir $(lastword $(MAKEFILE_LIST)))../Others)

.PHONY: help install test retrieve aux figures paper all clean

help:                ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:             ## editable install of the lunar package + dev extras
	# mcmc is included: `make aux` runs bayesian_crosscheck.py, which imports emcee
	$(PY) -m pip install -e ".[dev,mcmc]"

test:                ## run the unit-test suite
	$(PY) -m pytest -q

retrieve:            ## core retrieval + bootstrap (writes code/results/kd_retrieval_results.json)
	$(PY) code/pipeline/compute/retrieve_kd.py

aux:                 ## all auxiliary sensitivity sweeps + model selection + error budget + MCMC
	$(PY) code/pipeline/compute/compute_headline_rmse.py
	$(PY) code/pipeline/compute/compute_borestem_sensitivity.py
	$(PY) code/pipeline/compute/compute_stability_threshold_sensitivity.py
	$(PY) code/pipeline/compute/compute_window_criteria_sensitivity.py
	$(PY) code/pipeline/compute/compute_surface_bias_test.py
	$(PY) code/pipeline/compute/compute_uniform_kd_sensitivity.py
	$(PY) code/pipeline/compute/compute_fixed_input_sensitivities.py
	$(PY) code/pipeline/compute/compute_model_selection.py
	$(PY) code/pipeline/compute/bayesian_crosscheck.py
	$(PY) code/pipeline/compute/qb_prior_width_scan.py
	$(PY) code/pipeline/compute/compute_common_epoch.py
	$(PY) code/pipeline/compute/compute_diviner_closure.py
	$(PY) code/pipeline/compute/compute_qb_degeneracy.py
	$(PY) code/pipeline/compute/compute_offset_free_fit.py
	$(PY) code/pipeline/compute/compute_review_diagnostics.py   # ~5 min: flux scan, diurnal swing, level vs K_d, Diviner site vs zonal, TG/TR split
	$(PY) code/pipeline/compute/compute_albedo_diagnostics.py   # ~13 min: site albedo vs LOLA map, albedo x K_d scan
	$(PY) code/pipeline/compute/compute_albedo_sensitivity.py   # ~35 min: albedo / angular-law / chi re-retrievals (in-situ band)
	$(PY) code/pipeline/compute/compute_albedo_anchor.py   # ~5 min: Hayne (2017) standard-model check + published albedo laws at the sites
	$(PY) code/pipeline/compute/compute_error_budget.py   # after all of its inputs (qb_degeneracy, common_epoch, albedo_sensitivity, ...)
	$(PY) code/pipeline/compute/audit_qb_basins.py   # ~10 min: wide-grid basin audit
	$(PY) code/pipeline/compute/audit_qb_basin_followup.py   # ~1 min: narrow A15 basin at Q_b=10 (letter Sec. 2.4)
	$(PY) code/pipeline/compute/compute_stability_windows.py   # seconds: every sensor's stability window (letter Sec. 2.1, SI Table S4)
	$(PY) code/pipeline/compute/compute_joint_albedo_fit.py   # ~25 min: joint (albedo, K_d) retrieval + bootstrap (letter Sec. 2.6, 3.2)
	$(PY) code/pipeline/compute/compute_joint_valley.py   # seconds: the A17 worked example (SI Text S15, Table S5)
	$(PY) code/pipeline/compute/compute_joint_probe_checks.py   # seconds: per-probe and transient-diffusivity K_d, the +-5 K Apollo test (letter Sec. 3.3, 4.1)
	$(PY) code/pipeline/compute/compute_joint_block_bootstrap.py   # ~1 min: bootstrap with sensors grouped by probe (Text S8)
	$(PY) code/pipeline/compute/compute_joint_fit_sensitivities.py   # ~90 min: joint-fit error budget (incl. c_p), Q_b map, model comparison (letter Table 2 pooled comparison, Table 3 error budget; SI Fig S7)
	$(PY) code/pipeline/compute/compute_joint_fit_checks.py   # ~1 min, after the sensitivities: hold-out, TG/TR, epoch, gradient-matching Q_b
	$(PY) code/pipeline/compute/compute_joint_diviner.py   # ~3 min: Diviner comparison at the joint fit (Text S10)
	$(PY) code/pipeline/compute/compute_gradient_epochs.py   # seconds: A17/A15 gradient under each window epoch + drill-core gradient (letter Sec. 3.1, 3.2)
	$(PY) code/pipeline/compute/compute_joint_chi_density.py   # ~50 min: joint fit for chi 1.5-3.2 and site-specific densities (letter Sec. 4.2; SI Text S17, Table S6)
	$(PY) code/pipeline/compute/compute_likelihood_ratio.py   # seconds, after the joint fit, sensitivities, chi sweep and albedo anchor: likelihood-ratio tests (letter Tables 1-2, Sec. 3.2, 4.1, 4.2; SI Texts S13, S17)
	$(PY) code/pipeline/compute/compute_annual_wave.py   # ~3 min: annual wave measured in the full record + SPICE-forced forward model (letter Sec. 3.4, SI Text S18)
	$(PY) code/pipeline/compute/compute_transient_warming.py   # ~2 min, after the annual wave: surface darkening at deployment, warming in the windows, refit (letter Sec. 3.2, 3.3, 4.3; SI Text S19, Table S8)
	$(PY) code/pipeline/compute/compute_joint_mcmc.py   # ~2 h (resumable grid) + 1 min sampling: posterior of A, K_d, Q_b, rho_d (letter Fig 6, SI Text S14)

figures:             ## regenerate every figure (writes figures/) for the paper + guidebook
	$(PY) code/pipeline/make_all_figures.py

paper:               ## compile every document (delegates to the document set at $LUNAR_DOCS)
	@test -f "$(LUNAR_DOCS)/Makefile" || { \
	  echo "No document set at $(LUNAR_DOCS)."; \
	  echo "The manuscripts live outside this repo; set LUNAR_DOCS to point at them."; \
	  exit 1; }
	$(MAKE) -C "$(LUNAR_DOCS)" paper

all: retrieve aux figures  ## full reproduction from scratch (code + figures)

clean:               ## remove build artifacts (repo + document set, if present)
	find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@test -f "$(LUNAR_DOCS)/Makefile" && $(MAKE) -C "$(LUNAR_DOCS)" clean || true
