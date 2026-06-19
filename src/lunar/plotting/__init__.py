"""Shared publication figure style for the project.

Importing :mod:`lunar.plotting.style` applies the JGR:Planets-compliant
matplotlib rcParams and exposes the palette and layout helpers. Both the
analysis pipeline and the figure scripts import style from here, so the
pipeline no longer has to import a figure script just to borrow colours.
"""
from . import style  # noqa: F401
