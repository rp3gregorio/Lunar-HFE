#!/usr/bin/env python3
"""Anatomy of the 1-D model: the heat equation, Hayne's K(T,z), and the three
conditions that close the problem.

Four CANDIDATE registers of the same content, for the GEDES thesis. Build all
four, pick one (or two — the cutaway and the condition grid complement each
other rather than compete).

  A  fig_model_cutaway.pdf        a labelled regolith cutaway beside the real
                                  mean profile + diurnal envelope. Intuition
                                  first; every number on it is real.
  B  fig_model_equation_map.pdf   the PDE typeset once, each coefficient wired
                                  down to the real curve that supplies it,
                                  then the three conditions as equations.
  C  fig_model_stencil.pdf        the discretization: geometric cells, the
                                  surface half-step, and the two rows of the
                                  tridiagonal system the conditions modify.
  D  fig_model_conditions.pdf     one panel per condition, each showing what
                                  that condition actually controls in the
                                  solved field. The workhorse.

Everything plotted comes from a real converged solve at the retrieved K_d*
(results/kd_retrieval_results.json), not from a sketch:

  grid     69 cells, dz0 = 2 mm, growth 8 %, z_max 5.035 m   (config.GRID)
  forcing  S(t) = S0 cos(lat) max(0, cos 2pi t/P), 1417 steps of 1800.6 s
  BCs      radiative surface (Newton) / basal Q_b Neumann / periodic in t
  K_d*     4.600 mW m^-1 K^-1 (A15), 7.079 mW m^-1 K^-1 (A17)

Outputs: figures/fig_model_{cutaway,equation_map,stencil,conditions}.pdf
Cache:   results/model_anatomy_cache.npz  (delete, or pass --force, to rebuild)
Run:     python code/pipeline/figures/make_model_anatomy.py
"""
from __future__ import annotations

import functools
import json
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle
from matplotlib.ticker import FixedFormatter, NullFormatter

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))

from lunar.apollo_helpers import extract_sensor_stability
from lunar.config import (DT_STEP, EQ_Z_ANCHOR, GRID, HAYNE, SITES, T_LUNAR)
from lunar.constants import SIGMA_SB
from lunar.equilibrium import solve_periodic_equilibrium
from lunar.grid import make_geometric_grid
from lunar.plotting.style import (JGR_FULL, JGR_HALF, C_A15, C_A17, C_CHAR,
                                  C_CORAL, C_DIM, C_FOREST, C_GRID, C_NEUTRAL,
                                  C_PLUM, C_TEAL, FS_LABEL, FS_LEGEND, FS_TICK,
                                  WARM_SEQ, assert_no_overlap, fmt_axis)
from lunar.properties import conductivity_hayne, density_hayne, specific_heat
from lunar.solver import periodic_time_grid, standard_insolation

FIGS = _REPO.parent / "figures"
CACHE = _REPO / "results" / "model_anatomy_cache.npz"
KD_JSON = _REPO / "results" / "kd_retrieval_results.json"

P_DAYS = T_LUNAR / 86400.0          # 29.53 d
C_SITE = {"A15": C_A15, "A17": C_A17}


# ─── real data ───────────────────────────────────────────────────────────────
def build_cache(force: bool = False) -> dict:
    """One converged periodic solve per site, at the retrieved K_d*."""
    if CACHE.exists() and not force:
        with np.load(CACHE, allow_pickle=False) as f:
            return {k: f[k] for k in f.files}

    kd_all = json.loads(KD_JSON.read_text())
    grid = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)
    d: dict[str, np.ndarray] = {
        "z_mid": grid.z_mid, "z_face": grid.z_face, "dz": grid.dz,
        "t": t,
    }
    for key, site in SITES.items():
        kd = float(kd_all[key]["kd_star"])
        insol = standard_insolation(site["lat"], t)
        K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=kd,
                              H=HAYNE["H"], chi=HAYNE["CHI"])
        cp = functools.partial(specific_heat, model="hayne")
        eq = solve_periodic_equilibrium(
            grid=grid, t=t, insolation=insol, albedo=site["albedo"],
            emissivity=site["emissivity"], Q_b=site["Q_BASAL"],
            K_func=K, cp_func=cp, T_guess=site["T_MEAN_EFF"],
            z_anchor=EQ_Z_ANCHOR,
            hayne_params=(HAYNE["K_S"], kd, HAYNE["H"], HAYNE["CHI"]))
        if not eq.converged:
            raise RuntimeError(f"{key}: equilibrium did not converge")
        # anchor drift per outer iteration, second (z0 = EQ_Z_ANCHOR) stage
        drift = np.array([h[3] for h in eq.history], dtype=float)

        sens = extract_sensor_stability(site["mission"], site["MIN_DEPTH_CM"])
        d[f"{key}_insol"] = insol
        d[f"{key}_T"] = eq.out.T
        d[f"{key}_Ts"] = eq.out.T_surface
        d[f"{key}_Tmean"] = eq.T_mean
        d[f"{key}_kd"] = np.array([kd])
        d[f"{key}_drift"] = drift
        d[f"{key}_closure"] = np.array([eq.flux_closure])
        d[f"{key}_n_outer"] = np.array([eq.n_outer])
        d[f"{key}_sens_z"] = np.asarray(sens["depth_cm_all"], dtype=float)
        d[f"{key}_sens_T"] = np.asarray(sens["T_eq_all"], dtype=float)
        d[f"{key}_sens_deep"] = np.asarray(sens["deep_mask"], dtype=bool)
        print(f"  {key}: K_d* = {kd*1e3:.3f} mW/m/K, {eq.n_outer} outer iters, "
              f"flux closure {eq.flux_closure:.3%}, "
              f"T_s in [{eq.out.T_surface.min():.1f}, "
              f"{eq.out.T_surface.max():.1f}] K")

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE, **d)
    return d


