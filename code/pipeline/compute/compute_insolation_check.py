"""Real against idealized sunlight at the two Apollo sites (2026-10-23).

The model (letter Section 2.2, Equation 1) is driven by an idealized cycle:
the Sun rises and sets once per mean synodic month, at the site latitude,
with the solar constant at 1 AU. This script measures what that leaves out:
the mean of the real direct sunlight on a flat surface at each site over the
five full years 1972-1976, from the Sun's position in the Moon-fixed frame
(SPICE: DE440, MOON_ME), including the Sun-Moon distance.

Two effects lower the real mean below the idealized one:
  * at the near-side sites the Sun is up near full moon, when the Moon lies
    beyond the Earth and is farther from the Sun (about -0.4 %);
  * the Moon's small obliquity and its librations (about -0.2 %).
The fitted albedo absorbs the difference (letter Section 2.2).

Writes: results/insolation_check.json
Runtime: about 1 min (hourly samples, five years).

Run with:
    python pipeline/compute/compute_insolation_check.py
"""
from __future__ import annotations
import json
import pathlib
import sys

import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

from lunar import ephem
from lunar.config import SITES

S0 = 1361.0                  # W m^-2 at 1 AU (Kopp & Lean, 2011), as in the model
AU_KM = 149597870.7
START, END = "1972-01-01T00:00:00", "1977-01-01T00:00:00"   # five full years


def main():
    ephem._furnish_kernels()
    import spiceypy as spice  # type: ignore[import-not-found]

    et = np.arange(spice.str2et(START), spice.str2et(END), 3600.0)
    pos = np.array([spice.spkpos("SUN", float(t), "MOON_ME", "LT+S", "MOON")[0] for t in et])
    r_au = np.linalg.norm(pos, axis=1) / AU_KM
    sun = pos / (r_au * AU_KM)[:, None]
    out = {"period": [START[:10], END[:10]], "sampling_h": 1.0, "S0_W_m2": S0, "sites": {}}
    for s in ("A15", "A17"):
        lat, lon = np.deg2rad(SITES[s]["lat"]), np.deg2rad(SITES[s]["lon"])
        up = np.array([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
        mu = np.clip(sun @ up, 0.0, None)                      # cosine of the solar zenith angle, day side
        real = float(np.mean(S0 * mu / r_au**2))
        real_1au = float(np.mean(S0 * mu))                     # the same geometry with the Sun at 1 AU
        ideal = float(S0 * np.cos(lat) / np.pi)                # cycle mean of max(0, S0 cos(lat) cos(2 pi t / P))
        out["sites"][s] = dict(lat_deg=SITES[s]["lat"], mean_real_W_m2=real, mean_real_at_1AU_W_m2=real_1au,
                               mean_idealized_W_m2=ideal,
                               real_minus_ideal_pct=100 * (real / ideal - 1),
                               distance_part_pct=100 * (real / real_1au - 1),
                               geometry_part_pct=100 * (real_1au / ideal - 1))
    path = _REPO / "results" / "insolation_check.json"
    path.write_text(json.dumps(out, indent=1))
    for s, d in out["sites"].items():
        print(f"{s}: real {d['mean_real_W_m2']:.2f} vs idealized {d['mean_idealized_W_m2']:.2f} W m^-2 "
              f"({d['real_minus_ideal_pct']:+.2f} %: distance {d['distance_part_pct']:+.2f} %, "
              f"geometry {d['geometry_part_pct']:+.2f} %)")
    print(f"wrote {path.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
