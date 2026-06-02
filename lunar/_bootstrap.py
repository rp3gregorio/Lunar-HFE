"""Notebook bootstrap helpers.

Lets a user open any notebook in this repo and click "Run All" without
needing to know anything about venvs, pip, git, or data downloads. The
bootstrap cell at the top of each notebook imports this module and calls
`ensure_lunar()` (and optionally `ensure_data(...)`). Everything else is
handled automatically.

Design goals
------------
* Self-healing: works regardless of which Python/kernel the notebook was
  launched with, as long as that kernel can `pip install`.
* No venv required: if the `lunar` package isn't importable, we put the
  repo root on ``sys.path`` directly, bypassing ``pip install -e .``.
* Offline-tolerant: if data downloads fail, the calling notebook should
  degrade gracefully (each notebook guards its data-dependent cells).
* Zero third-party deps at import time — only stdlib.
"""

from __future__ import annotations

import importlib
import pathlib
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Iterable

# Python's default urllib User-Agent gets a 403 from several PDS servers.
# Pretend to be a normal Mac browser — matches what `curl` sends by default.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Safari/605.1.15"
)


# ---------------------------------------------------------------------------
# Path + package bootstrap
# ---------------------------------------------------------------------------


def find_repo_root(start: pathlib.Path | None = None) -> pathlib.Path:
    """Walk upward from ``start`` until we find the Lunar-V2 repo root.

    The repo root is identified by the presence of both ``pyproject.toml``
    and a ``lunar/`` package directory.
    """
    here = (start or pathlib.Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "lunar" / "__init__.py"
        ).is_file():
            return candidate
    raise RuntimeError(
        f"Could not locate Lunar-V2 repo root starting from {here}. "
        "Run this notebook from inside a cloned Lunar-V2 checkout."
    )


def _pip_install(*pkgs: str, quiet: bool = True) -> None:
    """Install packages into *this* kernel's Python via ``sys.executable``.

    Using ``sys.executable`` guarantees the install lands in the same
    environment the notebook is running under, no matter which kernel the
    user picked.
    """
    cmd = [sys.executable, "-m", "pip", "install"]
    if quiet:
        cmd.append("-q")
    cmd.extend(pkgs)
    subprocess.check_call(cmd)


def ensure_packages(packages: Iterable[tuple[str, str]]) -> list[str]:
    """Make sure each ``(pip_name, import_name)`` pair is importable.

    Installs any that are missing. Returns the list of packages that were
    actually installed (useful for logging).
    """
    installed: list[str] = []
    for pip_name, import_name in packages:
        try:
            importlib.import_module(import_name)
        except ImportError:
            print(f"  installing {pip_name} ...")
            _pip_install(pip_name)
            installed.append(pip_name)
    return installed


def ensure_lunar(extra: Iterable[str] = ()) -> pathlib.Path:
    """One-stop bootstrap for notebook 00/01/02/03.

    1. Locate the repo root and put it on ``sys.path`` so
       ``import lunar`` works without ``pip install -e .``.
    2. Install the core third-party deps (numpy, scipy, numba, matplotlib)
       plus anything in ``extra`` (e.g. ``"rasterio"``, ``"spiceypy"``).
    3. Print the Python executable and the lunar package location so the
       user can confirm the kernel is correctly wired.

    Parameters
    ----------
    extra : iterable of str, optional
        Pip names of additional packages to ensure. Each entry may be a
        ``(pip_name, import_name)`` tuple if the two names differ; a bare
        string is treated as both.

    Returns
    -------
    pathlib.Path
        The repo root (also added to ``sys.path``).
    """
    repo = find_repo_root()
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))

    core = [
        ("numpy", "numpy"),
        ("scipy", "scipy"),
        ("numba", "numba"),
        ("matplotlib", "matplotlib"),
    ]
    extras: list[tuple[str, str]] = []
    for item in extra:
        if isinstance(item, tuple):
            extras.append(item)
        else:
            extras.append((item, item))

    print("Lunar-V2 notebook bootstrap")
    print("  python :", sys.executable)
    print("  repo   :", repo)
    installed = ensure_packages(core + extras)
    if not installed:
        print("  deps   : all present")

    import lunar  # noqa: F401

    print("  lunar  :", lunar.__file__)
    return repo


