# Is the thermal solver fast enough, or do we need C++?

**Question:** the 1-D heat solver is the slow part of the pipeline. Should
the inner loop be rewritten in C++?

**Answer (measured, not guessed): No.** The slow part was one Python loop
that simply had not been handed to the speed-up tool we already depend on
(Numba). Once we did that, the solver got **7× faster on a real run** while
producing **the exact same scientific numbers** (agreement to ~2×10⁻¹² K).
A full C++ rewrite would buy at most another minute or two, for months of
work and a real risk of changing published results. It is not worth it.

**Author:** Ramon III Palinguba Gregorio · **Date:** 2026-06-18 ·
**Status:** implemented and tested (Phase 4)

---

## 1. Plain-English background

Think of the simulator as a kitchen with several cooking stations. To find
the slow station we put a stopwatch on each one (this is called
"profiling"). One station was doing the overwhelming majority of the work.

There is also a built-in "speed booster" in this project called **Numba**
(it appears in the code as the tag `@njit`). Numba takes a slow Python
function and, the first time it runs, translates it into fast machine code —
the same *kind* of fast code a C++ compiler produces, because Numba uses the
same underlying compiler engine (LLVM). After that one-time translation,
the function runs at near-C++ speed for the rest of the program.

The whole question of "Python vs C++" really comes down to: **is the slow
station running as fast machine code, or as slow interpreted Python?**

---

## 2. What we found by profiling (the surprise)

Before this work, only two *tiny* helper functions in `lunar/solver.py`
carried the `@njit` speed tag:

* `_thomas` — solves the small banded system of equations, and
* `_face_harmonic_mean` — averages conductivity between soil layers.

But the function doing almost all the work — `_step`, which assembles and
advances one time step — was **plain interpreted Python**, and so was the
Newton iteration that balances the sunlit surface. The stopwatch made this
unmistakable (steady-state run, counting only the real numerical work):

| Station (function) | Share of solver time | Was it sped up? |
|---|---:|---|
| `_step` (build + advance one timestep) | **86 %** | **No — plain Python** |
| `conductivity_hayne` | 4 % | No |
| `_cp_hayne` (specific heat) | 4 % | No |
| `density_hayne` | 2 % | No |
| `_solve_surface_newton` | ~2 % | No |
| everything else (incl. the two `@njit` helpers) | ~2 % | partly |

So the earlier belief that "almost all the runtime is already Numba-compiled"
was **incorrect**. The hot loop was interpreted Python. That is good news:
it means a large speed-up was available cheaply, and it has nothing to do
with the choice of programming language.

(The figures for this analysis are in
`output/figures/fig_phase4_profile.png` and
`output/figures/fig_phase4_njit_vs_cpp.png`, produced by
`scripts/analysis/phase4_performance.py`.)

---

## 3. How much faster is Numba, really? (the benchmark)

We built a Numba copy of the inner loop using the *same* physics formulas
and the *same* physical constants, checked it gives the identical answer,
and then timed it:

| Piece of work | Plain Python | Numba | Speed-up |
|---|---:|---:|---:|
| One `_thomas` solve | 41 µs | 1.3 µs | **33×** |
| One full inner "lunar day" loop | 80 ms | 0.6 ms | **133×** |

**The one-time cost:** Numba has to translate ("compile") a function the
first time it is called. That first call took about half a second; every
call afterwards was ~0.6 ms. So it is *compile once, then run fast forever* —
negligible over a pipeline that calls the solver hundreds of times.

This confirms the key fact: **Numba already runs at C++-class speed**,
because it compiles through the same LLVM engine a C++ compiler uses.

---

## 4. What we changed (and why it is safe for the science)

The solver is *generic*: `solve_pixel` / `solve_periodic_equilibrium`
accept arbitrary conductivity, density and specific-heat functions
(`K_func`, `rho_func`, `cp_func`). Production uses the Hayne form, but the
codebase also supports `martinez`, a discrete `3layer` model, and an
optional `bedrock` wrapper. A Numba kernel cannot accept arbitrary Python
functions cleanly, so the design had to keep all of those working.

The clean solution (in `lunar/solver.py`):

1. **`_cn_step_kernel`** — a new `@njit` kernel that does the heavy work
   (the per-cell assembly loops, the surface-balance Newton iteration, and
   the tridiagonal solve). Crucially it takes the *already-evaluated*
   property **arrays** as inputs — it never sees a Python function. This is
   what keeps it generic: Hayne, Martinez, 3-layer and bedrock all just
   produce different number arrays that feed the same fast kernel.
2. **`_newton_surface_njit`** — a compiled twin of the surface Newton solve,
   inlined into the kernel (a kernel can't call the Python residual function
   directly).
