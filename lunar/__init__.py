"""Lunar-Clean v2: planetary subsurface thermal modeling pipeline.

A 1D thermal solver with topographic illumination, ice-coupled properties,
and TSUKIMI terahertz RTM coupling. See ``.claude/skills/SKILL.md`` and the
project ``README.md`` for scientific scope and citation conventions.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("lunar-clean")
except PackageNotFoundError:  # pragma: no cover - during editable install
    __version__ = "0.0.0+dev"

__all__ = ["__version__"]
