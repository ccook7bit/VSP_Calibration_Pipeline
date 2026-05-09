"""
Reusable photometric quality cuts.

These were duplicated across ``slopifier/Slopifier.py`` and four notebooks
(``BigSlopifier``, ``Big2Slopifer``, ``SlopifierNotebook``,
``Slopifier2Notebook``). Centralizing them here means a single source of
truth for the band/PSF/Kron/color logic.
"""
from __future__ import annotations

from typing import Tuple

import pandas as pd

# Band -> (PSF column, Kron column, label) mapping for PanSTARRS columns.
BAND_COLUMNS = {
    "g": ("gMeanPSFMag", "gMeanKronMag", "gKron"),
    "r": ("rMeanPSFMag", "rMeanKronMag", "rKron"),
    "i": ("iMeanPSFMag", "iMeanKronMag", "iKron"),
    "z": ("zMeanPSFMag", "zMeanKronMag", "zKron"),
    "y": ("yMeanPSFMag", "yMeanKronMag", "yKron"),
}

# Color label -> (band_a PSF column, band_b PSF column, human label).
COLOR_PAIRS = {
    "gr": ("gMeanPSFMag", "rMeanPSFMag", "g-r"),
    "gi": ("gMeanPSFMag", "iMeanPSFMag", "g-i"),
    "ri": ("rMeanPSFMag", "iMeanPSFMag", "r-i"),
}


def kron_cut(df: pd.DataFrame, band: str = "g", max_dist: float = 0.5):
    """Drop rows where ``|PSF_mag - Kron_mag|`` exceeds ``max_dist`` for a given band.

    Returns
    -------
    (filtered_df, kron_col, psf_col, kron_cut_name)
    """
    if band not in BAND_COLUMNS:
        raise ValueError(f"Unknown band {band!r}; choose from {sorted(BAND_COLUMNS)}")
    psf_name, kron_name, kron_cut_name = BAND_COLUMNS[band]
    mask = (df[psf_name] - df[kron_name]).abs() < max_dist
    return df[mask].copy(), kron_name, psf_name, kron_cut_name


def bitflag_cut(df: pd.DataFrame, value, column: str = "Flags") -> pd.DataFrame:
    """Keep only rows whose ``column`` (default ``Flags``) equals ``value``."""
    return df[df[column] == value].copy()


def color_cut(df: pd.DataFrame, pair_1: str = "gr", pair_2: str = "ri"):
    """Insert ``color1``/``color2`` columns from two color pairs.

    Returns
    -------
    (df, band1a, band1b, band2a, band2b, name1, name2)
    """
    if pair_1 not in COLOR_PAIRS or pair_2 not in COLOR_PAIRS:
        raise ValueError(f"Unknown color pair; choose from {sorted(COLOR_PAIRS)}")
    band1a, band1b, name1 = COLOR_PAIRS[pair_1]
    band2a, band2b, name2 = COLOR_PAIRS[pair_2]
    out = df.copy()
    out.insert(0, "color1", out[band1a] - out[band1b])
    out.insert(1, "color2", out[band2a] - out[band2b])
    return out, band1a, band1b, band2a, band2b, name1, name2


def drop_panstarrs_sentinels(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows where any PanSTARRS PSF/Kron magnitude is the ``-999`` sentinel."""
    cols = [c for band in BAND_COLUMNS for c in BAND_COLUMNS[band][:2] if c in df.columns]
    if not cols:
        return df
    mask = pd.Series(True, index=df.index)
    for c in cols:
        mask &= df[c] != -999
    return df[mask].copy()


def magnitude_window(df: pd.DataFrame, mag_col: str = "Mag",
                     mag_min: float = 5.0, mag_max: float = 25.0) -> pd.DataFrame:
    """Keep rows where ``mag_col`` is in the ``[mag_min, mag_max]`` window."""
    return df[(df[mag_col] >= mag_min) & (df[mag_col] <= mag_max)].copy()


def flag_is_true(row, flag) -> bool:
    """Convenience: ``row.get(flag, False)`` for unpacked-bitmask DataFrames."""
    return bool(row.get(flag, False))
