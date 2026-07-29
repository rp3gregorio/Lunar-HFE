# =====================================================================
#  Lunar-HFE — one-stop commands. Run `make help` for the list.
# =====================================================================
PY := python3

# The manuscripts (JGR letter + guidebook, GEDES abstract/thesis/defense, AOGS
# poster) are NOT in this repository — it ships the code, the shared figures
# and the reproduction notes only. They live in the document set pointed at by
# LUNAR_DOCS, which carries its own Makefile providing `paper` and `clean`.
LUNAR_DOCS ?= $(HOME)/Documents/Lunar-HFE

.PHONY: help install test retrieve aux figures paper all clean

help:                ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:             ## editable install of the lunar package + dev extras
	$(PY) -m pip install -e ".[dev]"

test:                ## run the unit-test suite
	$(PY) -m pytest -q

retrieve:            ## core retrieval + bootstrap (writes code/results/kd_retrieval_results.json)
	$(PY) code/pipeline/compute/retrieve_kd.py

aux:                 ## all auxiliary sensitivity sweeps + model selection + error budget + MCMC
	$(PY) code/pipeline/compute/compute_headline_rmse.py
	$(PY) code/pipeline/compute/compute_borestem_sensitivity.py
	$(PY) code/pipeline/compute/compute_stability_threshold_sensitivity.py
	$(PY) code/pipeline/compute/compute_surface_bias_test.py
	$(PY) code/pipeline/compute/compute_uniform_kd_sensitivity.py
	$(PY) code/pipeline/compute/compute_fixed_input_sensitivities.py
	$(PY) code/pipeline/compute/compute_model_selection.py
	$(PY) code/pipeline/compute/compute_error_budget.py
	$(PY) code/pipeline/compute/bayesian_crosscheck.py
	$(PY) code/pipeline/compute/qb_prior_width_scan.py
	$(PY) code/pipeline/compute/compute_common_epoch.py
	$(PY) code/pipeline/compute/compute_diviner_closure.py

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
