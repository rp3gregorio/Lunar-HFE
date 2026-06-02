"""
Lunar-Clean Publication Figure Style & Templates
=================================================

Import this module to apply consistent, publication-quality styling
to all figures in the Lunar-Clean project.

Usage:
    from plotting.style_guide import apply_style, COLORS, CMAPS
    apply_style()
    fig, ax = plt.subplots(figsize=FIG_SINGLE)
    ...

Compatible with: JGR: Planets, PSJ, Icarus, Nature Astronomy, MNRAS
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

# ═══════════════════════════════════════════════════
# FIGURE DIMENSIONS (inches)
# ═══════════════════════════════════════════════════
FIG_SINGLE = (3.35, 3.0)      # Single-column
FIG_SINGLE_TALL = (3.35, 4.5)  # Single-column, portrait
FIG_DOUBLE = (7.0, 4.0)        # Double-column
FIG_DOUBLE_TALL = (7.0, 6.0)   # Double-column, tall
FIG_FULL_PAGE = (7.0, 9.0)     # Full page

# ═══════════════════════════════════════════════════
# MODEL COLORS (categorical, color-blind safe)
# ═══════════════════════════════════════════════════
COLORS = {
    # Thermal models
    'hayne':        '#2166ac',  # Blue
    'martinez':     '#d6604d',  # Red-brown
    'burger':       '#4dac26',  # Green
    'ice_coupled':  '#7b3294',  # Purple (novel)
    'discrete':     '#969696',  # Gray (retired)

    # Observations
    'diviner':      '#1b7837',  # Dark green
    'apollo':       '#e7298a',  # Pink
    'change4':      '#e6ab02',  # Gold
    'chaste':       '#66a61e',  # Lime
    'lister':       '#e78ac3',  # Light pink

    # General
    'primary':      '#2166ac',
    'secondary':    '#d6604d',
    'tertiary':     '#4dac26',
    'quaternary':   '#7b3294',
    'highlight':    '#e7298a',
    'neutral':      '#636363',
    'light':        '#bdbdbd',
}

# ═══════════════════════════════════════════════════
# COLORMAPS
# ═══════════════════════════════════════════════════

# Thermal: dark → cold → warm → hot
_thermal_nodes = [
    '#0d0221', '#1a0533', '#2d1b69', '#3d5a9e',
    '#4da6c9', '#7ec8a0', '#c8e550', '#f5d03b',
    '#f28c28', '#d94f30', '#a11a2d'
]
cmap_thermal = LinearSegmentedColormap.from_list(
    'lunar_thermal', _thermal_nodes, N=256)

# Ice stability: white (unstable) → blue (surface-stable)
_ice_nodes = ['#ffffff', '#d0e8ff', '#6baed6', '#2171b5', '#08306b']
cmap_ice = LinearSegmentedColormap.from_list(
    'ice_stability', _ice_nodes, N=256)

# Illumination fraction: black (PSR) → white (full sun)
_illum_nodes = ['#000000', '#1a1a2e', '#3d5a80', '#98c1d9', '#e0fbfc', '#ffffff']
cmap_illumination = LinearSegmentedColormap.from_list(
    'illumination', _illum_nodes, N=256)

# Diverging: for ΔT difference maps
# Blue (negative) → white (zero) → red (positive)
cmap_delta = 'RdBu_r'  # Built-in, excellent for ΔT

# Register custom colormaps
for name, cm in [('lunar_thermal', cmap_thermal),
                 ('ice_stability', cmap_ice),
                 ('illumination', cmap_illumination)]:
    try:
        mpl.colormaps.register(cm, name=name)
    except ValueError:
        pass  # Already registered

# Convenience dict
CMAPS = {
    'thermal': 'lunar_thermal',
    'ice': 'ice_stability',
    'illumination': 'illumination',
    'delta': 'RdBu_r',
    'magma': 'magma',         # Perceptually uniform, good default for T
    'viridis': 'viridis',     # Perceptually uniform, good for depth
}


# ═══════════════════════════════════════════════════
# STYLE APPLICATION
# ═══════════════════════════════════════════════════

def apply_style():
    """Apply Lunar-Clean publication style to all subsequent figures.

    Call once at the top of every notebook or script.
    Produces figures matching JGR/PSJ/Icarus standards.
    """
    style = {
        # Font
        'font.family': 'sans-serif',
        'font.sans-serif': ['Helvetica', 'Arial', 'DejaVu Sans'],
        'font.size': 10,
        'axes.titlesize': 11,
        'axes.labelsize': 10,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 9,

        # Lines
        'lines.linewidth': 1.5,
        'lines.markersize': 5,
        'axes.linewidth': 0.8,

        # Ticks
        'xtick.major.width': 0.8,
        'ytick.major.width': 0.8,
        'xtick.minor.width': 0.5,
        'ytick.minor.width': 0.5,
        'xtick.major.size': 4,
        'ytick.major.size': 4,
        'xtick.minor.size': 2.5,
        'ytick.minor.size': 2.5,
        'xtick.direction': 'in',
        'ytick.direction': 'in',
        'xtick.top': True,
        'ytick.right': True,
        'xtick.minor.visible': True,
        'ytick.minor.visible': True,

        # Grid (off by default)
        'axes.grid': False,
        'grid.alpha': 0.3,
        'grid.linewidth': 0.5,

        # Figure
        'figure.dpi': 150,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.05,
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',

        # Legend
        'legend.frameon': True,
        'legend.framealpha': 0.9,
        'legend.edgecolor': '0.8',
        'legend.fancybox': False,

        # Math
        'mathtext.default': 'regular',

        # Images
        'image.cmap': 'magma',
    }
    plt.rcParams.update(style)


def panel_label(ax, label, x=0.02, y=0.97, **kwargs):
    """Add (a), (b), (c) panel label to axes.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    label : str, e.g. '(a)', '(b)'
    """
    defaults = dict(transform=ax.transAxes, fontweight='bold',
                    fontsize=11, va='top', ha='left',
                    bbox=dict(facecolor='white', alpha=0.7,
                              edgecolor='none', pad=1.5))
    defaults.update(kwargs)
    ax.text(x, y, label, **defaults)


def save_figure(fig, name, formats=('pdf', 'png'), output_dir='figures'):
    """Save figure in multiple formats.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
    name : str — filename without extension
    formats : tuple of str — file formats to save
    output_dir : str — output directory
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    for fmt in formats:
        path = os.path.join(output_dir, f'{name}.{fmt}')
        fig.savefig(path, dpi=300, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        print(f'  Saved: {path}')


def add_colorbar(fig, im, ax, label, **kwargs):
    """Add a well-formatted colorbar.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
    im : mappable (output of pcolormesh, imshow, etc.)
    ax : matplotlib.axes.Axes
    label : str — colorbar label with units
    """
    defaults = dict(shrink=0.85, pad=0.02, aspect=25)
    defaults.update(kwargs)
    cbar = fig.colorbar(im, ax=ax, **defaults)
    cbar.set_label(label, fontsize=9)
    cbar.ax.tick_params(labelsize=8)
    return cbar


def legend_outside(ax=None, fig=None, handles=None, labels=None,
                   where='right', ncol=1, **kwargs):
    """Place legends outside plotting axes by default.

    Parameters
    ----------
    ax : matplotlib.axes.Axes, optional
        Used for outside-right legends.
    fig : matplotlib.figure.Figure, optional
        Used for figure-level legends.
    handles, labels : optional
        Explicit legend entries.
    where : {'right', 'top', 'bottom'}
        Preferred outside placement.
    ncol : int
        Number of legend columns for figure-level legends.
    """
    if where == 'right':
        if ax is None:
            raise ValueError("legend_outside(where='right') requires ax")
        defaults = dict(
            loc='upper left', bbox_to_anchor=(1.02, 1.0),
            borderaxespad=0.0, frameon=True,
        )
        defaults.update(kwargs)
        return ax.legend(handles=handles, labels=labels, **defaults)

    if fig is None:
        raise ValueError("legend_outside(where='top'/'bottom') requires fig")

    if where == 'top':
        defaults = dict(loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=ncol, frameon=True)
    elif where == 'bottom':
        defaults = dict(loc='upper center', bbox_to_anchor=(0.5, -0.04), ncol=ncol, frameon=True)
    else:
        raise ValueError("where must be 'right', 'top', or 'bottom'")

    defaults.update(kwargs)
    return fig.legend(handles=handles, labels=labels, **defaults)

# ═══════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════

def make_figure(ncols=1, nrows=1, width='single', height_per_row=3.0,
                **kwargs):
    """Create a figure with appropriate dimensions.

    Parameters
    ----------
    ncols, nrows : int
    width : 'single' (3.35 in) or 'double' (7.0 in)
    height_per_row : float — inches per row
    """
    apply_style()
    w = 3.35 if width == 'single' else 7.0
    h = height_per_row * nrows
    fig, axes = plt.subplots(nrows, ncols, figsize=(w, h), **kwargs)
    return fig, axes
