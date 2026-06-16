# =====================================================================
#  Lunar-HFE — one-stop commands. Run `make help` for the list.
# =====================================================================
PY := python3

.PHONY: help install test retrieve aux figures paper runtime all clean

help:                ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:             ## editable install of the lunar package + dev extras
	$(PY) -m pip install -e ".[dev]"

test:                ## run the unit-test suite
	$(PY) -m pytest -q

retrieve:            ## core retrieval + bootstrap (writes output/kd_retrieval_results.json)
	$(PY) scripts/pipeline/retrieve_kd.py

aux:                 ## all auxiliary sensitivity sweeps + model selection + error budget + MCMC
	$(PY) scripts/pipeline/compute_headline_rmse.py
	$(PY) scripts/pipeline/compute_borestem_sensitivity.py
	$(PY) scripts/pipeline/compute_stability_threshold_sensitivity.py
	$(PY) scripts/pipeline/compute_surface_bias_test.py
	$(PY) scripts/pipeline/compute_uniform_kd_sensitivity.py
	$(PY) scripts/pipeline/compute_fixed_input_sensitivities.py
	$(PY) scripts/pipeline/compute_model_selection.py
	$(PY) scripts/pipeline/compute_error_budget.py
	$(PY) scripts/pipeline/bayesian_crosscheck.py
	$(PY) scripts/pipeline/compute_diviner_closure.py

figures:             ## regenerate every figure (paper + guidebook + supplementary)
	$(PY) scripts/make_all_figures.py

paper:               ## compile the letter, science guidebook, and code guide PDFs
	cd paper/letter     && latexmk -pdf -interaction=nonstopmode letter.tex
	cd paper/letter     && latexmk -pdf -interaction=nonstopmode letter_clean.tex
	cd paper/guidebook     && latexmk -pdf -interaction=nonstopmode guidebook.tex
	cd paper/guidebook     && latexmk -pdf -interaction=nonstopmode guidebook_print.tex
	cd docs/code_guide  && latexmk -pdf -interaction=nonstopmode code_guide.tex
	cd docs/method_equivalence && latexmk -pdf -interaction=nonstopmode equivalence.tex

runtime:             ## run all 5 notebooks end-to-end with timing -> docs/RUNTIME.md
	$(PY) scripts/run_all_timed.py

all: retrieve aux figures paper  ## full reproduction from scratch

clean:               ## remove LaTeX build artifacts
	cd paper/letter     && latexmk -C 2>/dev/null || true
	cd paper/guidebook     && latexmk -C 2>/dev/null || true
	cd docs/code_guide  && latexmk -C 2>/dev/null || true
	cd docs/method_equivalence && latexmk -C 2>/dev/null || true