def _roll_to_midnight(arr: np.ndarray, n_t: int) -> np.ndarray:
    """standard_insolation puts NOON at t=0; roll so the x axis reads
    midnight -> sunrise -> noon -> sunset -> midnight."""
    return np.roll(arr, n_t // 2, axis=-1)


def surface_terms(d: dict, key: str) -> tuple[np.ndarray, ...]:
    """The three terms of the surface energy balance, exactly as the solver
    forms them (solver._newton_ts_njit): absorbed = (1-A) S,
    emitted = eps sigma T_s^4, conducted = K(T_0, z_0) (T_s - T_0)/(dz_0/2)."""
    site = SITES[key]
    T, Ts = d[f"{key}_T"], d[f"{key}_Ts"]
    kd, dz0, z0 = float(d[f"{key}_kd"][0]), float(d["dz"][0]), float(d["z_mid"][0])
    absorbed = (1.0 - site["albedo"]) * d[f"{key}_insol"]
    emitted = site["emissivity"] * SIGMA_SB * Ts**4
    K0 = conductivity_hayne(T[0], np.full_like(T[0], z0), Ks=HAYNE["K_S"],
                            Kd=kd, H=HAYNE["H"], chi=HAYNE["CHI"])
    conducted = K0 * (Ts - T[0]) / (0.5 * dz0)
    return absorbed, emitted, conducted


def mean_flux(d: dict, key: str) -> np.ndarray:
    """Mean-field conductive flux K(<T>,z) d<T>/dz [W m^-2]."""
    z, Tm, kd = d["z_mid"], d[f"{key}_Tmean"], float(d[f"{key}_kd"][0])
    K = conductivity_hayne(Tm, z, Ks=HAYNE["K_S"], Kd=kd, H=HAYNE["H"],
                           chi=HAYNE["CHI"])
    return K * np.gradient(Tm, z)


# ─── D. one panel per condition ──────────────────────────────────────────────
def figure_conditions(d: dict) -> None:
    """The workhorse: what each of the three conditions controls in the field
    the solver actually produced."""
    n_t = d["t"].size
    day = np.arange(n_t) * (P_DAYS / n_t)

    fig, axes = plt.subplots(2, 2, figsize=(JGR_FULL, 6.5),
                             constrained_layout=True)
    (axS, axK), (axQ, axP) = axes

    # (a) surface: the radiative balance ------------------------------------
    absorbed, emitted, conducted = surface_terms(d, "A15")
    A, E, C = (_roll_to_midnight(x, n_t) for x in (absorbed, emitted, conducted))
    axS.plot(day, A, color=C_CORAL, lw=2.0, label=r"absorbed $(1-A)\,S(t)$")
    axS.plot(day, E, color=C_TEAL, lw=2.0, ls="--",
             label=r"emitted $\varepsilon\sigma T_s^4$")
    fmt_axis(axS, xlabel="Local time (days into lunation)",
             ylabel=r"Surface flux (W m$^{-2}$)",
             title=r"(a)  Surface: radiative balance closes for $T_s$")
    axS.set_xlim(0, P_DAYS)
    # 1.55x headroom above the noon peak: it drops the peak to y-fraction 0.65
    # so the legend and the inset both clear the bump (at 1.32x the peak grazed
    # the legend's underside).
    axS.set_ylim(0, 1.55 * A.max())
    axS.set_xticks([0, P_DAYS / 4, P_DAYS / 2, 3 * P_DAYS / 4, P_DAYS])
    axS.set_xticklabels(["0", "7.4", "14.8", "22.1", "29.5"])

    # Sunrise at x-fraction 0.25, sunset at 0.75: the two top corners are the
    # only verified-empty pockets. Legend takes the left, the conduction inset
    # the right — placed there (not left) so its own tick labels sit in the
    # panel interior instead of colliding with the main y-axis labels.
    # ("Conduction is ~1 % of the balance yet the only term that sees K" is the
    # caption's job — there is no third empty pocket for a note.)
    axi = axS.inset_axes([0.635, 0.60, 0.335, 0.295])
    axi.plot(day, C, color=C_PLUM, lw=1.4)
    axi.axhline(0.0, color=C_NEUTRAL, lw=0.7)
    axi.set_xlim(0, P_DAYS)
    axi.set_xticks([0, P_DAYS])
    axi.set_xticklabels(["0", "29.5"], fontsize=FS_TICK - 2.5)
    axi.set_yticks([-20, 0, 10])
    axi.tick_params(labelsize=FS_TICK - 2.5, length=2.0, pad=1.5)
    axi.set_title(r"$K\,\partial T/\partial z|_0$ (W m$^{-2}$)",
                  fontsize=FS_TICK - 2.0, pad=3.0, loc="left")
    for s in axi.spines.values():
        s.set_color(C_DIM)
    axS.legend(loc="upper left", bbox_to_anchor=(0.02, 0.985),
               frameon=True, edgecolor=C_GRID, fontsize=FS_LEGEND - 1.0)

    # (b) Hayne K(T,z) -------------------------------------------------------
    z = d["z_mid"]
    z_cm = z * 100.0
    for key in ("A15", "A17"):
        kd = float(d[f"{key}_kd"][0])
        Kb = conductivity_hayne(d[f"{key}_Tmean"], z, Ks=HAYNE["K_S"], Kd=kd,
                                H=HAYNE["H"], chi=HAYNE["CHI"])
        axK.plot(Kb * 1e3, z_cm, color=C_SITE[key], lw=2.0,
                 label=f"{SITES[key]['label']}  "
                       rf"$K_d^\ast={kd*1e3:.2f}$ mW m$^{{-1}}$K$^{{-1}}$")
    # the chi (T/350)^3 swing: K at the coldest vs hottest phase of the cycle
    T15 = d["A15_T"]
    kd15 = float(d["A15_kd"][0])
    Kmin = conductivity_hayne(T15.min(axis=1), z, Ks=HAYNE["K_S"], Kd=kd15,
                              H=HAYNE["H"], chi=HAYNE["CHI"])
    Kmax = conductivity_hayne(T15.max(axis=1), z, Ks=HAYNE["K_S"], Kd=kd15,
                              H=HAYNE["H"], chi=HAYNE["CHI"])
    axK.fill_betweenx(z_cm, Kmin * 1e3, Kmax * 1e3, color=C_FOREST, alpha=0.16,
                      lw=0, label=r"A15 diurnal range of $K$ (the $\chi T^3$ term)")
    axK.set_xscale("log")
    axK.set_yscale("log")
    axK.set_ylim(z_cm.max(), 0.08)
    axK.set_xlim(0.65, 17.0)      # holds the band minimum (0.78) and A17 (14.9)
    # H marker as a short whisker in TRUE data coords, not an axhline: a blended
    # -transform line reads as data at x = 0.65..1.0 under assert_no_overlap and
    # produces a phantom collision with its own label.
    axK.plot([0.65, 1.25], [HAYNE["H"] * 100.0] * 2, color=C_DIM, lw=0.9,
             ls=":")
    fmt_axis(axK, xlabel=r"Conductivity $K$ (mW m$^{-1}$ K$^{-1}$)",
             ylabel="Depth (cm)",
             title=r"(b)  Interior: Hayne $K(T,z)$ carries the unknown")
    # K rises monotonically with depth, so the curve runs top-left to
    # bottom-right: the verified-empty pockets are top-right and bottom-left.
    axK.text(0.965, 0.945,
             rf"$K_s={HAYNE['K_S']*1e3:.2f}$ mW m$^{{-1}}$K$^{{-1}}$" "\n"
             "at the surface",
             transform=axK.transAxes, fontsize=FS_LEGEND - 1.0, color=C_DIM,
             ha="right", va="top", linespacing=1.3)
    # sits a real gap above the whisker (inverted axis: va="bottom" grows the
    # box toward smaller depths), so label and line are adjacent, never stacked
    axK.text(0.70, 0.87 * HAYNE["H"] * 100.0, rf"$H={HAYNE['H']*100:.0f}$ cm",
             fontsize=FS_LEGEND - 0.5, color=C_DIM, ha="left", va="bottom")
    axK.legend(loc="lower left", bbox_to_anchor=(0.02, 0.02),
               frameon=True, edgecolor=C_GRID, fontsize=FS_LEGEND - 1.5)

    # (c) basal Neumann ------------------------------------------------------
    m = z >= 0.30
    for key in ("A15", "A17"):
        axQ.plot(d[f"{key}_Tmean"][m], z_cm[m], color=C_SITE[key], lw=2.0)
    axQ.set_ylim(z_cm.max(), 30.0)
    clo = max(float(d["A15_closure"][0]), float(d["A17_closure"][0]))
    fmt_axis(axQ, xlabel=r"Cycle-mean temperature $\langle T\rangle$ (K)",
             ylabel="Depth (cm)",
             title=r"(c)  Base: $Q_b$ sets the deep gradient")
    # Both curves sweep rightward through the shallow third of the panel, so
    # neither upper corner is clear, and a legend BOX with handles is wide
    # enough to graze A17 at ~3.8 m (measured). Direct colour-coded labels are
    # a third of the width and sit safely in the deep-left pocket.
    for i, key in enumerate(("A15", "A17")):
        axQ.text(0.03, 0.115 - 0.075 * i,
                 rf"{SITES[key]['label']} — $Q_b={SITES[key]['Q_BASAL']*1e3:.0f}$"
                 r" mW m$^{-2}$",
                 transform=axQ.transAxes, color=C_SITE[key],
                 fontsize=FS_LEGEND - 1.0, ha="left", va="bottom")
    axQ.text(0.03, 0.275,
             rf"$\langle q\rangle=Q_b$ to {clo*100:.2f}%",
             transform=axQ.transAxes, color=C_DIM,
             fontsize=FS_LEGEND - 1.5, ha="left", va="bottom")

    # (d) temporal periodicity ----------------------------------------------
    two = np.concatenate([day, day + P_DAYS])
    for zt, col, ls in ((0.0, C_CORAL, "-"), (0.02, C_TEAL, "-"),
                        (0.10, C_PLUM, "-"), (0.30, C_FOREST, "-")):
        if zt == 0.0:
            series = _roll_to_midnight(d["A15_Ts"], n_t)
            lab = "surface"
        else:
            i = int(np.argmin(np.abs(z - zt)))
            series = _roll_to_midnight(d["A15_T"][i], n_t)
            lab = f"{z[i]*100:.0f} cm"
        axP.plot(two, np.concatenate([series, series]), color=col, lw=1.7,
                 ls=ls, label=lab)
    # the wrap marker stops just above the 374 K surface peak so it cannot run
    # through the legend strip above it (an axvline in blended coords would,
    # and assert_no_overlap cannot see blended-transform lines)
    axP.plot([P_DAYS, P_DAYS], [60.0, 392.0], color=C_CHAR, lw=0.9, ls=":")
    axP.set_xlim(0, 2 * P_DAYS)
    axP.set_xticks([0, P_DAYS, 2 * P_DAYS])
    axP.set_xticklabels(["0", "1 lunation", "2 lunations"])
    fmt_axis(axP, xlabel="Time", ylabel="Temperature (K)",
             title=r"(d)  In time: the state must repeat, $T(t{+}P)=T(t)$")
    # T_s peaks at 374 K, so the strip above it is empty across the full width
    # — the only pocket that clears all four curves at every phase.
    axP.set_ylim(60.0, 505.0)
    axP.legend(loc="upper center", bbox_to_anchor=(0.5, 0.99), ncols=4,
               frameon=True, edgecolor=C_GRID, fontsize=FS_LEGEND - 1.0,
               columnspacing=1.1, handlelength=1.4)

    fig.canvas.draw()
    for tag, ax in (("a/surface", axS), ("b/K", axK), ("c/Q_b", axQ),
                    ("d/periodic", axP)):
        try:
            assert_no_overlap(ax)
        except AssertionError as exc:      # name the panel, not just "axes"
            raise AssertionError(f"panel {tag}: {exc}") from None
    _save(fig, "fig_model_conditions.pdf")


# ─── A. cutaway + real profile ───────────────────────────────────────────────
def figure_cutaway(d: dict) -> None:
    """A labelled cutaway of the column beside the field it produces."""
    fig, (axC, axT) = plt.subplots(
        1, 2, figsize=(JGR_FULL, 4.7), width_ratios=[1.05, 1.0],
        constrained_layout=True)

    z = d["z_mid"]
    z_cm = z * 100.0

    # --- left: the cutaway -------------------------------------------------
    # Drawn in axes coords, but on an explicit LOG depth map with its own tick
    # labels down the left side. A schematic that compresses 5 m into a box has
    # to show its scale, or the eye reads H = 6 cm as a third of the column.
    axC.set_xlim(0, 1)
    axC.set_ylim(0, 1)
    axC.axis("off")
    axC.set_title(r"(a)  What the model imposes", loc="left")

    GROUND, BOT = 0.78, 0.115        # y of the surface / of the 5 m base
    x0, x1 = 0.22, 0.605             # column edges
    XR = 0.635                       # left edge of the annotation column
    Z_TOP, Z_BOT = 0.1, 500.0        # cm, the ends of the log depth map

    def ymap(z_cm):
        zc = np.clip(np.asarray(z_cm, dtype=float), Z_TOP, Z_BOT)
        return GROUND - (GROUND - BOT) * (np.log10(zc / Z_TOP)
                                          / np.log10(Z_BOT / Z_TOP))

    # regolith, tinted by the real cycle-mean temperature at that depth (a
    # single imshow, not stacked alpha bands — those striped visibly)
    zz = np.geomspace(Z_TOP, Z_BOT, 256)
    Tb = np.interp(zz, z_cm, d["A15_Tmean"])
    axC.imshow(Tb[:, None], cmap=WARM_SEQ, aspect="auto", origin="upper",
               alpha=0.42, extent=(x0, x1, BOT, GROUND),
               vmin=Tb.min() - 30.0, vmax=Tb.max() + 10.0, zorder=1)
    axC.add_patch(Rectangle((x0, BOT), x1 - x0, GROUND - BOT, fill=False,
                            edgecolor=C_CHAR, lw=1.0, zorder=4))
    axC.plot([x0, x1], [GROUND, GROUND], color=C_CHAR, lw=1.8, zorder=5)

    # the depth scale, so the log compression is visible
    axC.text(0.02, GROUND + 0.055, "depth (cm)\nlog scale", color=C_DIM,
             fontsize=FS_TICK - 2.0, ha="left", va="center", linespacing=1.3)
    for zc, lab in ((0.1, "0.1"), (1.0, "1"), (10.0, "10"), (100.0, "100"),
                    (500.0, "500")):
        y = float(ymap(zc))
        axC.plot([x0 - 0.022, x0], [y, y], color=C_DIM, lw=0.7, zorder=5)
        axC.text(x0 - 0.032, y, lab, color=C_DIM, fontsize=FS_TICK - 2.0,
                 ha="right", va="center")

    arr = dict(arrowstyle="-|>", mutation_scale=13, lw=1.9, shrinkA=0,
               shrinkB=0, zorder=6)
    axC.add_patch(FancyArrowPatch((x0 + 0.02, 0.985), (x0 + 0.10, GROUND + 0.012),
                                  color=C_CORAL, **arr))
    axC.add_patch(FancyArrowPatch((x0 + 0.21, GROUND + 0.012), (x0 + 0.29, 0.985),
                                  color=C_TEAL, **arr))
    axC.add_patch(FancyArrowPatch((x0 + 0.30, GROUND - 0.015),
                                  (x0 + 0.30, GROUND - 0.10),
                                  color=C_PLUM, **arr))
    axC.add_patch(FancyArrowPatch((x0 + 0.14, BOT - 0.075), (x0 + 0.14, BOT + 0.055),
                                  color=C_FOREST, **arr))

    axC.text(x0 + 0.005, 0.912, r"$(1{-}A)\,S(t)$", color=C_CORAL,
             fontsize=FS_LABEL - 0.5, ha="right", va="center")
    axC.text(x0 + 0.305, 0.912, r"$\varepsilon\sigma T_s^4$", color=C_TEAL,
             fontsize=FS_LABEL - 0.5, ha="left", va="center")
    axC.text(x0 + 0.115, BOT - 0.075,
             rf"$Q_b={SITES['A15']['Q_BASAL']*1e3:.0f}$ mW m$^{{-2}}$",
             color=C_FOREST, fontsize=FS_LABEL - 1.5, ha="right", va="center")

    # the annotation column, right of the box — nothing here touches the box
    axC.text(XR, GROUND, r"$z=0$", color=C_DIM, fontsize=FS_TICK - 1.0,
             ha="left", va="center")
    axC.text(XR, GROUND - 0.075, r"$K\,\partial T/\partial z$", color=C_PLUM,
             fontsize=FS_LABEL - 1.0, ha="left", va="center")
    y_H = float(ymap(HAYNE["H"] * 100.0))
    axC.plot([x0, x1], [y_H, y_H], color=C_CHAR, lw=0.9, ls=":", zorder=5)
    axC.text(XR, y_H, rf"$K_s\!\to\!K_d$" "\n" rf"over $H={HAYNE['H']*100:.0f}$ cm",
             color=C_CHAR, fontsize=FS_TICK - 1.0, ha="left", va="center",
             linespacing=1.4)
    axC.text(XR, BOT, r"$z=5$ m", color=C_DIM, fontsize=FS_TICK - 1.0,
             ha="left", va="center")

    # real Apollo sensor depths used for the retrieval, on the same map
    sz = d["A15_sens_z"][d["A15_sens_deep"]]
    ys = ymap(sz)
    # 84–139 cm is a narrow band on a log map, so the markers necessarily
    # crowd; small and thin-edged they read as one cluster rather than a blob
    axC.plot(np.full_like(ys, x1 - 0.055), ys, ls="none", marker="o", ms=2.4,
             color=C_A15, mec="white", mew=0.35, zorder=7)
    axC.plot([x1 - 0.022] * 2, [ys.min(), ys.max()], color=C_A15, lw=1.0,
             zorder=7)
    axC.text(XR, float(np.mean(ys)),
             f"{sz.size} A15 sensors\n{sz.min():.0f}–{sz.max():.0f} cm",
             color=C_A15, fontsize=FS_TICK - 1.5, ha="left", va="center",
             linespacing=1.3)
    # sits between the H line (6 cm) and the sensor band (84–139 cm); deeper
    # than ~200 cm it would collide with the rising Q_b arrow
    axC.text(0.5 * (x0 + x1), ymap(30.0), r"$\mathbf{K_d}$ — the one unknown",
             color=C_CHAR, fontsize=FS_LABEL - 1.0, ha="center", va="center",
             zorder=7)

    # --- right: the field it produces --------------------------------------
    for key in ("A15", "A17"):
        axT.plot(d[f"{key}_Tmean"], z_cm, color=C_SITE[key], lw=2.0)
    T15 = d["A15_T"]
    axT.fill_betweenx(z_cm, T15.min(axis=1), T15.max(axis=1), color=C_FOREST,
                      alpha=0.15, lw=0)
    axT.set_yscale("log")
    axT.set_ylim(z_cm.max(), 0.08)
    axT.set_xlim(75.0, 405.0)
    fmt_axis(axT, xlabel="Temperature (K)", ylabel="Depth (cm)",
             title=r"(b)  The field those conditions produce")
    # The diurnal envelope fills the whole upper half, so there is no interior
    # pocket up there for a legend box. Direct labels in the deep-right pocket
    # (empty below ~90 cm beyond x-fraction 0.6) replace it.
    axT.text(0.965, 0.195, r"wave dies by $\sim\!50$ cm",
             transform=axT.transAxes, fontsize=FS_LEGEND - 1.0, color=C_DIM,
             ha="right", va="bottom")
    for i, key in enumerate(("A15", "A17")):
        axT.text(0.965, 0.135 - 0.060 * i,
                 rf"{SITES[key]['label']}  $\langle T\rangle$",
                 transform=axT.transAxes, fontsize=FS_LEGEND - 1.0,
                 color=C_SITE[key], ha="right", va="bottom")
    axT.text(0.965, 0.020, "shaded: A15 diurnal range",
             transform=axT.transAxes, fontsize=FS_LEGEND - 2.0, color=C_DIM,
             ha="right", va="bottom")

    fig.canvas.draw()
    assert_no_overlap(axT)
    _save(fig, "fig_model_cutaway.pdf")


# ─── B. the equation, wired to its coefficients ──────────────────────────────
def figure_equation_map(d: dict) -> None:
    """The PDE typeset once; each coefficient wired straight down to the real
    curve that supplies it. Then the three conditions, as equations."""
    fig = plt.figure(figsize=(JGR_FULL, 6.3), constrained_layout=True)
    gs = fig.add_gridspec(3, 3, height_ratios=[0.52, 1.0, 0.92], hspace=0.05)

    # --- row 1: the equation ----------------------------------------------
    axE = fig.add_subplot(gs[0, :])
    axE.axis("off")
    axE.set_xlim(0, 1)
    axE.set_ylim(0, 1)
    axE.text(0.5, 0.70,
             r"$\rho(z)\,c_p(T)\,\dfrac{\partial T}{\partial t}"
             r"=\dfrac{\partial}{\partial z}\!\left["
             r"K(T,z)\,\dfrac{\partial T}{\partial z}\right]$",
             ha="center", va="center", fontsize=17.5, color=C_CHAR)
    axE.text(0.5, 0.10,
             "One equation, three material coefficients. Only $K$ is unknown; "
             r"$\rho$ and $c_p$ are taken from Hayne et al. (2017).",
             ha="center", va="center", fontsize=FS_LEGEND, color=C_DIM)

    # --- row 2: the three coefficients ------------------------------------
    z = d["z_mid"]
    z_cm = z * 100.0

    axR = fig.add_subplot(gs[1, 0])
    axR.plot(density_hayne(z), z_cm, color=C_NEUTRAL, lw=2.0)
    axR.set_yscale("log")
    axR.set_ylim(z_cm.max(), 0.08)
    fmt_axis(axR, xlabel=r"$\rho$ (kg m$^{-3}$)", ylabel="Depth (cm)",
             title=r"$\rho(z)$ — known")

    axCp = fig.add_subplot(gs[1, 1])
    Tg = np.linspace(90.0, 390.0, 240)
    axCp.plot(Tg, specific_heat(Tg, model="hayne"), color=C_NEUTRAL, lw=2.0)
    fmt_axis(axCp, xlabel=r"$T$ (K)", ylabel=r"$c_p$ (J kg$^{-1}$K$^{-1}$)",
             title=r"$c_p(T)$ — known")

    axKc = fig.add_subplot(gs[1, 2])
    for key in ("A15", "A17"):
        kd = float(d[f"{key}_kd"][0])
        Kb = conductivity_hayne(d[f"{key}_Tmean"], z, Ks=HAYNE["K_S"], Kd=kd,
                                H=HAYNE["H"], chi=HAYNE["CHI"])
        axKc.plot(Kb * 1e3, z_cm, color=C_SITE[key], lw=2.0)
    axKc.set_xscale("log")
    axKc.set_yscale("log")
    axKc.set_ylim(z_cm.max(), 0.08)
    axKc.set_xlim(0.65, 17.0)
    # a sub-decade log span makes matplotlib print every minor tick (2x10^0,
    # 3x10^0, ...) and they collide; pin the ticks and mute the minors
    axKc.set_xticks([1.0, 3.0, 10.0])
    axKc.xaxis.set_major_formatter(FixedFormatter(["1", "3", "10"]))
    axKc.xaxis.set_minor_formatter(NullFormatter())
    fmt_axis(axKc, xlabel=r"$K$ (mW m$^{-1}$K$^{-1}$)", ylabel="")
    axKc.set_title(r"$K(T,z)$ — retrieved", color=C_CORAL)
    # direct labels in the deep-left pocket (both curves are beyond x-fraction
    # 0.8 there), so no box can sit on the coral curve
    for i, key in enumerate(("A15", "A17")):
        axKc.text(0.04, 0.10 - 0.075 * i,
                  rf"{key}  $K_d^\ast={float(d[f'{key}_kd'][0])*1e3:.2f}$",
                  transform=axKc.transAxes, color=C_SITE[key],
                  fontsize=FS_LEGEND - 1.0, ha="left", va="bottom")

    # --- row 3: the three conditions --------------------------------------
    axB = fig.add_subplot(gs[2, :])
    axB.axis("off")
    axB.set_xlim(0, 3)
    axB.set_ylim(0, 1)
    Qb15, Qb17 = SITES["A15"]["Q_BASAL"] * 1e3, SITES["A17"]["Q_BASAL"] * 1e3
    blocks = (
        (r"at $z=0$",
         r"$(1{-}A)S(t)=\varepsilon\sigma T_s^4+K\dfrac{\partial T}{\partial z}$",
         "Non-linear, so $T_s$ is found\n"
         "by Newton iteration every\n"
         "step. Fixes the amplitude\n"
         "of the wave.", C_CORAL),
        (r"at $z=5$ m",
         r"$-K\dfrac{\partial T}{\partial z}=Q_b$",
         f"Neumann. {Qb15:.0f} mW m$^{{-2}}$ (A15),\n"
         f"{Qb17:.0f} (A17), from Langseth\n"
         "et al. (1976). Fixes the\n"
         "deep gradient.", C_FOREST),
        (r"in time",
         r"$T(z,\,t{+}P)=T(z,\,t)$",
         "Periodic in one lunation.\n"
         "Removes the initial guess —\n"
         "no transient is left to fit.", C_TEAL),
    )
    for i, (where, eq, note, col) in enumerate(blocks):
        axB.add_patch(Rectangle((i + 0.045, 0.06), 0.91, 0.90, lw=1.0,
                                edgecolor=C_GRID, facecolor="none",
                                transform=axB.transData, zorder=1))
        axB.text(i + 0.09, 0.865, where, fontsize=FS_LEGEND, color=col,
                 ha="left", va="center", weight="bold")
        axB.text(i + 0.50, 0.615, eq, fontsize=FS_LABEL + 0.5, color=C_CHAR,
                 ha="center", va="center")
        axB.text(i + 0.09, 0.315, note, fontsize=FS_LEGEND - 1.0, color=C_DIM,
                 ha="left", va="center", linespacing=1.45)

    fig.canvas.draw()
    _save(fig, "fig_model_equation_map.pdf")


# ─── C. the discretization ───────────────────────────────────────────────────
def figure_stencil(d: dict) -> None:
    """Where the conditions actually enter: the grid and the two modified rows
    of the tridiagonal system."""
    fig, (axG, axM) = plt.subplots(1, 2, figsize=(JGR_HALF, 3.5),
                                   width_ratios=[1.0, 1.12],
                                   constrained_layout=True)
    dz = d["dz"]
    n = dz.size
    z_cm = d["z_mid"] * 100.0

    # --- left: the geometric grid, quantitatively --------------------------
    # Cell OUTLINES were the first attempt and they lie: on a log depth axis a
    # geometric grid has constant log spacing, so it renders as a uniform
    # ladder — the exact opposite of the coarsening it is meant to show. The
    # cell thickness itself, plotted against depth, states it without ambiguity.
    axG.step(z_cm, dz * 100.0, where="post", color=C_TEAL, lw=1.8)
    axG.set_xscale("log")
    axG.set_yscale("log")
    fmt_axis(axG, xlabel="Depth (cm)", ylabel=r"Cell thickness $\Delta z$ (cm)",
             title="(a)  The depth grid")
    # Delta z rises monotonically with depth, so the curve runs bottom-left to
    # top-right and the whole upper-left region is empty.
    axG.text(0.04, 0.96,
             f"{n} cells, "
             rf"{GRID['growth']*100:.0f}% growth" "\n"
             rf"$\Delta z_0={dz[0]*1e3:.0f}$ mm at the surface" "\n"
             rf"$\Delta z_{{n-1}}={dz[-1]*100:.0f}$ cm at "
             rf"{d['z_face'][-1]:.2f} m",
             transform=axG.transAxes, fontsize=FS_TICK - 1.5, color=C_DIM,
             ha="left", va="top", linespacing=1.5)

    # --- right: the tridiagonal system ------------------------------------
    rows = 5
    axM.set_xlim(-0.4, 11.4)
    axM.set_ylim(6.6, -1.7)
    axM.axis("off")
    axM.set_title("(b)  Where each condition enters", loc="left")
    for r in range(rows):
        for c in range(rows):
            if abs(r - c) > 1:
                continue
            col = C_CORAL if r == 0 else (C_FOREST if r == rows - 1 else C_NEUTRAL)
            axM.add_patch(Rectangle((c + 0.06, r + 0.06), 0.88, 0.88,
                                    facecolor=col,
                                    alpha=0.85 if r == c else 0.42, lw=0))
    # matrix brackets, so it reads as a matrix and not a stray staircase
    for xb, dxb in ((0.0, 0.22), (5.0, -0.22)):
        axM.plot([xb + dxb, xb, xb, xb + dxb], [-0.06, -0.06, 5.06, 5.06],
                 color=C_CHAR, lw=0.9, solid_capstyle="butt")
    axM.text(2.5, -0.55, r"$\mathbf{A}\,T^{n+1}=\mathbf{d}$",
             fontsize=FS_LABEL, color=C_CHAR, ha="center", va="center")

    # No connectors: each label is colour-matched to its row's cells AND sits
    # at that row's height, so an arrow would encode the same dependency a
    # second time. Reaching into the matrix would also mean crossing row n−1's
    # own cells; stopping outside left a 0.5-unit stub that read as a stray
    # arrowhead. Deleting them is the style rule, not a compromise.
    axM.text(5.30, 0.5, "row 0 — the $T_s$ ghost\nfrom the Newton solve",
             color=C_CORAL, fontsize=FS_TICK - 1.5, ha="left", va="center",
             linespacing=1.4)
    axM.text(5.30, rows - 0.5,
             "row $n{-}1$ — the source\n"
             r"$+\,\Delta t\,Q_b/(\rho c_p \Delta z)$",
             color=C_FOREST, fontsize=FS_TICK - 1.5, ha="left", va="center",
             linespacing=1.4)
    axM.text(2.5, 6.15,
             "Crank–Nicolson, solved by the Thomas algorithm. Only the\n"
             "first and last rows differ from the interior — numerically,\n"
             "that is all a boundary condition is.",
             fontsize=FS_TICK - 1.5, color=C_DIM, ha="center", va="center",
             linespacing=1.5)

    fig.canvas.draw()
    assert_no_overlap(axG)
    _save(fig, "fig_model_stencil.pdf")


# ─── io ──────────────────────────────────────────────────────────────────────
def _save(fig, name: str) -> None:
    """PDF for the thesis, plus a 300 dpi PNG of the same figure.

    These four are candidates meant to be compared side by side, so the PNG is
    not a convenience — it is how you pick one without opening four PDFs. Both
    come from the same in-memory figure, so they cannot drift.
    """
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / name)
    png = name.replace(".pdf", ".png")
    fig.savefig(FIGS / png, dpi=300)
    plt.close(fig)
    print(f"  wrote figures/{name}  +  figures/{png}")


def main(force: bool = False) -> None:
    print("model anatomy: real periodic solves at the retrieved K_d*")
    d = build_cache(force=force)
    figure_conditions(d)
    figure_cutaway(d)
    figure_equation_map(d)
    figure_stencil(d)


if __name__ == "__main__":
    main(force="--force" in sys.argv)
