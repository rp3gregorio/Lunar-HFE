"""Apollo HFE per-site deep-conductivity retrieval package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("apollo-hfe-kd-retrieval")
except PackageNotFoundError:  # pragma: no cover - during editable install
    __version__ = "0.0.0+dev"

__all__ = ["__version__"]
