"""Publication-figure style and templates.

This package mirrors the canonical skill version at
``.claude/skills/plotting/style_guide.py`` so notebooks can do::

    from lunar.plotting.style_guide import apply_style, COLORS, CMAPS, save_figure

and scripts under ``lunar/`` get the same look-and-feel as the agent-
authored templates. Keep this copy in sync with the skill version.
"""

from .style_guide import (
    COLORS,
    CMAPS,
    FIG_DOUBLE,
    FIG_DOUBLE_TALL,
    FIG_FULL_PAGE,
    FIG_SINGLE,
    FIG_SINGLE_TALL,
    add_colorbar,
    apply_style,
    cmap_ice,
    cmap_illumination,
    cmap_thermal,
    make_figure,
    panel_label,
    save_figure,
)
from .animations import (
    animate_diurnal_cycle,
    animate_thermal_wave,
    animate_model_comparison,
)

__all__ = [
    "COLORS",
    "CMAPS",
    "FIG_SINGLE",
    "FIG_SINGLE_TALL",
    "FIG_DOUBLE",
    "FIG_DOUBLE_TALL",
    "FIG_FULL_PAGE",
    "apply_style",
    "save_figure",
    "panel_label",
    "add_colorbar",
    "make_figure",
    "cmap_thermal",
    "cmap_ice",
    "cmap_illumination",
    "animate_diurnal_cycle",
    "animate_thermal_wave",
    "animate_model_comparison",
]