3. **`_step_fast`** — evaluates the (arbitrary) property functions in Python
   exactly as before, then hands the arrays to the kernel.
4. **`_step_python`** — the original, unchanged, model-agnostic
   implementation. It is kept as the human-readable reference, the automatic
   fallback when Numba is not installed, and the oracle for the regression
   test.
5. **`_step = _step_fast if NUMBA_OK else _step_python`** — production uses
   the fast path; if Numba is ever missing, the solver still runs correctly
   (just slower).

Nothing about the public API, the boundary conditions, or the numerical
scheme changed. Only *where the same arithmetic runs* (machine code vs
interpreter) changed.

---

## 5. Proof the science is unchanged

We saved the solver outputs **before** and **after** the change for both
Apollo sites at their published retrieved conductivities (A15 `K_d` =
4.58 mW m⁻¹ K⁻¹, A17 `K_d` = 8.12 mW m⁻¹ K⁻¹), plus the Martinez, 3-layer
and bedrock paths, and compared the full temperature columns:

| Case | Largest temperature difference |
|---|---:|
| A15 (Hayne) | 2.0 × 10⁻¹³ K |
| A17 (Hayne) | 2.1 × 10⁻¹² K |
| A15 (Martinez) | 4.5 × 10⁻¹³ K |
| A15 (3-layer) | 9.4 × 10⁻¹³ K |
| A15 (bedrock, enabled) | 4.0 × 10⁻¹³ K |
| **Overall** | **2.1 × 10⁻¹² K** |

That is around 10⁻¹² K — a *trillionth* of a degree, i.e. ordinary
floating-point round-off. For comparison, the solver systematic already
carried in the paper's error budget is ±0.15 mW m⁻¹ K⁻¹ and the
measurement scatter is far larger still. **The published `K_d` numbers
(4.58 and 8.12) are unaffected.**

A dedicated regression test, `tests/test_solver_jit_identity.py`, locks the
fast kernel to the pure-Python reference (to ~10⁻¹⁰ K) for the radiative
boundary condition, the Dirichlet boundary condition, and a non-Hayne
model, so the two implementations can never silently drift in the future.

**Tests:** all **45** pass (`export MPLCONFIGDIR=/tmp/mpl &&
python3 -m pytest -q`) — the 42 pre-existing tests plus the 3 new identity
tests.

---

## 6. Measured speed-up

On one real, end-to-end solver call (`run_with`, a full flux-anchored
equilibrium), measured on this machine:

| Path | Time for one call | Full ~300-call pipeline |
|---|---:|---:|
| Before (interpreted `_step`) | 8.4 s | ~42 min |
| After (JIT kernel) | 1.15 s | ~6 min |
| **Speed-up** | **7.3×** | **7.3×** |

(The per-call speed-up is ~7× rather than the kernel's 133× because the
remaining ~14% of each call — evaluating the property formulas and the
equilibrium bookkeeping — is deliberately left in generic Python so every
conductivity model keeps working. Those parts are cheap.)

This is single-core. The pipeline's 300 calls are independent, so running
them across CPU cores would cut the wall-clock time roughly by the core
count on top of this — but that is an optional, separate change.

---

## 7. Why C++ is still not worth it

* **The speed gap to C++ is already closed.** Numba compiles through the
  same LLVM backend as a C++ compiler, so the hot kernel now runs at
  C++-class speed. A hand-tuned C++ version would realistically be ~1.3×
  faster than the JIT kernel — saving on the order of a minute over the
  whole pipeline.
* **The cost is enormous and one-sided.** Porting the solver, properties,
  equilibrium driver, grid and I/O to C++ (with Eigen/pybind11, a build
  system, and re-validation against the published numbers) is a multi-month
  effort with a high risk of subtly changing results.
* **We would lose the Python scientific ecosystem** (NumPy, SciPy,
  matplotlib, the bootstrap statistics) that the rest of the pipeline relies
  on.

**Recommendation:** keep Python + Numba. The bottleneck has been fixed in
the language we already use, with the science proven identical. If even more
speed is ever needed, parallelising the 300 independent calls is the next
cheap win — long before C++ would make sense.

---

## References

1. Numba documentation — performance tips:
   https://numba.pydata.org/numba-doc/dev/user/performance-tips.html
2. Lam, S. K., Pitrou, A., Seibert, S. "Numba: A LLVM-based Python JIT
   compiler." LLVM-HPC 2015.
3. This work: `scripts/analysis/phase4_performance.py` (profiling +
   benchmark + figures); `lunar/solver.py` (`_cn_step_kernel`,
   `_step_fast`); `tests/test_solver_jit_identity.py` (identity test).
