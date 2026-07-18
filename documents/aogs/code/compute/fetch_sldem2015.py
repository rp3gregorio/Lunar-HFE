"""Fetch SLDEM2015 (512 ppd, 59 m/px) crops around A15/A17 via HTTP range,
store small patches, and compute the finer horizons vs the 16 ppd result."""
import sys, json, subprocess, os, pathlib
import numpy as np
sys.path.insert(0, "/Users/rp3gregorio/Developer/Lunar-Clean/code/src")
sys.path.insert(0, "/Users/rp3gregorio/Developer/Lunar-Clean/code/pipeline/compute/aogs")
import s1_sensitivity as base
from lunar.config import SITES, DT_STEP
from lunar.solver import periodic_time_grid

URL = ("https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/"
       "data/sldem2015/tiles/float_img/sldem2015_512_00n_30n_000_045_float.img")
PPD, NCOL, R = 512, 23040, 1737.4
ROWBYTES = NCOL * 4
LINE_OFF = 15359.5          # row = LINE_OFF - lat*ppd  (row 0 = 30N)
OUT = pathlib.Path("/Users/rp3gregorio/Developer/Lunar-Clean/code/data/lola/sldem2015")
OUT.mkdir(parents=True, exist_ok=True)
HALF_LAT, HALF_LON = 1.5, 2.0     # crop half-widths (deg)

def fetch_crop(sk, lat0, lon0):
    r_top = int(np.floor(LINE_OFF - (lat0 + HALF_LAT) * PPD))
    r_bot = int(np.ceil(LINE_OFF - (lat0 - HALF_LAT) * PPD))
    b0, b1 = r_top * ROWBYTES, (r_bot + 1) * ROWBYTES - 1
    print(f"{sk}: rows {r_top}-{r_bot} ({(b1-b0)/1e6:.0f} MB range) ...", flush=True)
    tmp = f"/tmp/sldem_{sk}.f32"
    subprocess.run(["curl", "-sL", "--fail", "--max-time", "600",
                    "-r", f"{b0}-{b1}", "-o", tmp, URL], check=True)
    band = np.fromfile(tmp, dtype="<f4").reshape(-1, NCOL)     # km topography
    os.remove(tmp)
    lat_top = (LINE_OFF - r_top) / PPD
    c0 = int((lon0 - HALF_LON) * PPD); c1 = int((lon0 + HALF_LON) * PPD)
    crop = np.ascontiguousarray(band[:, c0:c1])
    lon_left = c0 / PPD
    crop.astype("<f4").tofile(OUT / f"{sk}.f32")
    (OUT / f"{sk}.json").write_text(json.dumps(dict(
        shape=list(crop.shape), ppd=PPD, lat_top=lat_top, lon_left=lon_left,
        units="km_topography", site=[lat0, lon0])))
    print(f"   saved crop {crop.shape} ({crop.nbytes/1e6:.1f} MB), "
          f"lat_top={lat_top:.3f} lon_left={lon_left:.3f}")
    return crop, lat_top, lon_left

def horizon(crop, lat_top, lon_left, lat0, lon0, r_max=40.0):
    dr = 2 * np.pi * R / 360.0 / PPD          # one pixel (~0.059 km)
    az = np.linspace(0, 360, 90, endpoint=False)
    def samp(lat, lon):
        rr = (lat_top - lat) * PPD; cc = (lon - lon_left) * PPD
        r0 = np.clip(np.floor(rr).astype(int), 0, crop.shape[0] - 2)
        c0 = np.clip(np.floor(cc).astype(int), 0, crop.shape[1] - 2)
        fr, fc = np.clip(rr - r0, 0, 1), np.clip(cc - c0, 0, 1)
        return ((1-fr)*(1-fc)*crop[r0, c0] + (1-fr)*fc*crop[r0, c0+1]
                + fr*(1-fc)*crop[r0+1, c0] + fr*fc*crop[r0+1, c0+1])
    h0 = float(samp(lat0, lon0)); r = np.arange(dr, r_max + dr, dr)
    hor = np.zeros_like(az)
    for i, a in enumerate(np.radians(az)):
        dlat = np.degrees((r / R) * np.cos(a))
        dlon = np.degrees((r / R) * np.sin(a) / max(np.cos(np.radians(lat0)), 1e-6))
        elev = np.degrees(np.arctan2(samp(lat0+dlat, lon0+dlon) - h0 - r**2/(2*R), r))
        hor[i] = max(0.0, float(elev.max()))
    return az, hor

t = periodic_time_grid(DT_STEP)
print(f"{'site':4s} {'DEM':>10s} {'px':>7s} {'max_hor':>8s} {'mean_hor':>9s} {'loss%':>7s}")
for sk in ("A15", "A17"):
    s = SITES[sk]
    crop, lat_top, lon_left = fetch_crop(sk, s["lat"], s["lon"])
    az, hor = horizon(crop, lat_top, lon_left, s["lat"], s["lon"])
    S_std = base.standard_insolation(s["lat"], t)
    S_sh = base.shadowed_insolation(s["lat"], t, az, hor)
    loss = 100 * (1 - S_sh.sum() / S_std.sum())
    print(f"{sk:4s} {'SLDEM2015':>10s} {'59 m':>7s} {hor.max():7.1f}° "
          f"{hor.mean():8.1f}° {loss:6.2f}%   (16 ppd was: "
          f"{'14.0/1.16' if sk=='A15' else '10.1/0.18'})")
