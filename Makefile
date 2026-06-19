# =====================================================================
#  Lunar-HFE — one-stop commands. Run `make help` for the list.
# =====================================================================
PY := python3

.PHONY: help install test retrieve aux figures paper all clean

help:                ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:             ## editable install of the lunar package + dev extras
	$(PY) -m pip install -e ".[dev]"

test:                ## run the unit-test suite
	$(PY) -m pytest -q

retrieve:            ## core retrieval + bootstrap (writes results/kd_retrieval_results.json)
	$(PY) pipeline/compute/retrieve_kd.py

aux:                 ## all auxiliary sensitivity sweeps + model selection + error budget + MCMC
	$(PY) pipeline/compute/compute_headline_rmse.py
	$(PY) pipeline/compute/compute_borestem_sensitivity.py
	$(PY) pipeline/compute/compute_stability_threshold_sensitivity.py
	$(PY) pipeline/compute/compute_surface_bias_test.py
	$(PY) pipeline/compute/compute_uniform_kd_sensitivity.py
	$(PY) pipeline/compute/compute_fixed_input_sensitivities.py
	$(PY) pipeline/compute/compute_model_selection.py
	$(PY) pipeline/compute/compute_error_budget.py
	$(PY) pipeline/compute/bayesian_crosscheck.py
	$(PY) pipeline/compute/compute_diviner_closure.py

figures:             ## regenerate every figure (writes results/figures/) for the paper + guidebook
	$(PY) pipeline/make_all_figures.py

paper:               ## compile the letter and the teaching guidebook
	cd paper/letter        && latexmk -pdf -interaction=nonstopmode letter.tex
	cd paper/letter        && latexmk -pdf -interaction=nonstopmode letter_clean.tex
	cd docs/guidebook      && latexmk -pdf -interaction=nonstopmode guidebook.tex

all: retrieve aux figures paper  ## full reproduction from scratch

clean:               ## remove LaTeX build artifacts
	cd paper/letter        && latexmk -C 2>/dev/null || true
	cd docs/guidebook      && latexmk -C 2>/dev/null || true
