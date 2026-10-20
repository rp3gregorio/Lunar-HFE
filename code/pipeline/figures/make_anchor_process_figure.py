#!/usr/bin/env python3
"""SI Fig. S4: the flux-anchored equilibrium solver, step by step (2026-10-12).

Replaces the three-panel fig_joint_anchor_method.pdf in the SI, which showed the
finished construction at once but not that the method is an iteration, nor why
it is allowed. Everything is computed live from the production solver for
Apollo 15 at its joint fit (config.SITES albedo, joint K_d*).

Top row -- the process:
  (a) a deliberately wrong start, straight in depth;
  (b) Step A: time-step only the top 0.70 m (production sub-grid) and read the
      cycle-mean temperature at the 0.55-m anchor;
  (c) Step B: walk down from the anchor with d<T>/dz = (Q_b - u_rect)/K
      (letter Eq. 5), never time-stepping the deep column;
      (a)-(c) are one pass at the production anchor and inner length;
  (d) repeat: the anchor change produced by each outer pass of the PRODUCTION
      schedule (stage 1 anchored at 0.25 m, stage 2 at 0.55 m), for three
      starting temperatures. The loop is replicated from the production
      pieces in the order equilibrium.solve_periodic_equilibrium calls them,
      and main() asserts that its final profile equals the production solve.
Bottom row -- why it is allowed, and that it is right:
  (e) the daily temperature swing and (f) the rectified flux u_rect fade with
      depth, so below the anchor the column feels only the mean;
  (g) the cycle-mean conductive flux equals Q_b below the skin;
  (h) a brute-force spin-up from a uniform 240 K (13 K off at 1 m) reaches the
      same state only after ~10^3 lunations.

Output: figures/fig_joint_anchor_process.pdf   (JGR full width)
Run:    python code/pipeline/figures/make_anchor_process_figure.py
"""
from __future__ import annotations
import functools
import json
import pathlib
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))

from lunar.config import (SITES, GRID, HAYNE, DT_STEP, EQ_Z_ANCHOR, EQ_N_INNER,
                          EQ_MAX_OUTER, EQ_ANCHOR_TOL)
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import (PixelInputs, solve_pixel, standard_insolation,
                          periodic_time_grid)
from lunar.equilibrium import (solve_periodic_equilibrium, _rectified_flux,
                               _reconstruct_subskin, _truncate_grid)
from lunar.plotting.style import (JGR_FULL, C_CHAR, C_DIM, C_NEUTRAL, C_FOREST,
                                  C_TEAL, C_GRID, fmt_axis, legend_between,
                                  legend_below)

OUT = _REPO / ".." / "figures"
SITE = SITES["A15"]
KD = json.loads((_REPO / "results" / "joint_albedo_fit.json").read_text())[
    "sites"]["A15"]["with_diffusivity"]["best"]["kd_star_mW"] * 1e-3
Z0 = EQ_Z_ANCHOR
ZCAP = Z0 + 0.15                       # production Step A depth (equilibrium.py)
STAGES = ((0.25, 4, 4, 0.10),          # production schedule (equilibrium.py):
          (Z0, EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL))   # (z0, n_in, max_it, tol)
SEEDS = (230.0, SITE["T_MEAN_EFF"], 270.0)   # starting temperatures (K)
ZMAX = 3.0
XLIM = (240.0, 263.0)
TOP = 0.35                              # flux closure holds below this (panel g)


def setup():
    g = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)
    insol = standard_insolation(SITE["lat"], t)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=KD,
                          H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    hp = (HAYNE["K_S"], KD, HAYNE["H"], HAYNE["CHI"])
    return g, t, insol, K, cp, hp


def step_a(sub, t, insol, K, cp, hp, T_init, n_in):
    return solve_pixel(PixelInputs(
        grid=sub, t=t, bc_mode="radiative", insolation=insol,
        albedo=SITE["albedo"], emissivity=SITE["emissivity"], Q_b=SITE["Q_BASAL"],
        T_init=T_init, n_lunations_spinup=n_in, spinup_tol_K=0.0,
        K_func=K, cp_func=cp, hayne_params=hp))


