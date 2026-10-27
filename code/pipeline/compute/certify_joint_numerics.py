"""Numerical certification of the reported K_d* (SI Table S3).

The solver tests of the SI (now Table S3) were run in July on the temperature-only fit
at the albedos then in use (0.131 / 0.137), and several came from one-off
studies. This script certifies THE REPORTED QUANTITY instead: the joint-fit
K_d* (compute_joint_albedo_fit.py, letter Eq. 11), found exactly as the joint
fit finds it -- the objective J (sensor temperatures, surface mean and the
two annual-wave diffusivities) along K_d at the fit's albedo grid node, its
minimum refined with the same three-point parabola -- with one numerical
choice changed at a time:

  * time step halved twice (1800 -> 900 -> 450 s);
  * a finer grid (first cell 1 mm, growing 4 % per cell);
  * anchor depth 0.45 and 0.70 m (production 0.55 m; Step A always reaches
    0.15 m below the anchor, as in production);
  * shallow-run length 64 and 128 lunations (production 96);
  * Step A on the full 5-m column instead of the top 0.70 m;
  * starting temperature 240 and 260 K (production 250 K);
  * K_d spacing: the parabola refined on nodes 0.05 apart instead of the
    production 0.25.

The nominal case must reproduce results/joint_albedo_fit.json to 1e-6
mW m^-1 K^-1, or the script stops.

Reads:  results/joint_albedo_fit.json, the Apollo HFE data (via the joint fit)
Writes: results/joint_numerics_certification.json
Runtime: ~3 min on 5 workers.

Run with:
    python pipeline/compute/certify_joint_numerics.py
"""
from __future__ import annotations
import functools, json, sys, pathlib, time
from multiprocessing import Pool
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src")); sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np
import compute_joint_albedo_fit as jf

N_WORKERS = 5
SITES_ = ("A15", "A17")
SENSOR_Z = np.array([0.8, 1.0, 1.4, 2.4])          # profile comparison depths [m]
VARIANTS = {
    "nominal":        {},
    "dt_900":         dict(dt=900.0),
    "dt_450":         dict(dt=450.0),
    "grid_fine":      dict(grid=dict(z_max=5.0, dz0=0.001, growth=0.04)),
    "anchor_0.45":    dict(z_anchor=0.45),
    "anchor_0.70":    dict(z_anchor=0.70),
    "n_inner_64":     dict(n_inner=64),
    "n_inner_128":    dict(n_inner=128),
    "full_column_A":  dict(step_a_depth_m=5.0),
    "start_240K":     dict(T_guess=240.0),
    "start_260K":     dict(T_guess=260.0),
    "kd_step_0.05":   dict(kd_step=0.05e-3),
}


def nodes(site, step=None):
    """The fit's albedo node and five K_d nodes around its minimum: the production
    grid's, or ``step`` apart around the reported K_d*."""
    d = json.loads((_REPO / "results" / "joint_albedo_fit.json").read_text())["sites"][site]["with_diffusivity"]
    J = np.array(d["J_map"])
    ia, ik = np.unravel_index(int(np.argmin(J)), J.shape)
    kd = jf.KD_GRID[ik - 2:ik + 3].copy() if step is None else \
        np.round(d["best"]["kd_star_mW"] * 1e-3 / step) * step + np.arange(-2, 3) * step
    return float(jf.A_GRID[ia]), kd, float(d["best"]["kd_star_mW"])


def solve_variant(job):
    """J ingredients at the five K_d nodes for one (site, variant)."""
    site, name = job
    ov = VARIANTS[name]
    from lunar.config import SITES, GRID, DT_STEP, HAYNE
    from lunar.constants import RHO_SURFACE, RHO_DEEP
    from lunar.grid import make_geometric_grid
    from lunar.solver import periodic_time_grid, standard_insolation
    from lunar.properties import conductivity_hayne, specific_heat, density_hayne
    from lunar.equilibrium import solve_periodic_equilibrium
    cfg = SITES[site]
    A, kd_nodes, _ = nodes(site, ov.get("kd_step"))
    z_obs, _ = jf.observed(site)
    ks, H, chi = HAYNE["K_S"], HAYNE["H"], HAYNE["CHI"]
    G = make_geometric_grid(**ov.get("grid", GRID))
    t = periodic_time_grid(ov.get("dt", DT_STEP))
    S = standard_insolation(cfg["lat"], t)
    rho = density_hayne(G.z_mid, rho_s=RHO_SURFACE, rho_d=RHO_DEEP, H=H)
    probes = jf.KAPPA_OBS[site]
    Tz, Ts, kap, Tsens, n_outer = [], [], [], [], []
    for kd in kd_nodes:
        K = functools.partial(conductivity_hayne, Ks=ks, Kd=float(kd), H=H, chi=chi)
        # the property set of lunar.equilibrium.solve_hayne_equilibrium (as the joint fit calls it)
        eq = solve_periodic_equilibrium(
            grid=G, t=t, insolation=S, albedo=A, emissivity=cfg["emissivity"], Q_b=cfg["Q_BASAL"],
            K_func=K, cp_func=functools.partial(specific_heat, model="hayne"),
            rho_func=functools.partial(density_hayne, rho_s=RHO_SURFACE, rho_d=RHO_DEEP, H=H),
            T_guess=ov.get("T_guess", cfg["T_MEAN_EFF"]), z_anchor=ov.get("z_anchor"),
            n_inner=ov.get("n_inner"), step_a_depth_m=ov.get("step_a_depth_m"),
            hayne_params=(ks, float(kd), H, chi, RHO_SURFACE, RHO_DEEP))
        Tz.append(np.interp(z_obs, G.z_mid, eq.T_mean))
        Ts.append(float(eq.out.T_surface.mean()))
        kz = K(eq.T_mean, G.z_mid) / (rho * specific_heat(eq.T_mean, model="hayne")) * 1e8
        kap.append([float(np.interp(np.linspace(z1, z2, 200), G.z_mid, kz).mean()) for z1, z2, _, _ in probes])
        Tsens.append(np.interp(SENSOR_Z, G.z_mid, eq.T_mean))
        n_outer.append(eq.n_outer)
    return site, name, np.array(Tz), np.array(Ts), np.array(kap), np.array(Tsens), n_outer


