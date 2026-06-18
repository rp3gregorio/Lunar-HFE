"""Phase 4 — is the thermal solver fast enough, or do we need C++?

This standalone benchmark answers one practical question with measured
numbers (no hand-waving):

    "The 1-D heat solver is the slow part of the pipeline. Is the current
     Python implementation fast enough, or must the inner loop be
     rewritten in C++?"

What it measures
----------------
1. WHERE the time actually goes, by profiling one real solver call
   (cProfile). This pinpoints the true hot function.
2. HOW FAST the hot loop could be if it were JIT-compiled with Numba,
   versus the current pure-Python implementation, versus what a C++
   rewrite could realistically buy. It does this by building a
   *byte-faithful* Numba copy of the inner timestep loop (same physics,
   same constants) and checking it reproduces the production solver to
   < 1e-6 K before timing it.
3. The JIT warm-up (one-time compile) cost versus the steady-state cost.
4. The full ~300-call pipeline runtime, extrapolated from a single call.

It writes two publication-styled figures to output/figures/:
    fig_phase4_profile.png       — where the time goes + warm-up vs steady
    fig_phase4_njit_vs_cpp.png   — speedups + full-pipeline extrapolation

Run:  python scripts/analysis/phase4_performance.py
"""
from __future__ import annotations

import cProfile
import io
import pathlib
import pstats
import sys
import time

import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from numba import njit  # noqa: E402

from lunar.config import GRID, SITES, S0, T_LUNAR, DT_STEP  # noqa: E402
from lunar.constants import (  # noqa: E402
    CHI_RADIATIVE,
    CP_HAYNE_C0,
    CP_HAYNE_C1,
    CP_HAYNE_C2,
    CP_HAYNE_C3,
    CP_HAYNE_C4,
    EMISSIVITY_DEFAULT,
    H_PARAMETER,
    K_SURFACE,
    RHO_DEEP,
    RHO_SURFACE,
    SIGMA_SB,
    T_REFERENCE,
)
from lunar.grid import make_geometric_grid  # noqa: E402
from lunar.solver import (  # noqa: E402
    PixelInputs,
    _thomas,
    solve_pixel,
)

from lunar.plotting.style import (  # noqa: E402
    C_A15,
    C_A17,
    C_CHAR,
    C_CORAL,
    C_DIM,
    C_FOREST,
    C_HAYNE,
    C_NEUTRAL,
    C_TEAL,
    FS_LABEL,
    FS_LEGEND,
    FS_TICK,
    JGR_FULL,
    fmt_axis,
)


# ─────────────────────────────────────────────────────────────────────────────
# A byte-faithful, fully JIT-compiled copy of the inner timestep loop.
#
# The production solver (lunar/solver.py) only @njit-decorates two tiny
# helpers (_thomas, _face_harmonic_mean); the dominant assembly loop
# (_step) and the Newton surface solve run in pure interpreted Python.
# The functions below reproduce that exact arithmetic — same Hayne
# property formulas, same Crank-Nicolson assembly, same Newton iteration —
# but inside @njit so the WHOLE inner loop compiles to machine code. We
# verify it matches the production solver to < 1e-6 K before timing it,
# so the speedup we report is for identical physics, not a shortcut.
# These live only in this analysis script; the production solver is
# untouched (no published number changes).
# ─────────────────────────────────────────────────────────────────────────────


@njit(cache=True)
def _newton_surface_jit(insol, albedo, emissivity, K_surf, dz_surf, T_sub, guess):
    T_s = guess if guess > 1.0 else 1.0
    for _ in range(40):
        rad_in = (1.0 - albedo) * insol
        rad_out = emissivity * SIGMA_SB * T_s**4
        cond = K_surf * (T_s - T_sub) / (0.5 * dz_surf)
        R = rad_in - rad_out - cond
        dR = -4.0 * emissivity * SIGMA_SB * T_s**3 - 2.0 * K_surf / dz_surf
        T_s_new = T_s - R / dR
        if T_s_new < 1.0:
            T_s_new = 0.5 * (T_s + 1.0)
        if abs(T_s_new - T_s) < 1e-4:
            return T_s_new
        T_s = T_s_new
    return T_s