def production_trace(T_guess, g, t, insol, K, cp, hp):
    """solve_periodic_equilibrium's outer loop, pass by pass. Returns one record
    per pass: (stage z0, change of the anchor made by this pass) and the final
    profile, which main() checks against the production solver."""
    z, Qb = g.z_mid, SITE["Q_BASAL"]
    sub, n_cut = _truncate_grid(g, ZCAP)
    K0 = np.asarray(K(np.full_like(z, T_guess), z), dtype=float)
    T_init = T_guess + Qb * np.cumsum(g.dz / K0)
    T_recon, passes = T_init, []
    for z0, n_in, max_it, tol in STAGES:
        i_s = int(np.argmin(np.abs(z - z0)))
        anchor_prev = np.inf
        for it in range(1, max_it + 1):
            start = float(T_init[i_s])
            out = step_a(sub, t, insol, K, cp, hp, T_init[:n_cut], n_in)
            T_sub = out.T.mean(axis=1)
            anchor = float(T_sub[i_s])
            drift = abs(anchor - anchor_prev)
            passes.append((z0, abs(anchor - start)))
            T_full = np.empty(z.size)
            T_full[:n_cut], T_full[n_cut:] = T_sub, T_sub[-1]
            u = np.zeros(z.size)
            u[:n_cut] = _rectified_flux(out.T, sub.z_mid, K)
            T_recon = _reconstruct_subskin(T_full, z, i_s, Qb, K, u_rect=u)
            if drift < tol and it >= 2:
                break
            anchor_prev = anchor
            T_init = T_recon
    return passes, T_recon


