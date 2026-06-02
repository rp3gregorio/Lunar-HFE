"""GIF animation utilities for Lunar-Clean thermal model outputs.

Produces animations that display inline in Jupyter notebooks via
``IPython.display.Image(filename=...)`` and are saved to the
``output/gifs/`` directory.

Usage
-----
::

    from lunar.plotting.animations import (
        animate_diurnal_cycle,
        animate_thermal_wave,
        animate_model_comparison,
    )
    gif_path = animate_diurnal_cycle(out, grid, t_s, ...)
    # In notebook: from IPython.display import Image; Image(filename=gif_path)
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

from .style_guide import apply_style, COLORS, panel_label

# Default output directory (relative to repo root, resolved at call time).
_DEFAULT_GIF_DIR = "output/gifs"


def _ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def animate_diurnal_cycle(
    T: np.ndarray,
    z: np.ndarray,
    t_s: np.ndarray,
    insolation: np.ndarray,
    label: str = "This work",
    color: str = COLORS["martinez"],
    output_dir: str = _DEFAULT_GIF_DIR,
    filename: str = "diurnal_cycle.gif",
    fps: int = 15,
    n_frames: int = 120,
    T_surface_ref: dict | None = None,
) -> str:
    """Animate the diurnal surface T + subsurface profile evolution.

    Parameters
    ----------
    T : (N_z, N_t) array — temperature field [K]
    z : (N_z,) array — depth nodes [m]
    t_s : (N_t,) array — time [s]
    insolation : (N_t,) array — surface insolation [W m^-2]
    label : str — legend label for this run
    color : str — line color
    output_dir : str — directory for output GIF
    filename : str — output filename
    fps : int — frames per second
    n_frames : int — total frames (sub-sampled from N_t)
    T_surface_ref : dict, optional — {label: (t_array, T_array)} reference curves

    Returns
    -------
    str — absolute path to the saved GIF
    """
    apply_style()

    out_path = _ensure_dir(output_dir) / filename

    # Sub-sample time steps for animation frames
    frame_idx = np.linspace(0, T.shape[1] - 1, n_frames, dtype=int)
    t_days = t_s / 86400.0
    z_cm = z * 100.0
    z_plot_max = min(200.0, z_cm[-1])

    fig, axes = plt.subplots(1, 3, figsize=(14, 5), constrained_layout=True)

    # Axis 0: insolation + marker
    ax0 = axes[0]
    ax0.plot(t_days, insolation, color="orange", lw=1.2)
    ax0.set_xlabel("Days into lunation")
    ax0.set_ylabel("Insolation [W m$^{-2}$]")
    ax0.set_title("Solar forcing")
    marker0, = ax0.plot([], [], "o", color="red", ms=8, zorder=5)

    # Axis 1: surface T time series + marker
    ax1 = axes[1]
    ax1.plot(t_days, T[0, :], color=color, lw=1.2, label=label)
    if T_surface_ref:
        for ref_label, (ref_t, ref_T) in T_surface_ref.items():
            ax1.plot(ref_t / 86400.0, ref_T, "--", lw=1, alpha=0.7,
                     label=ref_label)
    ax1.set_xlabel("Days into lunation")
    ax1.set_ylabel("Surface temperature [K]")
    ax1.set_title("Surface T(t)")
    ax1.legend(fontsize=8, loc="upper right")
    marker1, = ax1.plot([], [], "o", color="red", ms=8, zorder=5)

    # Axis 2: subsurface profile (animated)
    ax2 = axes[2]
    ax2.set_xlabel("Temperature [K]")
    ax2.set_ylabel("Depth [cm]")
    ax2.set_title("Subsurface T(z)")
    ax2.set_ylim(z_plot_max, 0)
    T_min_all = float(T[:, :].min()) - 10
    T_max_all = float(T[:, :].max()) + 10
    ax2.set_xlim(T_min_all, T_max_all)
    ax2.invert_yaxis()
    profile_line, = ax2.plot([], [], color=color, lw=2)
    time_text = ax2.text(0.02, 0.02, "", transform=ax2.transAxes,
                         fontsize=9, va="bottom",
                         bbox=dict(facecolor="white", alpha=0.8,
                                   edgecolor="0.8", pad=2))

    panel_label(ax0, "(a)")
    panel_label(ax1, "(b)")
    panel_label(ax2, "(c)")

    def _update(frame):
        i = frame_idx[frame]
        # Update markers
        marker0.set_data([t_days[i]], [insolation[i]])
        marker1.set_data([t_days[i]], [T[0, i]])
        # Update profile
        mask = z_cm <= z_plot_max
        profile_line.set_data(T[mask, i], z_cm[mask])
        time_text.set_text(f"t = {t_days[i]:.1f} d")
        return marker0, marker1, profile_line, time_text

    anim = FuncAnimation(fig, _update, frames=n_frames,
                         blit=True, interval=1000 // fps)
    anim.save(str(out_path), writer=PillowWriter(fps=fps), dpi=120)
    plt.close(fig)
    return str(out_path)


def animate_thermal_wave(
    T: np.ndarray,
    z: np.ndarray,
    t_s: np.ndarray,
    T_analytical: np.ndarray | None = None,
    output_dir: str = _DEFAULT_GIF_DIR,
    filename: str = "thermal_wave.gif",
    fps: int = 15,
    n_frames: int = 90,
) -> str:
    """Animate thermal wave propagation into the subsurface.

    Parameters
    ----------
    T : (N_z, N_t) — numerical solution
    z : (N_z,) — depth [m]
    t_s : (N_t,) — time [s]
    T_analytical : (N_z, N_t), optional — analytical reference

    Returns
    -------
    str — path to saved GIF
    """
    apply_style()
    out_path = _ensure_dir(output_dir) / filename
    frame_idx = np.linspace(0, T.shape[1] - 1, n_frames, dtype=int)

    z_cm = z * 100.0
    z_max = min(100.0, z_cm[-1])

    fig, ax = plt.subplots(figsize=(6, 7), constrained_layout=True)
    ax.set_xlabel("Temperature [K]")
    ax.set_ylabel("Depth [cm]")
    ax.set_title("Thermal wave propagation")
    ax.set_ylim(z_max, 0)
    ax.invert_yaxis()

    T_lo = float(T.min()) - 5
    T_hi = float(T.max()) + 5
    ax.set_xlim(T_lo, T_hi)

    line_num, = ax.plot([], [], color=COLORS["martinez"], lw=2,
                        label="Numerical (CN)")
    if T_analytical is not None:
        line_ana, = ax.plot([], [], "--", color=COLORS["hayne"], lw=1.5,
                            label="Analytical")
    ax.legend(loc="lower right")

    time_text = ax.text(0.02, 0.02, "", transform=ax.transAxes,
                        fontsize=10, va="bottom",
                        bbox=dict(facecolor="white", alpha=0.8,
                                  edgecolor="0.8", pad=2))

    mask = z_cm <= z_max

    def _update(frame):
        i = frame_idx[frame]
        line_num.set_data(T[mask, i], z_cm[mask])
        artists = [line_num, time_text]
        if T_analytical is not None:
            line_ana.set_data(T_analytical[mask, i], z_cm[mask])
            artists.append(line_ana)
        time_text.set_text(f"t = {t_s[i] / 86400:.1f} d")
        return artists

    anim = FuncAnimation(fig, _update, frames=n_frames,
                         blit=True, interval=1000 // fps)
    anim.save(str(out_path), writer=PillowWriter(fps=fps), dpi=120)
    plt.close(fig)
    return str(out_path)


def animate_model_comparison(
    results: dict[str, tuple[np.ndarray, np.ndarray]],
    z: np.ndarray,
    t_s: np.ndarray,
    insolation: np.ndarray,
    output_dir: str = _DEFAULT_GIF_DIR,
    filename: str = "model_comparison.gif",
    fps: int = 15,
    n_frames: int = 120,
) -> str:
    """Animate multiple thermal models side-by-side.

    Parameters
    ----------
    results : dict mapping model_name -> (T_field, color_str)
        T_field shape: (N_z, N_t)
    z : (N_z,) depth [m]
    t_s : (N_t,) time [s]
    insolation : (N_t,) insolation [W m^-2]

    Returns
    -------
    str — path to saved GIF
    """
    apply_style()
    out_path = _ensure_dir(output_dir) / filename
    frame_idx = np.linspace(0, list(results.values())[0][0].shape[1] - 1,
                            n_frames, dtype=int)

    t_days = t_s / 86400.0
    z_cm = z * 100.0
    z_max = min(200.0, z_cm[-1])
    mask = z_cm <= z_max

    fig, (ax_surf, ax_prof) = plt.subplots(1, 2, figsize=(12, 5),
                                           constrained_layout=True)

    # Left: surface T(t) for all models
    lines_surf = {}
    for name, (T_field, color) in results.items():
        ax_surf.plot(t_days, T_field[0, :], color=color, lw=1.2,
                     label=name, alpha=0.7)
        dot, = ax_surf.plot([], [], "o", color=color, ms=8, zorder=5)
        lines_surf[name] = dot
    ax_surf.set_xlabel("Days into lunation")
    ax_surf.set_ylabel("Surface temperature [K]")
    ax_surf.set_title("Surface T comparison")
    ax_surf.legend(fontsize=8, loc="upper right")
    panel_label(ax_surf, "(a)")

    # Right: subsurface profiles (animated)
    T_all = np.concatenate([T[mask, :] for T, _ in results.values()])
    ax_prof.set_xlim(float(T_all.min()) - 10, float(T_all.max()) + 10)
    ax_prof.set_ylim(z_max, 0)
    ax_prof.invert_yaxis()
    ax_prof.set_xlabel("Temperature [K]")
    ax_prof.set_ylabel("Depth [cm]")
    ax_prof.set_title("Subsurface T(z)")
    panel_label(ax_prof, "(b)")

    lines_prof = {}
    for name, (T_field, color) in results.items():
        line, = ax_prof.plot([], [], color=color, lw=2, label=name)
        lines_prof[name] = line
    ax_prof.legend(fontsize=8, loc="lower right")

    time_text = ax_prof.text(0.02, 0.02, "", transform=ax_prof.transAxes,
                             fontsize=10, va="bottom",
                             bbox=dict(facecolor="white", alpha=0.8,
                                       edgecolor="0.8", pad=2))

    def _update(frame):
        i = frame_idx[frame]
        artists = [time_text]
        for name, (T_field, color) in results.items():
            lines_surf[name].set_data([t_days[i]], [T_field[0, i]])
            lines_prof[name].set_data(T_field[mask, i], z_cm[mask])
            artists.extend([lines_surf[name], lines_prof[name]])
        time_text.set_text(f"t = {t_days[i]:.1f} d")
        return artists

    anim = FuncAnimation(fig, _update, frames=n_frames,
                         blit=True, interval=1000 // fps)
    anim.save(str(out_path), writer=PillowWriter(fps=fps), dpi=120)
    plt.close(fig)
    return str(out_path)
