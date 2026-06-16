#!/usr/bin/env python3
"""Demonstration + helpers: brute-force spin-up converges onto the shortcut.

Shows numerically that a long brute-force spin-up and the fast
flux-anchored solver (lunar/equilibrium.py) reach the *same* periodic
steady state -- the shortcut is an accelerator, not a different model.

Designed to be driven from notebooks/equilibrium_demo.ipynb, or from the
CLI. The worker functions are module-level and take only picklable
arguments, so ``compute_curves(parallel=True)`` can fan the *independent*
brute-force runs across CPU cores (macOS 'spawn'-safe).

Note on parallelism: a *single* spin-up is sequential (each lunation
needs the previous one) and cannot be split across cores. What we
parallelise here are the many *independent* runs -- the two initial
guesses x several lunation counts.

CLI:  python scripts/figures/make_equilibrium_demo.py
"""
from __future__ import annotations
import os, sys, time, functools, pathlib
import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from lunar.config import SITES, GRID, HAYNE, S0, T_LUNAR, DT_STEP
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import PixelInputs, solve_pixel
from lunar.equilibrium import solve_periodic_equilibrium

KD = 4.6e-3            # representative trial K_d [W m^-1 K^-1]
PROBE_Z = 1.0          # depth tracked in panel (a) [m]
SUBSKIN_Z = 0.30       # profiles compared below this depth [m]


def _setup(kd, site_key):
    """Build the grid, one-cycle forcing, and picklable K/cp callables."""
    site = SITES[site_key]
    g = make_geometric_grid(**GRID)
    t = np.arange(0, T_LUNAR, DT_STEP)
    insol = S0 * (1 - site["albedo"]) * np.clip(np.cos(2 * np.pi * t / T_LUNAR), 0, None)
    # functools.partial of a top-level function is picklable (lambdas are not)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=kd,
                          H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    return site, g, t, insol, K, cp


def shortcut_profile(kd=KD, site_key="A15"):
    """The fast flux-anchored equilibrium -> reference cycle-mean profile."""
    site, g, t, insol, K, cp = _setup(kd, site_key)
    t0 = time.perf_counter()
    eq = solve_periodic_equilibrium(
        grid=g, t=t, insolation=insol, albedo=site["albedo"],
        emissivity=site["emissivity"], Q_b=site["Q_BASAL"], K_func=K, cp_func=cp,
        T_guess=site["T_MEAN_EFF"])
    return dict(z=g.z_mid, T_mean=eq.T_mean, wall=time.perf_counter() - t0,
                drift=eq.anchor_drift_K, closure=eq.flux_closure, n_outer=eq.n_outer)


def bruteforce_profile(guess, n_lun, kd=KD, site_key="A15"):
    """Independent fixed-guess spin-up of ``n_lun`` lunations.

    Returns the cycle-mean profile. This is one *full* sequential run --
    the unit of work that gets parallelised across cores (one per task).
    """
    site, g, t, insol, K, cp = _setup(kd, site_key)
    t0 = time.perf_counter()
    out = solve_pixel(PixelInputs(
        grid=g, t=t, bc_mode="radiative", insolation=insol,
        albedo=site["albedo"], emissivity=site["emissivity"], Q_b=site["Q_BASAL"],
        T_init=np.full(g.n_layers, float(guess)), n_lunations_spinup=int(n_lun),
        spinup_tol_K=0.0, K_func=K, cp_func=cp))
    return dict(guess=float(guess), n_lun=int(n_lun), z=g.z_mid,
                T_mean=out.T.mean(axis=1), wall=time.perf_counter() - t0)


def _task(args):                       # top-level -> picklable for the pool
    guess, n_lun, kd, site_key = args
    return bruteforce_profile(guess, n_lun, kd=kd, site_key=site_key)


