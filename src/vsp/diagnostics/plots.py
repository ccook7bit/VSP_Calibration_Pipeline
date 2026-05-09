"""
Per-night diagnostic plot battery.

Produces three multi-panel PNGs for a given field+night:

* ``{field}_{night}_combined_plot.png``
    - Slope vs JD
    - AB-offset vs JD
    - Counts (#matched to PanSTARRS) vs JD
    - Limiting magnitude vs JD
* ``{field}_{night}_diag3plots.png``
    - Slope vs Counts, ABoffset vs Counts, DMoon vs Counts, VPrecip vs Counts
* ``{field}_{night}_diag4plots.png``
    - Elevation vs JD, Counts vs Elevation, M_Lim vs Elevation, Slope vs Elevation

Replaces the hardcoded ``matchedmanip/Reading2.py`` script. Uses the
shared config and `summary_csv` / `match_file` helpers so paths aren't
baked into the plotting code.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from astropy.io import fits
from astropy.table import Table

from ..config import get_config, get_path
from ..io.match_io import match_file, summary_csv

logger = logging.getLogger(__name__)

sns.set_theme(style="darkgrid")


def _load_summary(field: str, night: str) -> pd.DataFrame:
    """Load the per-exposure summary and tag with ``Night``."""
    df = pd.read_csv(summary_csv(field, night))
    df["Night"] = night
    return df


def _load_elevation(field: str, night: str, length: int) -> Optional[pd.Series]:
    """Pull HDU-2 ``ELEV`` from the match FITS, truncated to ``length`` rows."""
    fits_path = match_file(field, night, ext="fit")
    if not fits_path.is_file():
        logger.warning("No FITS for elevation lookup: %s", fits_path)
        return None
    try:
        with fits.open(fits_path) as hdu:
            tbl = Table(hdu[2].data)
        # Coerce big-endian -> native float.
        return pd.Series(tbl["ELEV"]).astype("<f8").iloc[:length].reset_index(drop=True)
    except Exception as exc:
        logger.warning("Could not read ELEV from %s: %s", fits_path, exc)
        return None


def plot_night_diagnostics(field: str, night: str, output_dir: Optional[Path] = None,
                           kron_label: str = "gKron 0.5") -> list[Path]:
    """Render the three diagnostic PNGs for one field+night. Returns paths written."""
    if output_dir is None:
        output_dir = get_path("graphics_dir")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = _load_summary(field, night)
    elev = _load_elevation(field, night, length=len(df))
    if elev is not None:
        df = pd.concat([df, elev.rename("ELEV")], axis=1)

    written: list[Path] = []
    written.append(_plot_against_jd(df, field, night, output_dir, kron_label))
    written.append(_plot_correlations(df, field, night, output_dir))
    if elev is not None:
        written.append(_plot_elevation(df, field, night, output_dir, kron_label))
    return written


def _plot_against_jd(df, field, night, output_dir, kron_label):
    fig = plt.figure(figsize=(18, 10))
    panels = [
        ("Slope", (0.0, 1.0), f"Slope of each exposure -- {field} {night} -- {kron_label}"),
        ("ABoffset", (0.0, 12.0), f"AB Offset of each exposure -- {field} {night} -- {kron_label}"),
        ("Counts", (0, 3000), f"objects matched to PanSTARRS {field} {night} {kron_label}"),
        ("M_Lim", (14.5, 16.5), f"Limiting Magnitude {field} {night} {kron_label}"),
    ]
    for i, (ycol, ylim, title) in enumerate(panels, 1):
        ax = plt.subplot(2, 2, i)
        sns.scatterplot(data=df, x="JulianDate", y=ycol, ax=ax)
        ax.set_xlabel("Julian Date", fontsize=16)
        ax.set_ylabel(ycol, fontsize=16)
        ax.set_ylim(*ylim)
        ax.set_title(title, fontsize=16)
        ax.tick_params(axis="both", which="major", labelsize=13)
    plt.tight_layout()
    out = output_dir / f"{field}_{night}_combined_plot.png"
    fig.savefig(out)
    plt.close(fig)
    logger.info("Wrote %s", out)
    return out


def _plot_correlations(df, field, night, output_dir):
    fig = plt.figure(figsize=(18, 10))
    panels = [
        ("Slope", "Counts", (0.0, 1.0), (0, 3000), "Slope vs Counts"),
        ("ABoffset", "Counts", (0.0, 12.0), (0, 3000), "ABoffset vs Counts"),
        ("Counts", "DMoon", (0, 3000), (70, 150), "DMoon over Counts"),
        ("Counts", "VPrecip", (0, 3000), (2.56, 2.7), "VPrecip over Counts"),
    ]
    for i, (xcol, ycol, xlim, ylim, title) in enumerate(panels, 1):
        if xcol not in df.columns or ycol not in df.columns:
            continue
        ax = plt.subplot(2, 2, i)
        sns.scatterplot(x=xcol, y=ycol, data=df, ax=ax)
        ax.set_title(title, fontsize=16)
        ax.set_xlabel(xcol, fontsize=14)
        ax.set_ylabel(ycol, fontsize=14)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.tick_params(axis="both", which="major", labelsize=13)
    plt.tight_layout()
    out = output_dir / f"{field}_{night}_diag3plots.png"
    fig.savefig(out)
    plt.close(fig)
    logger.info("Wrote %s", out)
    return out


def _plot_elevation(df, field, night, output_dir, kron_label):
    fig = plt.figure(figsize=(18, 10))
    panels = [
        ("JulianDate", "ELEV", None, None, f"Elevation of each exposure -- {field} {night} -- {kron_label}"),
        ("ELEV", "Counts", None, (0, 3000), "Elevation over Counts"),
        ("ELEV", "M_Lim", None, (14.5, 16.5), "Elevation over Limiting Magnitude"),
        ("ELEV", "Slope", None, (0, 1.0), "Elevation over Slope"),
    ]
    for i, (xcol, ycol, xlim, ylim, title) in enumerate(panels, 1):
        if xcol not in df.columns or ycol not in df.columns:
            continue
        ax = plt.subplot(2, 2, i)
        sns.scatterplot(data=df, x=xcol, y=ycol, ax=ax)
        ax.set_title(title, fontsize=16)
        ax.set_xlabel(xcol, fontsize=14)
        ax.set_ylabel(ycol, fontsize=14)
        if xlim:
            ax.set_xlim(*xlim)
        if ylim:
            ax.set_ylim(*ylim)
        ax.tick_params(axis="both", which="major", labelsize=13)
    plt.tight_layout()
    out = output_dir / f"{field}_{night}_diag4plots.png"
    fig.savefig(out)
    plt.close(fig)
    logger.info("Wrote %s", out)
    return out