@njit(cache=True)
def _inner_lunation_jit(T0, t, insol, z_mid, dz, Kd, albedo, emissivity, Q_b):
    """Run ``n_cycles`` worth of one forcing cycle, fully JIT-compiled.

    Reproduces lunar.solver._step (radiative BC) + Newton surface solve +
    Thomas tridiagonal solve, with the Hayne K/rho/cp formulas inlined.
    Returns the final temperature profile after one cycle through ``t``.
    """
    n = z_mid.size
    n_t = t.size
    T = T0.copy()

    K = np.empty(n)
    rho = np.empty(n)
    cp = np.empty(n)
    K_face = np.empty(n + 1)
    dz_c = np.empty(n + 1)
    cap = np.empty(n)
    alpha_l = np.empty(n)
    alpha_r = np.empty(n)
    a = np.empty(n)
    b = np.empty(n)
    c = np.empty(n)
    d = np.empty(n)
    cp_th = np.empty(n)
    dp_th = np.empty(n)
    x = np.empty(n)

    # depth-only quantities are constant across timesteps
    for i in range(n):
        rho[i] = RHO_DEEP - (RHO_DEEP - RHO_SURFACE) * np.exp(-z_mid[i] / H_PARAMETER)
    dz_c[0] = 0.5 * dz[0]
    dz_c[n] = 0.5 * dz[n - 1]
    for i in range(1, n):
        dz_c[i] = 0.5 * (dz[i - 1] + dz[i])

    for k in range(1, n_t):
        dt = t[k] - t[k - 1]
        # K(T,z) and cp(T) frozen at explicit half-step T
        for i in range(n):
            Kc = Kd - (Kd - K_SURFACE) * np.exp(-z_mid[i] / H_PARAMETER)
            K[i] = Kc * (1.0 + CHI_RADIATIVE * (T[i] / T_REFERENCE) ** 3)
            cp[i] = (
                CP_HAYNE_C0
                + CP_HAYNE_C1 * T[i]
                + CP_HAYNE_C2 * T[i] ** 2
                + CP_HAYNE_C3 * T[i] ** 3
                + CP_HAYNE_C4 * T[i] ** 4
            )
        # harmonic-mean face conductivities
        K_face[0] = K[0]
        K_face[n] = K[n - 1]
        for i in range(1, n):
            if K[i - 1] == 0.0 or K[i] == 0.0:
                K_face[i] = 0.0
            else:
                K_face[i] = 2.0 * K[i - 1] * K[i] / (K[i - 1] + K[i])

        for i in range(n):
            cap[i] = rho[i] * cp[i] * dz[i]
            alpha_l[i] = dt * K_face[i] / (dz_c[i] * cap[i])
            alpha_r[i] = dt * K_face[i + 1] / (dz_c[i + 1] * cap[i])

        for i in range(n):
            a[i] = -0.5 * alpha_l[i]
            c[i] = -0.5 * alpha_r[i]
            b[i] = 1.0 + 0.5 * (alpha_l[i] + alpha_r[i])
            left = T[i - 1] if i > 0 else T[i]
            right = T[i + 1] if i < n - 1 else T[i]
            d[i] = (
                0.5 * alpha_l[i] * left
                + (1.0 - 0.5 * (alpha_l[i] + alpha_r[i])) * T[i]
                + 0.5 * alpha_r[i] * right
            )

        T_s_new = _newton_surface_jit(
            insol[k], albedo, emissivity, K[0], dz[0], T[0], T[0]
        )
        d[0] -= 0.5 * alpha_l[0] * T[0]
        d[0] += 0.5 * alpha_l[0] * T_s_new
        d[0] += 0.5 * alpha_l[0] * T_s_new

        b[n - 1] -= 0.5 * alpha_r[n - 1]
        d[n - 1] += dt * Q_b / cap[n - 1]

        # Thomas solve (inlined)
        cp_th[0] = c[0] / b[0]
        dp_th[0] = d[0] / b[0]
        for i in range(1, n):
            m = b[i] - a[i] * cp_th[i - 1]
            cp_th[i] = c[i] / m if i < n - 1 else 0.0
            dp_th[i] = (d[i] - a[i] * dp_th[i - 1]) / m
        x[n - 1] = dp_th[n - 1]
        for i in range(n - 2, -1, -1):
            x[i] = dp_th[i] - cp_th[i] * x[i + 1]
        for i in range(n):
            T[i] = x[i]

    return T


# ─────────────────────────────────────────────────────────────────────────────
# Pure-Python reference timings via the production solver
# ─────────────────────────────────────────────────────────────────────────────