def compute_curves(n_workers=None, n_grid=(50, 100, 200, 400, 800),
                   guesses=(240.0, 260.0), kd=KD, site_key="A15", parallel=True):
    """Run the shortcut once + brute force over (guess x n_grid).

    ``parallel=True`` fans the independent brute-force runs across
    ``n_workers`` cores (default: all of them). Returns a result dict.
    """
    sc = shortcut_profile(kd=kd, site_key=site_key)
    tasks = [(float(g_), int(n_), kd, site_key) for g_ in guesses for n_ in n_grid]

    t0 = time.perf_counter()
    if parallel and len(tasks) > 1:
        # let 'spawn' workers import this module + lunar
        os.environ["PYTHONPATH"] = os.pathsep.join(
            [str(_REPO), str(_REPO / "scripts" / "figures"),
             os.environ.get("PYTHONPATH", "")])
        from concurrent.futures import ProcessPoolExecutor
        nw = int(n_workers or os.cpu_count() or 1)
        with ProcessPoolExecutor(max_workers=nw) as ex:
            res = list(ex.map(_task, tasks))
    else:
        nw = 1
        res = [_task(a) for a in tasks]
    wall = time.perf_counter() - t0

    z = sc["z"]; sub = z >= SUBSKIN_Z
    ip = int(np.argmin(np.abs(z - PROBE_Z)))
    curves = {}
    for r in res:
        d_probe = abs(r["T_mean"][ip] - sc["T_mean"][ip])
        d_sub = float(np.max(np.abs(r["T_mean"][sub] - sc["T_mean"][sub])))
        curves.setdefault(r["guess"], []).append(
            (r["n_lun"], r["T_mean"][ip], d_probe, d_sub, r["wall"]))
    for gk in curves:
        curves[gk] = np.array(sorted(curves[gk]))
    return dict(shortcut=sc, curves=curves, wall_parallel=wall, n_workers=nw,
                probe_i=ip, probe_z=float(z[ip]),
                serial_lun=sum(t[1] for t in tasks))


def plot_curves(result, save=None):
    """Two-panel figure: convergence of T(probe) and of the profile error."""
    import matplotlib.pyplot as plt
    from lunar.plotting.style import C_A15, C_A17, C_HAYNE, C_CHAR, C_DIM
    sc = result["shortcut"]; curves = result["curves"]
    ip = result["probe_i"]; pz = result["probe_z"]
    cmap = {240.0: C_A15, 260.0: C_A17}

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(10.5, 4.3))
    for gk, rec in curves.items():
        c = cmap.get(gk, C_DIM)
        axA.semilogx(rec[:, 0], rec[:, 1], "-o", ms=3, color=c,
                     label=f"brute force, guess {gk:.0f} K")
    axA.axhline(sc["T_mean"][ip], ls="--", lw=1.5, color=C_CHAR,
                label="shortcut equilibrium")
    axA.set_xlabel("brute-force spin-up [lunations]")
    axA.set_ylabel(f"cycle-mean T at {pz:.1f} m [K]")
    axA.set_title("(a)  Both guesses converge to the shortcut", loc="left", fontsize=10)
    axA.legend(fontsize=8, frameon=False); axA.grid(alpha=0.25)

    for gk, rec in curves.items():
        c = cmap.get(gk, C_DIM)
        axB.loglog(rec[:, 0], rec[:, 3], "-o", ms=3, color=c, label=f"guess {gk:.0f} K")
    axB.axhline(0.03, ls=":", lw=1.5, color=C_HAYNE, label="shortcut tolerance (0.03 K)")
    axB.set_xlabel("brute-force spin-up [lunations]")
    axB.set_ylabel(r"max$_{z>0.3\,m}\,|T_{\rm brute}-T_{\rm shortcut}|$  [K]")
    axB.set_title("(b)  Difference decays to the shortcut", loc="left", fontsize=10)
    axB.legend(fontsize=8, frameon=False); axB.grid(alpha=0.25, which="both")

    fig.suptitle(
        f"Brute force vs the flux-anchored shortcut (Apollo 15)\n"
        f"shortcut = {sc['wall']:.0f} s   |   brute force = {result['wall_parallel']:.0f} s "
        f"wall on {result['n_workers']} core(s)  ({result['serial_lun']} lunations total)",
        fontsize=10, color=C_CHAR)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    if save:
        fig.savefig(save, bbox_inches="tight"); print("->", save)
    return fig


def run(**kw):
    import matplotlib; matplotlib.use("Agg")
    res = compute_curves(**kw)
    plot_curves(res, save=_REPO / "output" / "figures" / "fig_equilibrium_demo.pdf")
    sc = res["shortcut"]
    print(f"\nshortcut: {sc['wall']:.1f} s (drift {sc['drift']*1e3:.1f} mK, "
          f"closure {sc['closure']:.2%})")
    print(f"brute force: {res['wall_parallel']:.1f} s wall on {res['n_workers']} core(s)")
    return res


if __name__ == "__main__":
    run()