def kd_star(site, Tz, Ts, kap, step=None):
    """Vertex of J along K_d at the fit's albedo node, as compute_joint_albedo_fit.best_point."""
    _, kd_nodes, _ = nodes(site, step)
    _, Tobs = jf.observed(site)
    kobs = np.array([p[2] for p in jf.KAPPA_OBS[site]]); ksig = np.array([p[3] for p in jf.KAPPA_OBS[site]])
    J, _ = jf.objective(Tz, Tobs, Ts, jf.TS_OBS[site], kap=kap, kobs=kobs, ksig=ksig)
    i = int(np.argmin(J))
    v, _ = jf.vertex(kd_nodes, J, i)
    return v * 1e3, bool(0 < i < len(J) - 1)


def main():
    t0 = time.time()
    jobs = [(s, v) for s in SITES_ for v in VARIANTS]
    res = {}
    from lunar.progress import bar
    with Pool(N_WORKERS) as pool:
        for site, name, Tz, Ts, kap, Tsens, n_outer in bar(pool.imap_unordered(solve_variant, jobs), total=len(jobs), desc="variants", unit="variants"):
            res[(site, name)] = (Tz, Ts, kap, Tsens, n_outer)
    out = dict(meta=dict(purpose="numerical certification of the joint-fit K_d* (SI Table S3)",
                         objective="J of compute_joint_albedo_fit (with diffusivity) along K_d at the fit's albedo node; "
                                   "3-point parabola vertex, as best_point",
                         variants=VARIANTS, sensor_depths_m=SENSOR_Z.tolist()), sites={})
    for s in SITES_:
        A, kd_nodes, reported = nodes(s)
        row = dict(albedo_node=A, kd_nodes_mW=(kd_nodes * 1e3).tolist(), reported_kd_star_mW=reported, variants={})
        Tsens_nom = res[(s, "nominal")][3]
        for v in VARIANTS:
            Tz, Ts, kap, Tsens, n_outer = res[(s, v)]
            k, inside = kd_star(s, Tz, Ts, kap, VARIANTS[v].get("kd_step"))
            same_nodes = "kd_step" not in VARIANTS[v]       # profiles comparable only at the same K_d
            row["variants"][v] = dict(kd_star_mW=k, minimum_inside_window=inside, n_outer=n_outer,
                                      max_abs_dT_sensors_vs_nominal_K=float(np.max(np.abs(Tsens - Tsens_nom)))
                                      if same_nodes else None)
        nom = row["variants"]["nominal"]["kd_star_mW"]
        assert abs(nom - reported) < 1e-6, f"{s}: nominal {nom} does not reproduce the joint fit {reported}"
        d = {v: row["variants"][v]["kd_star_mW"] - nom for v in VARIANTS}
        row["delta_kd_mW"] = d
        row["summary"] = dict(
            dt_per_halving_max=max(abs(d["dt_900"]), abs(row["variants"]["dt_450"]["kd_star_mW"] - row["variants"]["dt_900"]["kd_star_mW"])),
            grid_fine=abs(d["grid_fine"]),
            anchor_max=max(abs(d["anchor_0.45"]), abs(d["anchor_0.70"])),
            n_inner_max=max(abs(d["n_inner_64"]), abs(d["n_inner_128"])),
            full_column=abs(d["full_column_A"]),
            start_kd_max=max(abs(d["start_240K"]), abs(d["start_260K"])),
            start_profile_max_K=float(np.max(np.abs(res[(s, "start_240K")][3] - res[(s, "start_260K")][3]))),
            kd_spacing=abs(d["kd_step_0.05"]),
            all_max=max(abs(x) for x in d.values()))
        out["sites"][s] = row
        print(f"\n{s}: nominal K_d* {nom:.4f} (joint fit {reported:.4f}); albedo node {A}")
        for v in VARIANTS:
            x = row["variants"][v]
            dT = x["max_abs_dT_sensors_vs_nominal_K"]
            print(f"  {v:14s} K_d* {x['kd_star_mW']:.4f}  dK {d[v]:+.4f}  outer {x['n_outer'][2]}"
                  + (f"  max|dT| sensors {dT*1e3:.3f} mK" if dT is not None else "")
                  + ("" if x["minimum_inside_window"] else "  [minimum at window edge]"))
        print("  summary:", {k: round(v, 5) for k, v in row["summary"].items()})
    out["meta"]["runtime_s"] = round(time.time() - t0, 1)
    p = _REPO / "results" / "joint_numerics_certification.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"\nwrote {p.relative_to(_REPO)} in {time.time()-t0:.0f} s")


if __name__ == "__main__":
    main()