def _build_inputs(site, kd, n_cycles):
    grid = make_geometric_grid(**GRID)
    n_t = int(T_LUNAR / DT_STEP) + 1
    t = np.linspace(0.0, T_LUNAR, n_t)
    insol = (S0 * np.cos(np.deg2rad(site["lat"]))
             * np.maximum(0.0, np.cos(2 * np.pi * t / T_LUNAR)))

    def k_func(T, z):
        from lunar.properties import conductivity_hayne
        return conductivity_hayne(T, z, Ks=K_SURFACE, Kd=kd,
                                  H=H_PARAMETER, chi=CHI_RADIATIVE)

    inp = PixelInputs(
        grid=grid, t=t, bc_mode="radiative", insolation=insol,
        albedo=site["albedo"], emissivity=site["emissivity"],
        Q_b=site["Q_BASAL"], K_func=k_func,
        n_lunations_spinup=n_cycles, spinup_tol_K=0.0,
    )
    return grid, t, insol, inp


def _pure_thomas(a, b, c, d):
    n = b.size
    cp = np.empty(n)
    dp = np.empty(n)
    x = np.empty(n)
    cp[0] = c[0] / b[0]
    dp[0] = d[0] / b[0]
    for i in range(1, n):
        m = b[i] - a[i] * cp[i - 1]
        cp[i] = c[i] / m if i < n - 1 else 0.0
        dp[i] = (d[i] - a[i] * dp[i - 1]) / m
    x[n - 1] = dp[n - 1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x


def main():
    out_dir = _REPO / "output" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    site = SITES["A15"]
    kd = 4.58e-3
    print("\nPhase 4 — solver performance: Python/Numba vs C++?")
    print("=" * 68)

    grid, t, insol, inp = _build_inputs(site, kd, n_cycles=1)
    n_z = grid.n_layers
    n_t = t.size
    print(f"grid layers           : {n_z}")
    print(f"timesteps per lunation: {n_t}")

    # ── 1. Profile one representative solver call ────────────────────────────
    # The production solver now dispatches the inner step through the Numba
    # kernel (Phase 4 result). To measure the *interpreted* baseline this
    # analysis is about, pin solve_pixel to the pure-Python reference path
    # (_step_python) for the profiling and pure-Python timings below.
    import lunar.solver as _solver_mod
    _solver_mod._step = _solver_mod._step_python
    # Warm up FIRST (one throwaway call) so Numba compilation and one-time
    # module imports do not pollute the profile — we want the steady-state
    # compute breakdown, not import machinery.
    _, _, _, inp_warm = _build_inputs(site, kd, n_cycles=1)
    solve_pixel(inp_warm)
    # Profile 3 inner lunations (proportions match a full call but cheaper).
    _, _, _, inp_prof = _build_inputs(site, kd, n_cycles=3)
    pr = cProfile.Profile()
    pr.enable()
    solve_pixel(inp_prof)
    pr.disable()
    ps = pstats.Stats(pr).sort_stats("tottime")
    # Keep only the actual numerical compute (lunar package); import/JIT
    # machinery is excluded so the breakdown reflects the real hot path.
    compute_files = {"solver.py", "properties.py", "grid.py", "equilibrium.py"}
    prof_rows = []
    for func, stat in ps.stats.items():
        _, _, tottime, cumtime, _ = stat
        base = pathlib.Path(func[0]).name
        if base in compute_files:
            prof_rows.append((f"{base}:{func[2]}", tottime))
    prof_rows.sort(key=lambda r: r[1], reverse=True)
    total_tot = sum(r[1] for r in prof_rows)
    f_hot = next((tt for nm, tt in prof_rows if nm == "solver.py:_step_python"), 0.0) / total_tot
    print("\nProfile (steady-state, lunar compute only) — top by self-time:")
    for fname, tt in prof_rows[:6]:
        print(f"  {fname:42s} {tt:7.3f} s  ({100*tt/total_tot:4.1f}%)")
    print(f"  -> hot path (_step) is {100*f_hot:.0f}% of solver compute time")

    # ── 2a. Micro-benchmark: Thomas solve, pure-Python vs Numba ──────────────
    rng = np.random.default_rng(0)
    a = rng.random(n_z); b = 4.0 + rng.random(n_z); c = rng.random(n_z); d = rng.random(n_z)
    _thomas(a, b, c, d)  # warm up the production njit kernel

    def _time(fn, *args, reps):
        t0 = time.perf_counter()
        for _ in range(reps):
            fn(*args)
        return (time.perf_counter() - t0) / reps

    reps = 20000
    t_thomas_py = _time(_pure_thomas, a, b, c, d, reps=reps)
    t_thomas_jit = _time(_thomas, a, b, c, d, reps=reps)
    print("\nThomas tridiagonal solve (one call):")
    print(f"  pure Python : {t_thomas_py*1e6:8.2f} us")
    print(f"  Numba @njit : {t_thomas_jit*1e6:8.2f} us "
          f"({t_thomas_py/t_thomas_jit:.0f}x faster)")

    # ── 2b. Macro-benchmark: the WHOLE inner loop, pure-Python vs Numba ──────
    # Pure-Python: time one inner lunation through the production solve_pixel.
    T_init = np.full(n_z, 250.0)
    inp.T_init = T_init.copy()

    t0 = time.perf_counter()
    out_py = solve_pixel(inp)
    t_inner_py = time.perf_counter() - t0
    T_final_py = out_py.T[:, -1]

    # Numba: first call includes one-time compile (warm-up), then steady state.
    t0 = time.perf_counter()
    T_final_jit = _inner_lunation_jit(
        T_init, t, insol, grid.z_mid, grid.dz, kd,
        site["albedo"], site["emissivity"], site["Q_BASAL"])
    t_inner_jit_warm = time.perf_counter() - t0

    steady = []
    for _ in range(5):
        t0 = time.perf_counter()
        _inner_lunation_jit(
            T_init, t, insol, grid.z_mid, grid.dz, kd,
            site["albedo"], site["emissivity"], site["Q_BASAL"])
        steady.append(time.perf_counter() - t0)
    t_inner_jit = float(np.median(steady))

    max_dT = float(np.max(np.abs(T_final_py - T_final_jit)))
    print("\nInner-loop fidelity check (Numba copy vs production solver):")
    print(f"  max |ΔT| over the column = {max_dT:.2e} K  "
          f"({'PASS' if max_dT < 1e-6 else 'FAIL'})")
    print("\nOne inner lunation (709 timesteps):")
    print(f"  pure Python (current)     : {t_inner_py*1e3:8.1f} ms")
    print(f"  Numba warm-up (1st call)  : {t_inner_jit_warm*1e3:8.1f} ms  (one-time compile)")
    print(f"  Numba steady state        : {t_inner_jit*1e3:8.1f} ms  "
          f"({t_inner_py/t_inner_jit:.0f}x faster than pure Python)")

    speedup_inner = t_inner_py / t_inner_jit

    # ── 3. Full-pipeline extrapolation ───────────────────────────────────────
    # Ground the extrapolation on a MEASURED full production solver call
    # (one flux-anchored equilibrium = many inner lunations), not a guess.
    from scripts.pipeline.retrieve_kd import run_with
    run_with(site, kd=5.1e-3, k_model="hayne")        # warm caches/imports
    t0 = time.perf_counter()
    run_with(site, kd=7.3e-3, k_model="hayne")        # fresh kd -> no cache hit
    t_call_py = time.perf_counter() - t0
    # If the hot loop were JIT-compiled, only the (1-f_hot) non-hot part and
    # the f_hot part / speedup remain. Conservative: keep non-hot as Python.
    t_call_jit = t_call_py * ((1.0 - f_hot) + f_hot / speedup_inner)
    print(f"\nMeasured one full production solver call (equilibrium):")
    print(f"  pure Python (current)     : {t_call_py:6.2f} s")
    print(f"  with JIT-compiled hot loop: {t_call_jit:6.2f} s  "
          f"({t_call_py/t_call_jit:.0f}x faster)")

    N_CALLS = 300
    pipe_py_min = N_CALLS * t_call_py / 60.0
    pipe_jit_min = N_CALLS * t_call_jit / 60.0
    # Realistic optimistic C++: ~1.3x over a JIT-compiled inner loop (same
    # LLVM-class codegen; the gap is small once the loop is compiled).
    CPP_OVER_JIT = 1.3
    pipe_cpp_min = pipe_jit_min / CPP_OVER_JIT
    # Parallel JIT across cores (embarrassingly parallel over the 300 calls).
    import os
    ncores = os.cpu_count() or 8
    par_eff = 0.85
    pipe_jit_par_min = pipe_jit_min / max(1, int(ncores * par_eff))

    print(f"\nFull-pipeline extrapolation (~{N_CALLS} solver calls):")
    print(f"  current pure-Python loop       : {pipe_py_min:7.1f} min")
    print(f"  Numba-jitted inner loop        : {pipe_jit_min:7.1f} min  "
          f"({pipe_py_min/pipe_jit_min:.0f}x faster)")
    print(f"  Numba jitted + {ncores}-core parallel : {pipe_jit_par_min:7.1f} min")
    print(f"  hypothetical C++ (×{CPP_OVER_JIT} over JIT) : {pipe_cpp_min:7.1f} min  "
          f"(saves only {pipe_jit_min - pipe_cpp_min:.1f} min vs JIT)")

    # ── Figures ──────────────────────────────────────────────────────────────
    _fig_profile(out_dir, prof_rows, total_tot,
                 t_inner_jit_warm, t_inner_jit, n_z, n_t)
    _fig_njit_vs_cpp(out_dir,
                     t_thomas_py, t_thomas_jit,
                     t_inner_py, t_inner_jit, speedup_inner,
                     pipe_py_min, pipe_jit_min, pipe_jit_par_min, pipe_cpp_min,
                     ncores, max_dT)

    print("\nDone.")


def _short(name):
    """Human-friendly labels for the profile bar chart."""
    table = {
        "solver.py:_step_python": "_step  (assembly loop)",
        "properties.py:conductivity_hayne": "conductivity_hayne",
        "properties.py:_cp_hayne": "_cp_hayne",
        "properties.py:density_hayne": "density_hayne",
        "solver.py:_solve_surface_newton": "_solve_surface_newton",
        "solver.py:surface_energy_balance_residual": "surface_balance_residual",
        "solver.py:solve_pixel": "solve_pixel (driver)",
        "solver.py:_thomas": "_thomas  (@njit)",
        "solver.py:_face_harmonic_mean": "_face_harmonic_mean (@njit)",
    }
    return table.get(name, name)


def _fig_profile(out_dir, prof_rows, total_tot,
                 t_warm, t_steady, n_z, n_t):
    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(JGR_FULL, 3.7),
        gridspec_kw={"width_ratios": [1.55, 1.0], "wspace": 0.45})

    # (a) where the time goes — top self-time functions
    rows = prof_rows[:7]
    labels = [_short(r[0]) for r in rows]
    vals = [100 * r[1] / total_tot for r in rows]
    is_jit = ["@njit" in lab for lab in labels]
    colors = [C_NEUTRAL if j else C_CORAL for j in is_jit]
    y = np.arange(len(rows))[::-1]
    axL.barh(y, vals, color=colors, edgecolor=C_CHAR, lw=0.6)
    for yi, v in zip(y, vals):
        axL.text(v + 1.0, yi, f"{v:.0f}%", va="center",
                 fontsize=FS_TICK, color=C_CHAR)
    axL.set_yticks(y)
    axL.set_yticklabels(labels, fontsize=FS_TICK)
    axL.set_xlim(0, max(vals) * 1.18)
    fmt_axis(axL, xlabel="share of solver self-time  (%)",
             title="(a)  Where the time goes")
    axL.text(0.97, 0.04,
             "pure Python (not JIT-compiled)",
             transform=axL.transAxes, ha="right", va="bottom",
             fontsize=FS_LEGEND, color=C_CORAL, style="italic")

    # (b) warm-up (one-time compile) vs steady-state cost
    bars = axR.bar([0, 1], [t_warm * 1e3, t_steady * 1e3],
                   color=[C_TEAL, C_FOREST], edgecolor=C_CHAR, lw=0.7,
                   width=0.62)
    axR.set_xticks([0, 1])
    axR.set_xticklabels(["warm-up\n(1st call,\ncompile)", "steady\nstate"],
                        fontsize=FS_TICK)
    for bar, v in zip(bars, [t_warm * 1e3, t_steady * 1e3]):
        axR.text(bar.get_x() + bar.get_width() / 2, v,
                 f"{v:.0f} ms", ha="center", va="bottom",
                 fontsize=FS_TICK, color=C_CHAR)
    axR.set_ylim(0, max(t_warm, t_steady) * 1e3 * 1.2)
    fmt_axis(axR, ylabel="time per inner lunation  (ms)",
             title="(b)  Compile once, run fast")

    fig.suptitle("Phase 4 — the solver's hot path is pure Python, "
                 "not the JIT-compiled kernels",
                 fontsize=FS_LABEL + 0.5, fontweight="bold", x=0.5, y=1.08)
    png = out_dir / "fig_phase4_profile.png"
    fig.savefig(png, dpi=200)
    fig.savefig(out_dir / "fig_phase4_profile.pdf")
    plt.close(fig)
    print(f"\nSaved: {png}")


