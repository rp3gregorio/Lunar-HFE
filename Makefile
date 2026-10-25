# Lunar-HFE: run `make help` for the targets.
PY := python3
C := code/pipeline/compute

.PHONY: help install test analysis figures notebook all clean

help:        ## list the targets
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*## "}{printf "  %-10s %s\n", $$1, $$2}'

install:     ## install the lunar package with the notebook, test and MCMC extras
	$(PY) -m pip install -e ".[dev,mcmc]"

test:        ## unit tests of the physics code
	$(PY) -m pytest -q

# Every analysis step, in the order of 1_run_analysis.ipynb (later steps read
# the results of earlier ones). Times are for a six-core laptop.
analysis:    ## every analysis step, in order (about 6 h)
	$(PY) $(C)/retrieve_kd.py                       # 95 min  fixed-albedo retrieval; later steps reuse it
	$(PY) $(C)/compute_common_epoch.py              # 15 min  the common 1974 window
	$(PY) $(C)/compute_diviner_closure.py           #  3 min  Diviner comparison inputs (needs the Diviner data)
	$(PY) $(C)/compute_review_diagnostics.py        #  5 min  daily swing below 80 cm (needs the Diviner data)
	$(PY) $(C)/compute_albedo_diagnostics.py        # 13 min  site albedos
	$(PY) $(C)/compute_albedo_sensitivity.py        # 35 min  fixed-albedo fits (SI Table S7)
	$(PY) $(C)/compute_albedo_anchor.py             #  5 min  the published model at its own values
	$(PY) $(C)/compute_stability_windows.py         # seconds each sensor's stability window (SI Table S1)
	$(PY) $(C)/compute_insolation_check.py          #  1 min  real against idealized sunlight (Section 2.2)
	$(PY) $(C)/compute_joint_albedo_fit.py          # 25 min  the joint fit of albedo and K_d (Table 1)
	$(PY) $(C)/certify_joint_numerics.py            #  3 min  solver tests at the fit (SI Table S3)
	$(PY) $(C)/benchmark_cpp.py                     #  2 min  the C++ copy of the solver (SI Table S3)
	$(PY) $(C)/compute_subset_fits.py               #  1 min  each probe and thermometer type (Table 1, Figure 3)
	$(PY) $(C)/compute_joint_valley.py              # seconds the albedo-K_d trade-off (SI Table S10)
	$(PY) $(C)/compute_joint_probe_checks.py        # seconds each probe's diffusivity, the 5 K test (SI Table S9)
	$(PY) $(C)/compute_joint_block_bootstrap.py     #  1 min  bootstrap by probe (SI Table S5)
	$(PY) $(C)/compute_joint_fit_sensitivities.py   # 80 min  error budget (SI Tables S5, S12)
	$(PY) $(C)/compute_joint_fit_checks.py          #  4 min  the models against the sensors (Table 1, Figure 3)
	$(PY) $(C)/compute_martinez_density.py          # 20 min  Martinez & Siegler with its density fitted (SI Table S4)
	$(PY) $(C)/compute_martinez_diffusivity.py      #  2 min  the density it needs for the measured diffusivities (Section 4.1)
	$(PY) $(C)/compute_joint_diviner.py             #  3 min  Diviner comparison (SI Table S13; needs the Diviner data)
	$(PY) $(C)/compute_gradient_epochs.py           # seconds the measured gradients (SI Table S2)
	$(PY) $(C)/compute_joint_chi_density.py         # 50 min  radiative coefficient and density (SI Table S14)
	$(PY) $(C)/compute_likelihood_ratio.py          # seconds every p value
	$(PY) $(C)/compute_annual_wave.py               #  3 min  the annual wave, measured and modeled (SI Figure S5, Table S11)
	$(PY) $(C)/compute_own_diffusivity_fit.py       # seconds the fit with our own diffusivities (SI Table S11)
	$(PY) $(C)/compute_annual_wave_surface_test.py  #  6 min  the near-surface layer (SI Table S11)
	$(PY) $(C)/compute_transient_warming.py         #  2 min  warming after deployment (SI Table S8)
	$(PY) $(C)/compute_joint_mcmc.py                #  2 h    posterior with Q_b and density free (SI Figure S6, Table S6)

figures:     ## the paper's figures, written to figures/
	$(PY) code/pipeline/make_all_figures.py

notebook:    ## run the three notebooks (analysis in "show" mode, then the checks) as a check (a few minutes)
	cd code/notebooks && for n in 1_run_analysis 2_letter_results 3_supporting_information; do \
	  PATH="$$(dirname $$($(PY) -c 'import sys; print(sys.executable)')):$$PATH" \
	  $(PY) -m jupyter nbconvert --to notebook --execute --stdout $$n.ipynb > /dev/null || exit 1; done

all: analysis figures  ## the whole study from scratch

clean:       ## remove Python caches
	find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
