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
	$(PY) code/pipeline/compute/compute_diviner_closure.py

figures:             ## regenerate every figure (writes figures/) for the paper + guidebook
	$(PY) code/pipeline/make_all_figures.py

paper:               ## compile the letter and the teaching guidebook
	cd documents/letter        && latexmk -pdf -interaction=nonstopmode letter.tex
	cd documents/letter        && latexmk -pdf -interaction=nonstopmode letter_clean.tex
	cd documents/guidebook      && latexmk -pdf -interaction=nonstopmode guidebook.tex
	cd documents/thesis         && latexmk -pdf -interaction=nonstopmode thesis.tex
	cd documents/abstract       && latexmk -pdf -interaction=nonstopmode gedes_abstract.tex

all: retrieve aux figures paper  ## full reproduction from scratch

clean:               ## remove LaTeX build artifacts
	cd documents/letter        && latexmk -C 2>/dev/null || true
	cd documents/guidebook      && latexmk -C 2>/dev/null || true
	cd documents/thesis         && latexmk -C 2>/dev/null || true
	cd documents/abstract       && latexmk -C 2>/dev/null || true
