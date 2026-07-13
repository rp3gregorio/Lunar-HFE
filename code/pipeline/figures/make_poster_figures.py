"""Vector figure panels for the AOGS A0 poster.

Reads the two AOGS study archives
  results/aogs_sensitivity.json      (DEM horizons, forcing, first sweep)
  results/aogs_density_study.json    (swept boundaries x cp/coupled)
and writes print-resolution vector PDFs into
  deliverables/documents/aogs/poster/figures/

Panels (all pure re-plots of cached results; no physics here):
  poster_dem.pdf          site DEM shaded relief, side by side
  poster_horizons.pdf     horizon polar plots + energy loss
  poster_forcing.pdf      standard vs DEM-shadowed insolation
  poster_profiles.pdf     best-config thermal profiles vs HFE sensors
  poster_leverage.pdf     RMSE spread: cp vs coupled branches
  poster_boundaries.pdf   best-RMSE map over the (z1, z2) boundary plane

Run:  .venv/bin/python code/pipeline/figures/make_poster_figures.py
Panels needing aogs_density_study.json are skipped until it exists.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

from lunar._bootstrap import find_repo_root  # noqa: E402
from lunar.plotting.style import (JGR_FULL, C_A15, C_A17, C_CHAR, C_GRID,  # noqa: E402
                                  C_PLUM, C_TEAL, fmt_axis, assert_no_overlap,
                                  legend_below)
from matplotlib.legend_handler import HandlerTuple  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "compute" / "aogs"))
import s1_sensitivity as aogs  # noqa: E402  (sun_track: the ONE solar-geometry source)

ROOT = find_repo_root()
OUT = ROOT.parent / "deliverables" / "documents" / "aogs" / "poster" / "figures"
POSTER_W = 4.8      # small canvas => ~2.9x font scale at A0 print
SITE_COLOR = {"A15": C_A15, "A17": C_A17}
BR_NAME = {"cp": "heat-capacity only", "coupled": "density-coupled K"}


def _save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name)
    plt.close(fig)
    print(f"  -> {OUT / name}")


def dem_panels(sens):
    dem, ppd = aogs.load_dem()            # finest available, memmapped (raw DN)
    ls = LightSource(azdeg=315, altdeg=35)
    fig, axes = plt.subplots(1, 2, figsize=(POSTER_W, 2.7),
                             constrained_layout=True)
    for ax, sk in zip(axes, ("A15", "A17")):
        s = sens["sites"][sk]
        half = 3.0
        r0 = int((90 - s["lat"] - half) * ppd)
        r1 = int((90 - s["lat"] + half) * ppd)
        c0 = int((s["lon"] + 180 - half) * ppd)
        c1 = int((s["lon"] + 180 + half) * ppd)
        shaded = ls.shade(dem[r0:r1, c0:c1] * aogs.DEM_SCALE_KM,
                          cmap=plt.get_cmap("gist_earth"),
                          blend_mode="soft", vert_exag=40)
        ax.imshow(shaded, extent=(s["lon"] - half, s["lon"] + half,
                                  s["lat"] - half, s["lat"] + half),
                  origin="upper")
        ax.plot(s["lon"], s["lat"], "o", color="white", ms=11,
                mec=SITE_COLOR[sk], mew=3)
        fmt_axis(ax, xlabel="longitude (°E)",
                 ylabel="latitude (°N)" if sk == "A15" else "",
                 title=f"Apollo {sk[1:]}  ({s['lat']:.1f}°N, {s['lon']:.1f}°E)")
    _save(fig, "poster_dem.pdf")


def horizon_panels(sens):
    fig = plt.figure(figsize=(POSTER_W, 2.9))
    for i, sk in enumerate(("A15", "A17")):
        s = sens["sites"][sk]
        ax = fig.add_subplot(1, 2, i + 1, projection="polar")
        az = np.radians(np.asarray(s["horizon_az_deg"]))
        hor = np.asarray(s["horizon_deg"])
        ax.plot(np.append(az, az[0]), np.append(hor, hor[0]),
                color=SITE_COLOR[sk], lw=2.6)
        ax.fill(np.append(az, az[0]), np.append(hor, hor[0]),
                color=SITE_COLOR[sk], alpha=0.25)
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_title(f"Apollo {sk[1:]}  (max {s['horizon_max_deg']:.0f}°)",
                     fontsize=11)
        ax.set_rlabel_position(200)
        ax.tick_params(labelsize=8)
    fig.tight_layout()
    _save(fig, "poster_horizons.pdf")


def forcing_panels(sens):
    fig, axes = plt.subplots(1, 2, figsize=(POSTER_W, 2.2),
                             constrained_layout=True)
    for ax, sk in zip(axes, ("A15", "A17")):
        fs = sens["forcing_samples"][sk]
        ax.plot(fs["t_days"], fs["S_standard"], color=C_GRID, lw=3.2,
                label="standard")
        ax.plot(fs["t_days"], fs["S_shadowed"], color=SITE_COLOR[sk], lw=1.4,
                label="DEM-shadowed")
        fmt_axis(ax, xlabel="time (Earth days)",
                 ylabel="insolation (W m$^{-2}$)" if sk == "A15" else "",
                 title=f"Apollo {sk[1:]}")
        if sk == "A15":
            std_h, shd_h15 = ax.get_lines()[0], ax.get_lines()[1]
        else:
            shd_h17 = ax.get_lines()[1]
    # one shared legend BELOW the panels (a per-panel legend under the axes
    # collided with the x-labels — the audit's poster_forcing defect);
    # the shadowed swatch shows both site colors via HandlerTuple.
    legend_below(fig, [std_h, (shd_h15, shd_h17)],
                 ["standard", "DEM-shadowed"], ncols=2, fontsize=9,
                 handler_map={tuple: HandlerTuple(ndivide=None, pad=0.3)})
    for ax in axes:
        fig.canvas.draw()
        assert_no_overlap(ax)
    _save(fig, "poster_forcing.pdf")


def profile_panels(study):
    meta, sites, runs = study["meta"], study["sites"], study["runs"]
    z_grid = np.asarray(meta["z_mid_m"])
    fig, axes = plt.subplots(1, 2, figsize=(POSTER_W, 4.1),
                             constrained_layout=True)
    for ax, sk in zip(axes, ("A15", "A17")):
        s = sites[sk]
        zs = np.asarray(s["sensor_depth_cm"]) / 100.0
        Ts = np.asarray(s["sensor_T_eq"])
        Te = np.asarray(s["sensor_T_std"])
        zm = z_grid <= 2.7            # plot only the displayed window:
        zg = z_grid[zm]               # off-window tails would trip the
                                      # overlap guard from outside the axes
        hay = next(r for r in runs if r["site"] == sk and r["rho"] == "hayne")
        ax.plot(np.asarray(hay["T_mean_profile"])[zm], zg, "--",
                color=C_CHAR, lw=1.8,
                label=f"Hayne continuous ({hay['rmse_K']:.2f} K)")
        for br, lw_ in (("cp", 2.2), ("coupled", 3.4)):
            best = min((r for r in runs if r["site"] == sk
                        and r["branch"] == br and r["rho"] != "hayne"),
                       key=lambda r: r["rmse_K"])
            col = C_TEAL if br == "cp" else SITE_COLOR[sk]
            ax.plot(np.asarray(best["T_mean_profile"])[zm], zg,
                    color=col, lw=lw_,
                    label=(f"best {BR_NAME[br]} ({best['rmse_K']:.2f} K)"))
        eb = ax.errorbar(Ts, zs, xerr=Te, fmt="o", color="black", ms=7,
                         mfc="white", mew=1.6, elinewidth=1.4, capsize=3,
                         zorder=6, label="HFE deep sensors")
        if sk == "A15":
            eb_handle = eb
        ax.set_ylim(2.5, 0.7)
        ax.set_xlim(Ts.min() - 1.6, Ts.max() + 1.6)
        fmt_axis(ax, xlabel="mean temperature (K)",
                 ylabel="depth (m)" if sk == "A15" else "",
                 title=f"Apollo {sk[1:]}")
    # ONE shared legend below both panels (RMSE values live in the poster's
    # table, not here); the coupled swatch shows both site colors side by
    # side via HandlerTuple. No safe interior pocket -> outside-below.
    hA, hB = axes[0].get_lines(), axes[1].get_lines()
    handles = [hA[0], hA[1], (hA[2], hB[2]), eb_handle]
    labels = ["Hayne continuous", "best heat-capacity only",
              "best density-coupled K", "HFE deep sensors"]
    legend_below(fig, handles, labels, ncols=2, fontsize=9,
                 handler_map={tuple: HandlerTuple(ndivide=None, pad=0.3)})
    for ax in axes:
        fig.canvas.draw()
        assert_no_overlap(ax)
    _save(fig, "poster_profiles.pdf")


def leverage_panels(study):
    runs = study["runs"]
    fig, axes = plt.subplots(1, 2, figsize=(POSTER_W, 2.5),
                             constrained_layout=True)
    for ax, sk in zip(axes, ("A15", "A17")):
        data, labels, colors = [], [], []
        for br in ("cp", "coupled"):
            vals = [r["rmse_K"] for r in runs if r["site"] == sk
                    and r["branch"] == br and r["rho"] != "hayne"]
            data.append(vals)
            labels.append(BR_NAME[br])
            colors.append(C_TEAL if br == "cp" else SITE_COLOR[sk])
        base = next(r["rmse_K"] for r in runs
                    if r["site"] == sk and r["rho"] == "hayne")
        bp = ax.boxplot(data, tick_labels=labels, patch_artist=True,
                        widths=0.5)
        for patch, c in zip(bp["boxes"], colors):
            patch.set_facecolor(c)
            patch.set_alpha(0.55)
        ax.axhline(base, color=C_CHAR, ls="--", lw=1.4)
        ax.text(0.02, base, " Hayne continuous", fontsize=8.5, color=C_CHAR,
                va="bottom", transform=ax.get_yaxis_transform())
        fmt_axis(ax, ylabel="deep-sensor RMSE (K)" if sk == "A15" else "",
                 title=f"Apollo {sk[1:]}")
    _save(fig, "poster_leverage.pdf")


def boundary_panels(study):
    meta, runs = study["meta"], study["runs"]
    z1g, z2g = meta["z1_grid"], meta["z2_grid"]
    fig, axes = plt.subplots(1, 2, figsize=(POSTER_W, 2.6),
                             constrained_layout=True)
    for ax, sk in zip(axes, ("A15", "A17")):
        M = np.full((len(z2g), len(z1g)), np.nan)
        for a, z2 in enumerate(z2g):
            for b, z1 in enumerate(z1g):
                cand = [r["rmse_K"] for r in runs
                        if r["site"] == sk and r["branch"] == "coupled"
                        and r["rho"] != "hayne"
                        and abs(r["z1_m"] - z1) < 1e-9
                        and abs(r["z2_m"] - z2) < 1e-9]
                M[a, b] = min(cand)
        im = ax.imshow(M, origin="lower", cmap="RdYlGn_r", aspect="auto")
        ax.set_xticks(range(len(z1g)), [f"{100 * v:.0f}" for v in z1g])
        ax.set_yticks(range(len(z2g)), [f"{100 * v:.0f}" for v in z2g])
        for a in range(len(z2g)):
            for b in range(len(z1g)):
                ax.text(b, a, f"{M[a, b]:.2f}", ha="center", va="center",
                        fontsize=9)
        fmt_axis(ax, xlabel="z$_1$ skin|mid boundary (cm)",
                 ylabel="z$_2$ mid|deep (cm)" if sk == "A15" else "",
                 title=f"Apollo {sk[1:]} — coupled branch")
        fig.colorbar(im, ax=ax, shrink=0.9).set_label("best RMSE (K)",
                                                      fontsize=9)
    _save(fig, "poster_boundaries.pdf")


def emit_numbers(sens, study):
    """poster_numbers.tex: every quantitative value the poster quotes,
    generated from the archives (no hand-typed numbers on the poster)."""
    import math
    L = []
    for sk in ("A15", "A17"):
        s = sens["sites"][sk]
        az = np.radians(np.asarray(s["horizon_az_deg"]))
        H = np.radians(np.asarray(s["horizon_deg"]))
        svf = float(np.mean(np.cos(H) ** 2))          # sky-view factor
        tag = {"A15": "Afif", "A17": "Asev"}[sk]
        L.append(f"\\newcommand{{\\hor{tag}}}{{{s['horizon_max_deg']:.1f}}}")
        L.append(f"\\newcommand{{\\loss{tag}}}{{{100*s['insolation_energy_loss']:.2f}}}")
        L.append(f"\\newcommand{{\\svf{tag}}}{{{svf:.3f}}}")
        L.append(f"\\newcommand{{\\kdstar{tag}}}{{{1e3*s['kd_star_used']:.2f}}}")
    if study is not None:
        runs = study["runs"]
        for sk in ("A15", "A17"):
            tag = {"A15": "Afif", "A17": "Asev"}[sk]
            hay = next(r for r in runs if r["site"] == sk and r["rho"] == "hayne")
            L.append(f"\\newcommand{{\\rmsehay{tag}}}{{{hay['rmse_K']:.2f}}}")
            for br in ("cp", "coupled"):
                best = min((r for r in runs if r["site"] == sk
                            and r["branch"] == br and r["rho"] != "hayne"),
                           key=lambda r: r["rmse_K"])
                b = "cp" if br == "cp" else "cK"
                L.append(f"\\newcommand{{\\rmse{b}{tag}}}{{{best['rmse_K']:.2f}}}")
                L.append(f"\\newcommand{{\\bestz{b}{tag}}}{{{100*best['z1_m']:.0f}/{100*best['z2_m']:.0f}}}")
                rr = "/".join(str(int(v)) for v in best["rho"])
                L.append(f"\\newcommand{{\\bestrho{b}{tag}}}{{{rr}}}")
    xp = ROOT / "results" / "aogs_crossite.json"
    if xp.exists():
        x = json.loads(xp.read_text())
        L.append(f"\\newcommand{{\\rmsehomAfif}}{{{x['A15_homogeneous']:.2f}}}")
        L.append(f"\\newcommand{{\\rmsehomAsev}}{{{x['A17_homogeneous']:.2f}}}")
        L.append(f"\\newcommand{{\\xferatAsev}}{{{x['A15_config_at_A17']:.2f}}}")
        L.append(f"\\newcommand{{\\xferatAfif}}{{{x['A17_config_at_A15']:.2f}}}")
    sp = ROOT / "results" / "aogs_svf_terms.json"
    if sp.exists():
        # (1-SVF) terrain-radiation terms (aogs_svf_terms.py; T_terr ~= T_s
        # upper bound): mean sensor-depth warming from terrain IR alone and
        # from IR + reflected sunlight -- the channel OPPOSING the shadowing
        # loss. Feeds the poster's two-channel "Why shadowing matters" box.
        sv = json.loads(sp.read_text())
        for sk in ("A15", "A17"):
            tag = {"A15": "Afif", "A17": "Asev"}[sk]
            L.append(f"\\newcommand{{\\svfdtir{tag}}}"
                     f"{{{sv[sk]['dT_mean_ir_selfheat_K']:.2f}}}")
            L.append(f"\\newcommand{{\\svfdtall{tag}}}"
                     f"{{{sv[sk]['dT_mean_ir_plus_reflected_K']:.2f}}}")
    # AUDIT 2026-07-12 additions ------------------------------------------
    # shadow cooling at the deep sensors (standard vs shadowed forcing,
    # Hayne-continuous config, same n_inner — the difference is clean).
    # The old poster said "~1 K": the archive says 2.22 / 0.48 K.
    for sk in ("A15", "A17"):
        tag = {"A15": "Afif", "A17": "Asev"}[sk]
        pair = {r["forcing"]: np.asarray(r["T_model_at_sensors"])
                for r in sens["runs"]
                if r["site"] == sk and r["profile"] == "hayne-continuous"}
        cool = float((pair["standard"] - pair["shadowed"]).mean())
        L.append(f"\\newcommand{{\\shadowcool{tag}}}{{{cool:.2f}}}")
    # winner-degeneracy honesty (bootstrap) + true convergence wording
    bp = ROOT / "results" / "aogs_winner_bootstrap.json"
    if bp.exists():
        bs = json.loads(bp.read_text())
        for sk in ("A15", "A17"):
            tag = {"A15": "Afif", "A17": "Asev"}[sk]
            L.append(f"\\newcommand{{\\stabcK{tag}}}"
                     f"{{{100 * bs[f'{sk}_coupled']['winner_stability']:.0f}}}")
            lo, hi = bs[f"{sk}_coupled"]["best_rmse_ci95_K"]
            L.append(f"\\newcommand{{\\bootcicK{tag}}}"
                     f"{{{lo:.2f}--{hi:.2f}}}")
    if study is not None:
        cert = study["certification"]
        L.append(f"\\newcommand{{\\driftmax}}"
                 f"{{{1000 * max(v['drift_K'] for v in cert.values()):.0f}}}")
        winners_fc = []
        for sk in ("A15", "A17"):
            for br in ("cp", "coupled"):
                b = min((r for r in study["runs"] if r["site"] == sk
                         and r["branch"] == br and r["rho"] != "hayne"),
                        key=lambda r: r["rmse_K"])
                winners_fc.append(b["flux_closure"])
        L.append(f"\\newcommand{{\\closurewin}}"
                 f"{{{100 * max(winners_fc):.2f}}}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    (OUT.parent / "poster_numbers.tex").write_text("\n".join(L) + "\n")
    print(f"  -> {OUT.parent / 'poster_numbers.tex'} ({len(L)} macros)")




def sites_composite(sens):
    """2x2: DEM shaded relief (top) + horizon polars (bottom), one panel."""
    dem, ppd = aogs.load_dem()            # finest available, memmapped (raw DN)
    lsrc = LightSource(azdeg=315, altdeg=35)
    fig = plt.figure(figsize=(POSTER_W, 4.9))
    for i, sk in enumerate(("A15", "A17")):
        s = sens["sites"][sk]
        ax = fig.add_subplot(2, 2, i + 1)
        half = 3.0
        r0 = int((90 - s["lat"] - half) * ppd)
        r1 = int((90 - s["lat"] + half) * ppd)
        c0 = int((s["lon"] + 180 - half) * ppd)
        c1 = int((s["lon"] + 180 + half) * ppd)
        shaded = lsrc.shade(dem[r0:r1, c0:c1] * aogs.DEM_SCALE_KM,
                            cmap=plt.get_cmap("gist_earth"),
                            blend_mode="soft", vert_exag=40)
        ax.imshow(shaded, extent=(s["lon"] - half, s["lon"] + half,
                                  s["lat"] - half, s["lat"] + half),
                  origin="upper")
        ax.plot(s["lon"], s["lat"], "o", color="white", ms=10,
                mec=SITE_COLOR[sk], mew=2.6)
        fmt_axis(ax, xlabel="longitude (\u00b0E)",
                 ylabel="latitude (\u00b0N)" if sk == "A15" else "",
                 title=f"Apollo {sk[1:]}")
    from lunar.constants import LUNATION_SECONDS
    for i, sk in enumerate(("A15", "A17")):
        s = sens["sites"][sk]
        ax = fig.add_subplot(2, 2, 3 + i, projection="polar")
        az = np.radians(np.asarray(s["horizon_az_deg"]))
        hor = np.asarray(s["horizon_deg"])
        ax.plot(np.append(az, az[0]), np.append(hor, hor[0]),
                color=SITE_COLOR[sk], lw=2.4)
        ax.fill(np.append(az, az[0]), np.append(hor, hor[0]),
                color=SITE_COLOR[sk], alpha=0.25)
        # sun path over one lunation (aogs_sensitivity.sun_track \u2014 the same
        # geometry that shadows the forcing). Only the low-elevation portion
        # near rise/set fits inside the polar range: exactly where the
        # horizon acts. Blocked samples (below the terrain horizon) in plum.
        rmax = max(1.35 * float(np.max(hor)), 6.0)
        tt = np.linspace(0.0, LUNATION_SECONDS, 20001)
        elev, A = aogs.sun_track(s["lat"], tt)
        hor_at = np.interp(A, np.asarray(s["horizon_az_deg"]),
                           hor, period=360.0)
        vis = (elev >= 0.0) & (elev <= rmax)
        clear, blocked = vis & (elev > hor_at), vis & (elev <= hor_at)
        for mask, col, lw_, lab in ((clear, C_CHAR, 1.5, "sun path"),
                                    (blocked, C_PLUM, 3.0, "sun blocked")):
            seg = np.where(mask, elev, np.nan)          # NaN-split segments
            ax.plot(np.radians(A), seg, color=col, lw=lw_, ls=":",
                    solid_capstyle="round", label=lab if i == 0 else None)
        ax.set_rmax(rmax)
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_title(f"horizon (max {s['horizon_max_deg']:.0f}\u00b0, "
                     f"loss {100 * s['insolation_energy_loss']:.2f}%)",
                     fontsize=9)
        ax.set_rlabel_position(200)
        ax.tick_params(labelsize=6.5)
        if i == 0:
            sun_handles, sun_labels = ax.get_legend_handles_labels()
    fig.tight_layout(h_pad=1.4)
    fig.legend(sun_handles, sun_labels, ncols=2, fontsize=8, frameon=True,
               edgecolor=C_GRID, loc="lower center",
               bbox_to_anchor=(0.5, -0.035))
    _save(fig, "poster_sites.pdf")


def sens_composite(study):
    """2x2: leverage boxplots (top) + boundary maps (bottom), one panel."""
    import matplotlib as mpl
    runs, meta = study["runs"], study["meta"]
    z1g, z2g = meta["z1_grid"], meta["z2_grid"]
    fig, axes = plt.subplots(2, 2, figsize=(POSTER_W, 4.6))
    for j, sk in enumerate(("A15", "A17")):
        ax = axes[0, j]
        data, colors = [], []
        for br in ("cp", "coupled"):
            data.append([r["rmse_K"] for r in runs if r["site"] == sk
                         and r["branch"] == br and r["rho"] != "hayne"])
            colors.append(C_TEAL if br == "cp" else SITE_COLOR[sk])
        base = next(r["rmse_K"] for r in runs
                    if r["site"] == sk and r["rho"] == "hayne")
        bp = ax.boxplot(data, tick_labels=["cp only", "coupled K"],
                        patch_artist=True, widths=0.5)
        for patch, c in zip(bp["boxes"], colors):
            patch.set_facecolor(c)
            patch.set_alpha(0.55)
        ax.axhline(base, color=C_CHAR, ls="--", lw=1.2)
        fmt_axis(ax, ylabel="RMSE (K)" if j == 0 else "",
                 title=f"Apollo {sk[1:]}")
        ax = axes[1, j]
        M = np.full((len(z2g), len(z1g)), np.nan)
        for a, z2 in enumerate(z2g):
            for b, z1 in enumerate(z1g):
                M[a, b] = min(r["rmse_K"] for r in runs
                              if r["site"] == sk and r["branch"] == "coupled"
                              and r["rho"] != "hayne"
                              and abs(r["z1_m"] - z1) < 1e-9
                              and abs(r["z2_m"] - z2) < 1e-9)
        im = ax.imshow(M, origin="lower", cmap="RdYlGn_r", aspect="auto")
        ax.set_xticks(range(len(z1g)), [f"{100 * v:.0f}" for v in z1g],
                      fontsize=8)
        ax.set_yticks(range(len(z2g)), [f"{100 * v:.0f}" for v in z2g],
                      fontsize=8)
        for a in range(len(z2g)):
            for b in range(len(z1g)):
                ax.text(b, a, f"{M[a, b]:.2f}", ha="center", va="center",
                        fontsize=8)
        fmt_axis(ax, xlabel="$z_1$ (cm)",
                 ylabel="$z_2$ (cm)" if j == 0 else "", title="")
    fig.tight_layout(h_pad=1.2)
    _save(fig, "poster_sens.pdf")




def transfer_matrix():
    """3x2 RMSE matrix: {A15 structure, A17 structure, homogeneous} x
    {evaluated at A15, at A17} — the cross-site 'physics, not curve-
    fitting' argument as one glance. Values from aogs_crossite.json
    (writer: aogs_crossite.py)."""
    x = json.loads((ROOT / "results" / "aogs_crossite.json").read_text())
    M = np.array([[x["native_best"]["A15"], x["A15_config_at_A17"]],
                  [x["A17_config_at_A15"], x["native_best"]["A17"]],
                  [x["A15_homogeneous"], x["A17_homogeneous"]]])
    rows = ["A15 structure", "A17 structure", "homogeneous"]
    cols = ["at Apollo 15", "at Apollo 17"]
    fig, ax = plt.subplots(figsize=(POSTER_W * 0.62, 2.6),
                           constrained_layout=True)
    im = ax.imshow(M, cmap="RdYlGn_r", aspect="auto", vmin=0.3, vmax=3.8)
    ax.set_xticks(range(2), cols)
    ax.set_yticks(range(3), rows)
    ax.tick_params(length=0)
    for a in range(3):
        for b in range(2):
            dark = M[a, b] > 3.0 or M[a, b] < 0.55     # only the saturated
            # RdYlGn_r extremes are dark enough for white text; mid-scale
            # cells (pale yellow) need black
            ax.text(b, a, f"{M[a, b]:.2f}", ha="center", va="center",
                    fontsize=13, fontweight="bold",
                    color="white" if dark else C_CHAR)
    fig.colorbar(im, ax=ax, shrink=0.92).set_label(
        "deep-sensor RMSE (K)", fontsize=9)
    _save(fig, "poster_transfer.pdf")


def bootstrap_panel():
    """10k-draw bootstrap (s7_winner_bootstrap): best-RMSE 95% CIs for both
    branches vs the homogeneous baseline. The improvement is robust (CIs far
    left of homogeneous) even where the exact winning triple is not (the
    stability % beside each bar)."""
    boot = json.loads((ROOT / "results" / "aogs_winner_bootstrap.json").read_text())
    xs = json.loads((ROOT / "results" / "aogs_crossite.json").read_text())
    homo = {"A15": xs["A15_homogeneous"], "A17": xs["A17_homogeneous"]}
    fig, axes = plt.subplots(1, 2, figsize=(POSTER_W, 1.05),
                             constrained_layout=True)
    for ax, sk in zip(axes, ("A15", "A17")):
        his = []
        for br, yy, col in (("coupled", 1.0, SITE_COLOR[sk]), ("cp", 0.0, C_TEAL)):
            e = boot[f"{sk}_{br}"]
            med = e["best_rmse_median_K"]
            lo, hi = e["best_rmse_ci95_K"]
            ax.errorbar([med], [yy], xerr=[[med - lo], [hi - med]], fmt="o",
                        color=col, ms=9, mfc="white", mew=2.2, elinewidth=2.6,
                        capsize=5, zorder=5)
            his.append(hi)
        maxhi, h = max(his), homo[sk]
        # Zoom the x-axis to the CI points so they stay large. If the homogeneous
        # baseline sits close (A15), keep the usual dashed line; if it is far
        # off-scale (A17, homo=3.76 vs points <0.5), mark it with an off-scale
        # arrow instead of stretching the axis and crushing the points.
        if h <= maxhi * 1.5:
            up = h * 1.12
            ax.axvline(h, color=C_CHAR, ls="--", lw=1.5)
        else:
            up = maxhi * 1.9
            # homogeneous is off-scale to the right: mark it in the empty
            # top-right corner with a right-pointing arrow (keeps the points big).
            ax.annotate("", xy=(up * 0.99, 1.42), xytext=(up * 0.82, 1.42),
                        arrowprops=dict(arrowstyle="-|>", color=C_CHAR, lw=1.4))
            ax.text(up * 0.80, 1.42, f"homog. {h:.2f} K", fontsize=7,
                    color=C_CHAR, ha="right", va="center")
        ax.set_yticks([0.0, 1.0]); ax.set_yticklabels(["cp", "coupled"])
        ax.set_ylim(-0.6, 1.6)
        ax.set_xlim(0.0, up)
        fmt_axis(ax, xlabel="best-RMSE 95% CI (K)",
                 title=f"Apollo {sk[1:]}")
        fig.canvas.draw()
        assert_no_overlap(ax)
    _save(fig, "poster_bootstrap.pdf")


def density_mini(study):
    """Compact rho(z): continuous Hayne vs the winning 3-layer staircases."""
    from lunar.properties import density_hayne
    runs, meta = study["runs"], study["meta"]
    z = np.linspace(0, 1.0, 300)
    fig, ax = plt.subplots(figsize=(POSTER_W, 2.1), constrained_layout=True)
    for sk, ls_ in (("A15", "-"), ("A17", (0, (4, 2)))):
        best = min((r for r in runs if r["site"] == sk
                    and r["branch"] == "coupled" and r["rho"] != "hayne"),
                   key=lambda r: r["rmse_K"])
        r1, r2, r3 = best["rho"]
        z1, z2 = best["z1_m"], best["z2_m"]
        prof = np.where(z < z1, r1, np.where(z < z2, r2, r3))
        ax.step(prof, z, where="post", color=SITE_COLOR[sk], lw=2.6,
                linestyle=ls_,
                label=(f"best {sk}: {int(r1)}/{int(r2)}/{int(r3)}, "
                       f"z={100*z1:.0f}/{100*z2:.0f} cm"))
    ax.plot(density_hayne(z), z, ":", color=C_TEAL, lw=2.2,
            label="Hayne continuous")
    ax.invert_yaxis()
    fmt_axis(ax, xlabel=r"density (kg m$^{-3}$)", ylabel="depth (m)",
             title="")
    # the deep/low-density corner (lower left) is empty — all three curves
    # sit at rho >= 1500 below ~0.3 m — so the legend fits INSIDE, killing
    # the dead right margin the outside legend used to leave. The overlap
    # guard verifies the pocket really is empty.
    ax.legend(fontsize=8, frameon=True, edgecolor=C_GRID, loc="lower left")
    fig.canvas.draw()
    assert_no_overlap(ax)
    _save(fig, "poster_density.pdf")


def main():
    sens = json.loads((ROOT / "results" / "aogs_sensitivity.json")
                      .read_text())
    dem_panels(sens)
    horizon_panels(sens)
    forcing_panels(sens)
    sites_composite(sens)
    study_p = ROOT / "results" / "aogs_density_study.json"
    if study_p.exists():
        study = json.loads(study_p.read_text())
        profile_panels(study)
        leverage_panels(study)
        boundary_panels(study)
        sens_composite(study)
        density_mini(study)
        if (ROOT / "results" / "aogs_crossite.json").exists():
            transfer_matrix()
        if (ROOT / "results" / "aogs_winner_bootstrap.json").exists():
            bootstrap_panel()
        emit_numbers(sens, study)
    else:
        emit_numbers(sens, None)
        print("  (aogs_density_study.json not ready -- profile/leverage/"
              "boundary panels skipped)")


if __name__ == "__main__":
    main()