def main(out_name="fig_joint_anchor_process.pdf"):
    g, t, insol, K, cp, hp = setup()
    z, Qb = g.z_mid, SITE["Q_BASAL"]
    m = z <= ZMAX
    i0 = int(np.argmin(np.abs(z - Z0)))
    sub, n_cut = _truncate_grid(g, ZCAP)

    print(f"A15 joint fit: K_d = {KD*1e3:.3f} mW/m/K, A = {SITE['albedo']}")
    eq = solve_periodic_equilibrium(
        grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
        emissivity=SITE["emissivity"], Q_b=Qb, K_func=K, cp_func=cp,
        T_guess=SITE["T_MEAN_EFF"], hayne_params=hp)
    T_eq = eq.T_mean

    # (d) the production schedule from three starting temperatures; certify
    traces = {}
    for s in SEEDS:
        passes, T_fin = production_trace(s, g, t, insol, K, cp, hp)
        traces[s] = passes
        prod = solve_periodic_equilibrium(
            grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
            emissivity=SITE["emissivity"], Q_b=Qb, K_func=K, cp_func=cp,
            T_guess=s, hayne_params=hp)
        dev = float(np.max(np.abs(T_fin - prod.T_mean)))
        assert dev < 1e-9 and len(passes) == prod.n_outer, (s, dev, len(passes), prod.n_outer)
        spread = float(np.max(np.abs(prod.T_mean - T_eq)[(z >= 0.8) & (z <= 2.4)]))
        print(f"  start {s:.0f} K: {len(passes)} passes "
              f"({sum(p[0] < 0.5 for p in passes)} at 0.25 m), last anchor change "
              f"{passes[-1][1]*1e3:.2f} mK; replica = production to {dev:.1e} K; "
              f"0.8-2.4 m within {spread*1e3:.2f} mK of the {SITE['T_MEAN_EFF']:.0f}-K start")
    n_lun = sum(n for (_, n, _, _), k in zip(STAGES, (
        sum(p[0] < 0.5 for p in traces[SITE["T_MEAN_EFF"]]),
        sum(p[0] >= 0.5 for p in traces[SITE["T_MEAN_EFF"]]))) for _ in range(k))
    print(f"  production start: {n_lun} lunations of the top {ZCAP:.2f} m "
          f"({n_cut} of {z.size} cells) + 3 full-column lunations")

    # (a)-(c) one pass at the production anchor from a straight-line start
    Tm = float(T_eq[m].mean())
    T_guess = (Tm - 5.0) + 4.2 * z
    out = step_a(sub, t, insol, K, cp, hp, T_guess[:n_cut], EQ_N_INNER)
    skin = out.T.mean(axis=1)
    T_full = T_guess.copy()
    T_full[:n_cut] = skin
    u = np.zeros(z.size)
    u[:n_cut] = _rectified_flux(out.T, sub.z_mid, K)
    recon = _reconstruct_subskin(T_full, z, i0, Qb, K, u_rect=u)
    gap = float(np.max(np.abs(recon - T_eq)[(z >= Z0) & m]))
    print(f"  one pass from the straight line: deep column within {gap*1e3:.1f} mK of the converged state")

    # (e)-(g) from the converged periodic cycle (full column)
    zc = eq.out.z
    amp = 0.5 * (eq.out.T.max(axis=1) - eq.out.T.min(axis=1))
    u_full = _rectified_flux(eq.out.T, zc, K)
    q_tot = np.asarray(K(T_eq, z), dtype=float) * np.gradient(T_eq, z) + np.interp(z, zc, u_full)
    ratio = q_tot / Qb
    below = z >= TOP
    print(f"  at {Z0} m: daily amplitude {np.interp(Z0, zc, amp):.2f} K, "
          f"|u_rect| = {abs(np.interp(Z0, zc, u_full))/Qb*100:.2f} % of Q_b; "
          f"mean flux within {np.max(np.abs(ratio[below & m] - 1))*100:.2f} % of Q_b below {TOP} m")

    # (h) brute force from a uniform 240-K start (compiled kernel)
    ip = int(np.argmin(np.abs(z - 1.0)))
    T_init = np.full(z.size, 240.0)
    luns, gaps, cum = [], [], 0
    for d in (1, 2, 2, 5, 10, 30, 50, 100, 300, 500, 1000, 1000):
        o = solve_pixel(PixelInputs(
            grid=g, t=t, bc_mode="radiative", insolation=insol,
            albedo=SITE["albedo"], emissivity=SITE["emissivity"], Q_b=Qb,
            T_init=T_init, n_lunations_spinup=d, spinup_tol_K=0.0,
            K_func=K, cp_func=cp, hayne_params=hp))
        cum += d
        T_init = o.T[:, -1]
        luns.append(cum)
        gaps.append(abs(o.T.mean(axis=1)[ip] - T_eq[ip]))
    luns, gaps = np.array(luns), np.array(gaps)
    print(f"  brute force: {gaps[0]:.1f} K off after 1 lunation, {gaps[-1]*1e3:.0f} mK after {luns[-1]}")

    # ── figure ──────────────────────────────────────────────────────────────
    from lunar.plotting import style as _st     # SI: text width, 11 pt, printed at 100 %
    _st.use_document_fonts()
    fig, axs = plt.subplots(2, 4, figsize=(_st.TEXT_W - 0.04, 5.2))
    fig.subplots_adjust(left=0.075, right=0.985, top=0.95, bottom=0.08,
                        wspace=0.38, hspace=0.42)
    (a, b, c, d), (e, f, gg, h) = axs
    kw_conv = dict(color=C_DIM, lw=1.2, ls="--", zorder=2)
    kw_guess = dict(color=C_NEUTRAL, lw=1.8, zorder=3)
    kw_skin = dict(color=C_FOREST, lw=2.6, zorder=5)
    kw_deep = dict(color=C_TEAL, lw=2.6, zorder=6)
    kw_dot = dict(marker="o", color=C_CHAR, ms=7, mec="white", mew=0.8, zorder=9, ls="none")
    kw_z0 = dict(color=C_DIM, lw=0.6, ls=":", zorder=1)
    kw_z1 = dict(color=C_DIM, lw=0.6, ls="-.", zorder=1)
    deep = (z >= Z0) & m

    for ax in (a, b, c):
        ax.plot(T_eq[m], z[m], **kw_conv)
        ax.axhline(Z0, **kw_z0)
        ax.set_xlim(*XLIM)
        ax.set_ylim(ZMAX, 0.0)
    a.plot(T_guess[m], z[m], **kw_guess)
    b.axhspan(0.0, sub.z_face[-1], color=C_FOREST, alpha=0.08, zorder=0)
    b.plot(T_guess[deep & (z > sub.z_face[-1])], z[deep & (z > sub.z_face[-1])], **kw_guess)
    b.plot(skin, sub.z_mid, **kw_skin)
    b.plot(skin[i0], Z0, **kw_dot)
    c.axhspan(0.0, sub.z_face[-1], color=C_FOREST, alpha=0.08, zorder=0)
    c.plot(skin, sub.z_mid, **kw_skin)
    c.plot(recon[deep], z[deep], **kw_deep)
    c.plot(recon[i0], Z0, **kw_dot)
    wz, wT = z[deep], recon[deep]
    for zt in (0.95, 1.65, 2.35):
        z1 = zt + 0.22
        c.annotate("", xy=(float(np.interp(z1, wz, wT)), z1),
                   xytext=(float(np.interp(zt, wz, wT)), zt), zorder=10,
                   arrowprops=dict(arrowstyle="-|>", color=C_CHAR, lw=1.3,
                                   mutation_scale=10, shrinkA=0, shrinkB=0))
    fmt_axis(a, xlabel="cycle-mean $T$ (K)", ylabel="depth (m)", title="(a)  start")
    fmt_axis(b, xlabel="cycle-mean $T$ (K)", title="(b)  Step A")
    fmt_axis(c, xlabel="cycle-mean $T$ (K)", title="(c)  Step B")

    seed_col = {SEEDS[0]: C_NEUTRAL, SEEDS[1]: C_CHAR, SEEDS[2]: C_NEUTRAL}
    for s in SEEDS:
        p = traces[s]
        k = np.arange(1, len(p) + 1)
        v = np.array([x[1] for x in p])
        st1 = np.array([x[0] < 0.5 for x in p])
        d.plot(k, v, "-", color=seed_col[s], lw=1.0, zorder=3)
        d.plot(k[st1], v[st1], "o", color=seed_col[s], ms=5.5, mfc="white", mew=1.2, zorder=4)
        d.plot(k[~st1], v[~st1], "s", color=seed_col[s], ms=5.0, mec="white", mew=0.6, zorder=4)
    d.axhline(0.10, color=C_DIM, lw=0.7, ls="--", zorder=1)
    d.axhline(EQ_ANCHOR_TOL, color=C_DIM, lw=0.7, ls="--", zorder=1)
    d.text(0.03, 0.10 * 1.2, "0.1 K", transform=d.get_yaxis_transform(), ha="left",
           va="bottom", color=C_DIM)
    d.text(0.03, EQ_ANCHOR_TOL * 1.2, "5 mK", transform=d.get_yaxis_transform(), ha="left",
           va="bottom", color=C_DIM)
    d.set_yscale("log")
    kmax = max(len(traces[s]) for s in SEEDS)
    d.set_xticks(range(1, kmax + 1))
    d.set_xlim(0.5, kmax + 0.5)
    fmt_axis(d, xlabel="outer pass", ylabel="anchor change (K)", title="(d)  repeat")

    for ax in (e, f, gg):
        ax.axhline(Z0, **kw_z0)
        ax.axhline(0.25, **kw_z1)
        ax.set_ylim(1.0, 0.0)
    sel = zc <= 0.9          # deeper, the half-range is the slow residual drift, not the daily wave
    e.plot(amp[sel], zc[sel], color=C_CHAR, lw=1.8)
    e.set_xscale("log")
    fmt_axis(e, xlabel="daily half-range (K)", ylabel="depth (m)", title="(e)  daily swing")
    uu = np.abs(u_full) / Qb * 100
    f.plot(uu[sel & (uu > 0)], zc[sel & (uu > 0)], color=C_CHAR, lw=1.8)
    f.set_xscale("log")
    fmt_axis(f, xlabel=r"$|u_\mathrm{rect}|$ (% of $Q_b$)", title="(f)  rectified flux")
    sel2 = (z <= 1.0) & below
    gg.plot(ratio[sel2], z[sel2], color=C_CHAR, lw=1.8)
    gg.axvline(1.0, color=C_DIM, lw=0.7, ls="--")
    gg.set_xlim(0.98, 1.02)
    fmt_axis(gg, xlabel=r"mean flux / $Q_b$", title="(g)  mean flux")
    h.plot(luns, gaps, "-o", color=C_CHAR, lw=1.4, ms=4, mec="white", mew=0.6, zorder=3)
    h.set_xscale("log")
    h.set_yscale("log")
    h.set_xlim(0.8, 4000)
    fmt_axis(h, xlabel="brute-force lunations", ylabel=r"$|\Delta T|$ at 1 m (K)",
             title="(h)  brute force")
    for ax in axs.flat:
        ax.grid(True, lw=0.5, color=C_GRID)

    top_h = [Line2D([], [], **kw_guess), Line2D([], [], **kw_skin), Line2D([], [], **kw_deep),
             Line2D([], [], **kw_dot), Line2D([], [], **kw_conv),
             Line2D([], [], marker="o", color=C_DIM, mfc="white", mew=1.2, ls="none"),
             Line2D([], [], marker="s", color=C_DIM, mec="white", ls="none"),
             Line2D([], [], color=C_CHAR, lw=1.4), Line2D([], [], color=C_NEUTRAL, lw=1.4)]
    top_l = ["starting profile", "Step A: time-stepped (top 0.70 m)",
             "Step B: walked down", "anchor (0.55 m)", "converged state",
             "pass anchored at 0.25 m", "pass anchored at 0.55 m",
             f"start {SEEDS[1]:.0f} K", f"start {SEEDS[0]:.0f} or {SEEDS[2]:.0f} K"]
    legend_between(fig, [a, b, c, d], top_h, top_l)
    legend_below(fig, [Line2D([], [], **kw_z1), Line2D([], [], **kw_z0)],
                 ["first-stage anchor (0.25 m)", "anchor (0.55 m)"])
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / out_name
    fig.savefig(p)
    plt.close(fig)
    print(f"  -> {p.resolve()}")


if __name__ == "__main__":
    main()