# ---------------------------------------------------------------------------
# Data downloads
# ---------------------------------------------------------------------------


def _download(url: str, dest: pathlib.Path, min_bytes: int = 1024) -> bool:
    """Download ``url`` to ``dest`` unless the file already looks complete.

    Tries ``curl -L`` first (always available on macOS/Linux, handles
    redirects and sends a normal User-Agent). Falls back to ``urllib``
    with a spoofed browser User-Agent when curl is absent (e.g. Windows
    without WSL).

    Returns True if the file exists and is >= ``min_bytes`` after the call.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size >= min_bytes:
        return True

    print(f"  fetching {dest.name} ...")
    dest_tmp = dest.with_suffix(dest.suffix + ".part")

    # --- curl path (preferred) ---
    if shutil.which("curl"):
        try:
            subprocess.check_call(
                ["curl", "-fsSL", "--retry", "3", "-o", str(dest_tmp), url],
                timeout=600,
            )
            dest_tmp.rename(dest)
        except (subprocess.CalledProcessError, OSError) as exc:
            print(f"    curl failed: {exc}")
            dest_tmp.unlink(missing_ok=True)
        else:
            if dest.is_file() and dest.stat().st_size >= min_bytes:
                return True
            print(f"    file too small after curl ({dest.stat().st_size} B)")
            dest.unlink(missing_ok=True)

    # --- urllib fallback ---
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            dest_tmp.write_bytes(resp.read())
        dest_tmp.rename(dest)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        print(f"    FAILED: {exc}")
        dest_tmp.unlink(missing_ok=True)
        return False

    ok = dest.is_file() and dest.stat().st_size >= min_bytes
    if not ok:
        print(f"    file too small ({dest.stat().st_size if dest.exists() else 0} B)")
    return ok


def ensure_spice_kernels(repo_root: pathlib.Path | None = None) -> bool:
    """Download the 6 SPICE kernels needed by ``lunar.ephem`` if missing.

    Total size ~46 MB. Returns True iff all 6 are present after the call.
    """
    repo = repo_root or find_repo_root()
    spice_dir = repo / "data" / "spice"
    base = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels"
    kernels = [
        (f"{base}/lsk/naif0012.tls", "naif0012.tls"),
        (f"{base}/pck/pck00011.tpc", "pck00011.tpc"),
        (f"{base}/pck/moon_pa_de440_200625.bpc", "moon_pa_de440_200625.bpc"),
        (f"{base}/fk/satellites/moon_de440_250416.tf", "moon_de440_250416.tf"),
        (f"{base}/fk/satellites/moon_assoc_me.tf", "moon_assoc_me.tf"),
        (f"{base}/spk/planets/de440s.bsp", "de440s.bsp"),
    ]
    print("Ensuring SPICE kernels ...")
    ok = True
    for url, name in kernels:
        ok &= _download(url, spice_dir / name)
    return ok


def _list_pds_tab_files(listing_url: str) -> list[str]:
    """Return the list of .tab hrefs from a PDS HTML directory listing.

    PDS servers return an HTML page with ``href="something.tab"`` links.
    We scrape those and return the full URLs, mirroring what the working
    curl + grep pipeline did during initial data setup.
    """
    import re

    req = urllib.request.Request(
        listing_url, headers={"User-Agent": _USER_AGENT}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        # If urllib is blocked, try curl -s
        if shutil.which("curl"):
            try:
                result = subprocess.run(
                    ["curl", "-fsS", "--retry", "2", listing_url],
                    capture_output=True, text=True, timeout=30,
                )
                html = result.stdout
            except Exception:
                return []
        else:
            return []

    # Extract hrefs that end in .tab
    hrefs = re.findall(r'href="([^"]*\.tab)"', html, re.IGNORECASE)
    root = listing_url.split("/lunar/")[0]  # e.g. https://pds-geosciences.wustl.edu

    urls = []
    for h in hrefs:
        if h.startswith("http"):
            urls.append(h)
        elif h.startswith("/"):
            urls.append(root + h)
        else:
            urls.append(listing_url.rstrip("/") + "/" + h)
    return urls


def ensure_apollo_hfe(
    repo_root: pathlib.Path | None = None,
    probes: Iterable[str] = ("p1f1", "p1f2", "p1f3", "p1f4"),
    mission: str = "a15",
) -> bool:
    """Download a minimal Apollo HFE file set (default: Apollo 15 Probe 1).

    Scrapes the PDS directory listing to get the exact filenames (avoids
    hard-coding paths that may shift between PDS bundle versions).
    Falls back to known-good hardcoded URLs if the listing scrape fails.

    Only the sensor timeseries + depth tables for the requested mission /
    probes are fetched. Total size < 10 MB for the default set.
    """
    repo = repo_root or find_repo_root()
    pds_root = "https://pds-geosciences.wustl.edu"
    base = (
        f"{pds_root}/lunar/"
        "urn-nasa-pds-a15_17_hfe_concatenated/data"
    )
    data_dir = repo / "data" / "apollo" / mission
    depth_dir = repo / "data" / "apollo" / "depth"
    print(f"Ensuring Apollo HFE ({mission}) ...")

    # --- Probe timeseries ---
    listing_url = f"{base}/clean/{mission}/"
    tab_urls = _list_pds_tab_files(listing_url)

    # Build a name→url map from the scraped listing.
    scraped: dict[str, str] = {u.rsplit("/", 1)[-1]: u for u in tab_urls}

    ok = True
    probes_list = list(probes)
    for probe in probes_list:
        fname = f"{mission}{probe}.tab"
        url = scraped.get(fname) or f"{base}/clean/{mission}/{fname}"
        ok &= _download(url, data_dir / fname)

    # --- Depth tables ---
    depth_listing = f"{base}/depth/"
    depth_urls = _list_pds_tab_files(depth_listing)
    scraped_depth: dict[str, str] = {u.rsplit("/", 1)[-1]: u for u in depth_urls}

    for depth_name in ("p1", "p2"):
        fname = f"{mission}{depth_name}_depth.tab"
        url = scraped_depth.get(fname) or f"{base}/depth/{fname}"
        ok &= _download(url, depth_dir / fname)

    if not ok:
        print()
        print("  NOTE: Some Apollo HFE files could not be downloaded automatically.")
        print("  Download them manually from:")
        print(f"    {listing_url}")
        print(f"  and place them in:  {data_dir}/")
        print(f"  Depth tables from:  {depth_listing}")
        print(f"  and place in:       {depth_dir}/")
    return ok


def ensure_change4(repo_root: pathlib.Path | None = None) -> bool:
    """Ensure Chang'E-4 in-situ thermal reference values are available.

    Chang'E-4 temperature-probe time-series lives on China's Lunar and
    Planetary Data Release System (http://moon.bao.ac.cn) which requires
    free user registration. There is no unauthenticated direct-download
    URL, so this function does three things in order:

    1. Verify the bundled reference table ``data/reference/change4_huang2022.csv``
       exists (ships with the repo). This holds the derived scalar
       quantities reported in Huang et al. 2022 (NSR 9, nwac175): probe
       peak temperatures, inferred K_c(z), bulk density, landing
       coordinates.
    2. Try a small set of optional public mirrors that may host the
       supplementary data. Currently empty — update with any Zenodo/
       figshare DOI if Huang et al. deposit a public mirror.
    3. If the reference table is present, return True and print a one-
       line note telling the user where to obtain the full time-series.

    Returns True iff the reference table is usable.
    """
    repo = repo_root or find_repo_root()
    ref_dir = repo / "data" / "reference"
    ref_file = ref_dir / "change4_huang2022.csv"
    ts_dir = repo / "data" / "change4"
    ts_dir.mkdir(parents=True, exist_ok=True)

    print("Ensuring Chang'E-4 reference table ...")

    # Any public mirror URLs go here. None known at time of writing — the
    # authoritative archive is login-gated. Entries should point to
    # unauthenticated direct-download .csv / .tab files only.
    mirror_urls: list[tuple[str, str]] = []
    for url, fname in mirror_urls:
        _download(url, ts_dir / fname)

    if not ref_file.is_file():
        print(f"  ERROR: bundled reference table missing: {ref_file}")
        print("  This file ships with the Lunar-V2 repo — re-clone or")
        print("  restore data/reference/change4_huang2022.csv from git.")
        return False

    print(f"  ok     : {ref_file.name}")
    print("  NOTE   : Full Chang'E-4 T(t) time-series lives on CLPDS")
    print("           (http://moon.bao.ac.cn) — free registration required.")
    print("           The bundled CSV has all scalar quantities needed")
    print("           for Lunar-V2 model cross-checks (Huang et al. 2022).")
    return True


def ensure_chaste(repo_root: pathlib.Path | None = None) -> bool:
    """Ensure Chandrayaan-3 ChaSTE in-situ thermal reference values are available.

    The ChaSTE time-series lives on ISRO PRADAN
    (https://pradan.issdc.gov.in/ch3/) which is login-gated. There is no
    unauthenticated direct-download URL, so this function:

    1. Verifies the bundled reference table
       ``data/reference/chaste_murty2025.csv`` (Murty et al. 2025,
       Sci Rep 15 91866-4; Seth et al. 2025, MNRAS 538 2330; Das et al.
       2025, Commun Earth Environ 6 02114-6).
    2. Attempts an optional public mirror list (currently empty).
    3. Prints manual-download instructions for the full time-series.

    Returns True iff the reference table is usable.
    """
    repo = repo_root or find_repo_root()
    ref_dir = repo / "data" / "reference"
    ref_file = ref_dir / "chaste_murty2025.csv"
    ts_dir = repo / "data" / "chaste"
    ts_dir.mkdir(parents=True, exist_ok=True)

    print("Ensuring ChaSTE reference table ...")

    mirror_urls: list[tuple[str, str]] = []
    for url, fname in mirror_urls:
        _download(url, ts_dir / fname)

    if not ref_file.is_file():
        print(f"  ERROR: bundled reference table missing: {ref_file}")
        print("  This file ships with the Lunar-V2 repo — re-clone or")
        print("  restore data/reference/chaste_murty2025.csv from git.")
        return False

    print(f"  ok     : {ref_file.name}")
    print("  NOTE   : Full ChaSTE T(t,z) time-series lives on ISRO PRADAN")
    print("           (https://pradan.issdc.gov.in/ch3/) — login required.")
    print("           Place downloaded file at data/chaste/chaste_profile.csv")
    print("           for automatic use once available.")
    return True


def ensure_lola_dem_80mpp(repo_root: pathlib.Path | None = None) -> bool:
    """Download the 80 m/pixel south polar LOLA DEM (~180 MB).

    This is the smallest of the three PGDA polar DEMs and is enough for
    the illumination notebook quicklooks.
    """
    repo = repo_root or find_repo_root()
    url = (
        "https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/"
        "LDEM_80S_80MPP_ADJ.TIF"
    )
    dest = repo / "data" / "dem" / "LDEM_80S_80MPP_ADJ.TIF"
    print("Ensuring LOLA 80 MPP DEM ...")
    return _download(url, dest, min_bytes=10_000_000)
