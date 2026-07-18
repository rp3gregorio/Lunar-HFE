# Guidebook — extended edition (archive)

`guidebook-extended.tex` is the **full 83-page reference manuscript** that the
concise study guide (`../guidebook.tex`) was distilled from. It is kept here as
an "extended edition" and is **not compiled into the main book**.

The concise guide keeps only three things: the pipeline, the slope-method
theory, and how the slope method differs from brute force. Everything below was
moved here to keep the main book readable in one sitting:

- The full **physics chapter** (Fourier's law, the heat equation, the lunar
  forcing and which terms are dropped, the skin-depth derivation, the boundary
  conditions, periodic steady state from first principles).
- The full **two-conductivity-models chapter**, including the Martínez & Siegler
  (2021) density-based model derivation.
- The full **numerical-solver chapter** (geometric grid, Crank–Nicolson
  derivation, the boundary-conditions-in-the-matrix walkthrough, the Thomas
  algorithm, the Newton surface solver, one-lunation stepping, the spin-up).
- The full **basal-flux Qb chapter** (the Kd–Qb degeneracy and circularity
  discussion).
- The full **uncertainty chapter** (MCMC joint posterior, AICc model selection).
- The full **independent-cross-checks chapter** (Diviner surface closure,
  Martínez α-sweep, the robustness battery).
- The full **site-geology chapter** (Apollo 15 mare vs Apollo 17 highland).
- The **conclusion** and **future-mission** sections.
- The **code-organisation appendix** and the **pre-submission audit (flag report)**.
- All **practice problems and solutions** from every chapter.

Nothing here is wrong or obsolete — it is simply more depth than a study guide
needs. To compile it standalone:

```
cd docs/guidebook/reference
latexmk -pdf guidebook-extended.tex   # needs ../figures and ../figures-tikz on the path
```

(The figure paths inside it are relative to `docs/guidebook/`, so compile from a
copy in that directory if the relative `figures/` symlink does not resolve.)
