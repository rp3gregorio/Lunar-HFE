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

.PHONY: help install test retrieve aux figures notebooks paper all clean

help:                ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:             ## editable install of the lunar package + dev extras
	# mcmc is included: `make aux` runs compute_joint_mcmc.py, which imports emcee
	$(PY) -m pip install -e ".[dev,mcmc]"

test:                ## run the unit-test suite
	$(PY) -m pytest -q

retrieve:            ## core retrieval + bootstrap (writes code/results/kd_retrieval_results.json)
	$(PY) code/pipeline/compute/retrieve_kd.py

aux:                 ## every analysis of the paper after the retrieval (24 steps with retrieve; ~6 h)
	$(PY) code/pipeline/compute/compute_common_epoch.py
	$(PY) code/pipeline/compute/compute_diviner_closure.py
	$(PY) code/pipeline/compute/compute_review_diagnostics.py   # ~5 min: flux scan, diurnal swing, level vs K_d, Diviner site vs zonal, TG/TR split
	$(PY) code/pipeline/compute/compute_albedo_diagnostics.py   # ~13 min: site albedo vs LOLA map, albedo x K_d scan
	$(PY) code/pipeline/compute/compute_albedo_sensitivity.py   # ~35 min: albedo / angular-law / chi re-retrievals (in-situ band)
	$(PY) code/pipeline/compute/compute_albedo_anchor.py   # ~5 min: Hayne (2017) standard-model check + published albedo laws at the sites
	$(PY) code/pipeline/compute/compute_stability_windows.py   # seconds: every sensor's stability window (letter Sec. 2.1, SI Table S1)
	$(PY) code/pipeline/compute/compute_joint_albedo_fit.py   # ~25 min: joint (albedo, K_d) retrieval + bootstrap (letter Secs. 2.3, 3.3)
	$(PY) code/pipeline/compute/certify_joint_numerics.py   # ~2 min, after the joint fit, before the sensitivities: the reported K_d* under each numerical choice (grid, time step, anchor, run length, start, K_d spacing; SI Table S3)
	$(PY) code/pipeline/compute/compute_joint_valley.py   # seconds: the A17 worked example (SI Table S11)
	$(PY) code/pipeline/compute/compute_joint_probe_checks.py   # seconds: per-probe and transient-diffusivity K_d, the +-5 K Apollo test (letter Secs. 3.2, 4.2; SI Table S9)
	$(PY) code/pipeline/compute/compute_joint_block_bootstrap.py   # ~1 min: bootstrap with sensors grouped by probe (letter Sec. 2.3; SI Table S5)
	$(PY) code/pipeline/compute/compute_joint_fit_sensitivities.py   # ~90 min: joint-fit error budget (incl. c_p), Q_b map, model comparison (letter Table 2 error budget, Sec. 4.2 pooled comparison; SI Tables S5, S12; SI Fig S5)
	$(PY) code/pipeline/compute/compute_joint_fit_checks.py   # ~4 min, after the sensitivities: Table 1, each sensor minus the fit (Fig 3), hold-out, probe and TG/TR splits, gradient-matching Q_b (letter Secs. 3.1, 3.4)
	$(PY) code/pipeline/compute/compute_joint_diviner.py   # ~3 min: Diviner comparison at the joint fit (SI Table S13, Fig S6)
	$(PY) code/pipeline/compute/compute_gradient_epochs.py   # seconds: A17/A15 gradient under each window epoch + drill-core gradient (letter Secs. 3.1, 3.3; SI Table S2)
	$(PY) code/pipeline/compute/compute_joint_chi_density.py   # ~50 min: joint fit for chi 1.5-3.2 and site-specific densities (letter Sec. 4.3; SI Table S14)
	$(PY) code/pipeline/compute/compute_likelihood_ratio.py   # seconds, after the joint fit, sensitivities, chi sweep and albedo anchor: likelihood-ratio tests (letter Table 1, Secs. 3.3, 4.2, 4.3; SI Tables S7, S14)
	$(PY) code/pipeline/compute/compute_annual_wave.py   # ~3 min: annual wave measured in the full record + SPICE-forced forward model (letter Sec. 3.2, Fig 5, SI Table S10)
	$(PY) code/pipeline/compute/compute_own_diffusivity_fit.py   # ~15 s, after the annual wave and the joint fit: joint fit with our own diffusivities instead of Langseth's (letter Secs. 3.4, 4.2; SI Table S10)
	$(PY) code/pipeline/compute/compute_annual_wave_surface_test.py   # ~6 min, after the annual wave: near-surface layer (H 3-10 cm, K_s x0.5-2) vs the annual-wave amplitude factor (letter Sec. 4.4 (iii), SI Table S10)
	$(PY) code/pipeline/compute/compute_transient_warming.py   # ~2 min, after the annual wave: surface darkening at deployment, warming in the windows, refit (letter Secs. 3.2-3.4, 4.4; SI Table S8)
	$(PY) code/pipeline/compute/compute_joint_mcmc.py   # ~2 h (resumable grid) + 1 min sampling: posterior of A, K_d, Q_b, rho_d (letter Fig 6, Secs. 3.4, 4.2; SI Table S6)

figures:             ## regenerate the paper's figures (writes figures/)
	$(PY) code/pipeline/make_all_figures.py

notebooks:           ## run run_everything.ipynb top to bottom in "show" mode, as a check (a few minutes)
	# the kernel is the "python" on PATH: put this Python's folder first, so it is the one used
	cd code/notebooks && PATH="$$(dirname $$($(PY) -c 'import sys; print(sys.executable)')):$$PATH" \
	  $(PY) -m jupyter nbconvert --to notebook --execute --stdout run_everything.ipynb > /dev/null

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