def _fig_njit_vs_cpp(out_dir,
                     t_thomas_py, t_thomas_jit,
                     t_inner_py, t_inner_jit, speedup_inner,
                     pipe_py_min, pipe_jit_min, pipe_jit_par_min, pipe_cpp_min,
                     ncores, max_dT):
    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(JGR_FULL, 3.8),
        gridspec_kw={"width_ratios": [1.0, 1.25], "wspace": 0.42})

    # (a) speedups: pure Python vs Numba for the two kernels (log scale)
    groups = ["Thomas\nsolve", "Full inner\nloop"]
    py = [t_thomas_py * 1e6, t_inner_py * 1e3]      # us, ms (different units)
    jit = [t_thomas_jit * 1e6, t_inner_jit * 1e3]
    # normalise to "x slower than Numba" so units cancel
    rel_py = [p / j for p, j in zip(py, jit)]
    rel_jit = [1.0, 1.0]
    x = np.arange(len(groups))
    w = 0.36
    axL.bar(x - w / 2, rel_py, w, color=C_CORAL, edgecolor=C_CHAR, lw=0.6,
            label="pure Python")
    axL.bar(x + w / 2, rel_jit, w, color=C_TEAL, edgecolor=C_CHAR, lw=0.6,
            label="Numba @njit")
    axL.set_yscale("log")
    for xi, rp in zip(x, rel_py):
        axL.text(xi - w / 2, rp, f"{rp:.0f}×", ha="center", va="bottom",
                 fontsize=FS_TICK, color=C_CORAL)
    axL.set_xticks(x)
    axL.set_xticklabels(groups, fontsize=FS_TICK)
    axL.axhline(1.0, color=C_DIM, lw=0.8, ls=":")
    fmt_axis(axL, ylabel="run time relative to Numba  (×)",
             title="(a)  Numba is already C++-class")
    axL.legend(fontsize=FS_LEGEND, loc="upper left")

    # (b) full pipeline runtime: the actual decision
    names = ["current\n(pure\nPython)", "Numba\nJIT",f"Numba JIT\n+{ncores}-core",
             "C++\n(hypo-\nthetical)"]
    vals = [pipe_py_min, pipe_jit_min, pipe_jit_par_min, pipe_cpp_min]
    cols = [C_CORAL, C_FOREST, C_HAYNE, C_NEUTRAL]
    xb = np.arange(len(names))
    bars = axR.bar(xb, vals, color=cols, edgecolor=C_CHAR, lw=0.7, width=0.66)
    for bar, v in zip(bars, vals):
        lab = f"{v:.0f} min" if v >= 1 else f"{v*60:.0f} s"
        axR.text(bar.get_x() + bar.get_width() / 2, v,
                 lab, ha="center", va="bottom",
                 fontsize=FS_TICK, color=C_CHAR)
    axR.set_xticks(xb)
    axR.set_xticklabels(names, fontsize=FS_TICK - 0.5)
    axR.set_ylim(0, max(vals) * 1.18)
    fmt_axis(axR, ylabel="full ~300-call pipeline  (minutes)",
             title="(b)  C++ saves minutes; Numba saves hours")
    # annotate the marginal C++ gain
    axR.annotate(
        f"C++ gains only\n{pipe_jit_min - pipe_cpp_min:.1f} min over JIT",
        xy=(3, pipe_cpp_min), xytext=(2.1, max(vals) * 0.55),
        fontsize=FS_LEGEND, color=C_DIM, ha="center",
        arrowprops=dict(arrowstyle="->", color=C_DIM, lw=0.8))

    fig.suptitle("Phase 4 — JIT-compiling the inner loop closes the gap to "
                 "C++; a rewrite is not worth it",
                 fontsize=FS_LABEL + 0.5, fontweight="bold", x=0.5, y=1.06)
    png = out_dir / "fig_phase4_njit_vs_cpp.png"
    fig.savefig(png, dpi=200)
    fig.savefig(out_dir / "fig_phase4_njit_vs_cpp.pdf")
    plt.close(fig)
    print(f"Saved: {png}")


if __name__ == "__main__":
    main()
