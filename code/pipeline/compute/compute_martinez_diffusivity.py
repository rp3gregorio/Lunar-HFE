#!/usr/bin/env python3
"""Can density alone give the measured diffusivities? (letter Section 4.1; 2026-10-24)

The Martinez & Siegler (2021) conductivity rises with density, K(T, rho), so a
denser regolith conducts better. This script asks how dense the deep regolith
would have to be for that model to reproduce the annual-wave diffusivities
measured at the probes (Langseth et al. 1976, Table 1).

For each site, the Martinez & Siegler model is solved once at the joint-fit
albedo and the published density (rho_d = 1800 kg/m^3) for its mean temperature
profile T(z). The model diffusivity K(T, rho) / (rho c_p(T)) is then averaged
over each probe's depth range, as in compute_joint_albedo_fit.py, with the deep
density rho_d of the shared profile (Hayne et al. 2017, Eq. A2) swept from 1600
to 3300 kg/m^3. T(z) is held at its 1800 kg/m^3 shape: the diffusivity depends
on temperature only through c_p and the T^3 term, a few-K change in T(z)
moves it by well under 1 %.

Reported per site: the probe-mean model diffusivity at 1800 kg/m^3, at the top
of the Apollo drill-core densities (1990; Carrier et al. 1991, p. 492) and at the
top of the in-situ estimates of Langseth et al. (1976) (A15 1900, A17 2090), and
the density at which it equals the mean of the two measured diffusivities.

Reads:  the Apollo record (via retrieve_kd), config.SITES, results/joint_albedo_fit.json
Writes: results/martinez_diffusivity.json
Runtime: about 2 min (one Martinez solve per site).

Run with:
    python pipeline/compute/compute_martinez_diffusivity.py
"""
from __future__ import annotations
import copy
import json
import sys
import pathlib

import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import retrieve_kd as rk                                         # noqa: E402
import compute_joint_albedo_fit as jf                            # noqa: E402
from lunar.config import SITES, HAYNE                            # noqa: E402
from lunar.constants import RHO_SURFACE                          # noqa: E402
from lunar.properties import conductivity_martinez, density_hayne, specific_heat   # noqa: E402

RHO_GRID = np.arange(1600.0, 3300.1, 5.0)          # deep density rho_d [kg/m^3]
RHO_CORES_TOP = 1990.0                               # Carrier et al. (1991) p. 492: A15 1620-1930, A17 1740-1990
RHO_LANGSETH_TOP = {"A15": 1900.0, "A17": 2090.0}    # Langseth et al. (1976) p. 3154: 1750-1900, 1830-2090


def kappa_probes(z, T, rho_d, probes):
    """Martinez & Siegler diffusivity [1e-4 cm^2/s], averaged over each probe's depth range."""
    rho = density_hayne(z, rho_s=RHO_SURFACE, rho_d=rho_d, H=HAYNE["H"])
    k = conductivity_martinez(T, rho=rho) / (rho * specific_heat(T, model="hayne")) * 1e8
    return [float(np.interp(np.linspace(z1, z2, 200), z, k).mean()) for z1, z2, _, _ in probes]


def main():
    out = dict(meta=dict(purpose=__doc__.splitlines()[0], rho_grid_kg_m3=[RHO_GRID[0], RHO_GRID[-1], 5.0],
                         kappa_units="1e-4 cm^2 s^-1", rho_cores_top_kg_m3=RHO_CORES_TOP), sites={})
    joint = json.loads((_REPO / "results" / "joint_albedo_fit.json").read_text())["sites"]
    for s in ("A15", "A17"):
        cfg = copy.deepcopy(SITES[s])
        cfg["albedo"] = joint[s]["with_diffusivity"]["best"]["A"]     # the joint-fit albedo
        zm, Tm = rk.run_with(cfg, k_model="martinez")
        zm, Tm = np.asarray(zm, float), np.asarray(Tm, float)
        probes = jf.KAPPA_OBS[s]
        kap = np.array([kappa_probes(zm, Tm, r, probes) for r in RHO_GRID])     # (n_rho, n_probe)
        mean_model = kap.mean(axis=1)
        obs = [p[2] for p in probes]
        mean_obs = float(np.mean(obs))
        at = lambda r: [float(np.interp(r, RHO_GRID, kap[:, p])) for p in range(len(probes))]
        needed = float(np.interp(mean_obs, mean_model, RHO_GRID)) if mean_model[-1] >= mean_obs else None
        per_probe = [float(np.interp(o, kap[:, p], RHO_GRID)) if kap[-1, p] >= o else None for p, o in enumerate(obs)]
        out["sites"][s] = dict(albedo=cfg["albedo"], kappa_obs=obs, kappa_obs_mean=mean_obs,
                               kappa_model_1800=at(1800.0), kappa_model_cores_top=at(RHO_CORES_TOP),
                               kappa_model_langseth_top=at(RHO_LANGSETH_TOP[s]),
                               rho_langseth_top_kg_m3=RHO_LANGSETH_TOP[s],
                               rho_d_for_mean_obs_kg_m3=needed, rho_d_for_each_probe_kg_m3=per_probe)
        print(f"{s}: kappa at 1800 {np.round(at(1800.0), 3)}, at {RHO_CORES_TOP:.0f} {np.round(at(RHO_CORES_TOP), 3)}; "
              f"measured {obs} (mean {mean_obs:.3f}) needs rho_d {needed:.0f} kg/m^3; "
              f"each probe {[None if v is None else round(v) for v in per_probe]}", flush=True)
    p = _REPO / "results" / "martinez_diffusivity.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
