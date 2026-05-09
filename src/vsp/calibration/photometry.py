"""
Photometric helpers: AB flux <-> magnitude, pseudo-bolometric magnitude,
and the simple linear fits used by the slopifier and unconex steps.

Replaces ``pyfiles/VSPFunctions.py`` and the per-script copies of the
flux/pseudo-bolometric block in ``slopifier/Slopifier.py``.

See ``docs/calibration_math.md`` for the derivation of the
pseudo-bolometric magnitude.
"""
from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd

# Standard PanSTARRS bands.
BANDS = ("g", "r", "i", "z", "y")


def mag_to_flux(mag, ab_zeropoint: float = 48.6):
    """Convert AB magnitude to flux (erg/s/cm^2/Hz)."""
    return np.power(10.0, (mag + ab_zeropoint) / -2.5)


def flux_to_mag(flux, ab_zeropoint: float = 48.6):
    """Inverse of :func:`mag_to_flux` (NaN if ``flux <= 0``)."""
    flux = np.asarray(flux, dtype=float)
    out = np.full_like(flux, np.nan)
    pos = flux > 0
    out[pos] = -2.5 * np.log10(flux[pos]) - ab_zeropoint
    return out


def add_band_fluxes(df: pd.DataFrame, ab_zeropoint: float = 48.6) -> pd.DataFrame:
    """Add ``gflux``..``yflux`` columns derived from ``{band}MeanPSFMag``.

    The input ``df`` must already be filtered of ``-999`` sentinels (see
    :func:`vsp.calibration.cuts.drop_panstarrs_sentinels`).
    """
    out = df.copy()
    for band in BANDS:
        out[f"{band}flux"] = mag_to_flux(out[f"{band}MeanPSFMag"], ab_zeropoint)
    return out


def pseudo_bolometric_magnitude(
    df: pd.DataFrame,
    weights: Mapping[str, float],
    norm: float,
    ab_zeropoint: float = 48.6,
    ab_flux_zero_jy: float = 3631.0e-23,
    flux_columns: bool = True,
    drop_intermediate: bool = True,
) -> pd.DataFrame:
    """Add ``totalFlux``, ``logpart``, ``pseudoBoloMag`` columns to ``df``.

    Combines the five PanSTARRS PSF magnitudes into a single
    pseudo-bolometric magnitude using band weights and an overall
    normalization (defaults match the values in the original
    ``slopifier/Slopifier.py``).

    Parameters
    ----------
    df
        DataFrame with ``{band}flux`` columns (set ``flux_columns=False``
        if those don't exist; this function will compute them from
        ``{band}MeanPSFMag``).
    weights
        Per-band weight (``g``, ``r``, ``i``, ``z``, ``y``).
    norm
        Normalization divisor.
    ab_zeropoint
        AB magnitude zero-point used in flux conversion.
    ab_flux_zero_jy
        AB=0 flux in cgs units.
    flux_columns
        If False, compute ``{band}flux`` first.
    drop_intermediate
        Drop ``{band}flux`` and ``logpart`` after computing
        ``pseudoBoloMag``.
    """
    out = df if flux_columns else add_band_fluxes(df, ab_zeropoint)
    if not flux_columns:
        out = out.copy()

    if not all(f"{b}flux" in out.columns for b in BANDS):
        out = add_band_fluxes(out, ab_zeropoint)

    weighted = sum(out[f"{b}flux"] * weights[b] for b in BANDS) / norm
    out["totalFlux"] = weighted
    out["logpart"] = np.log10(out["totalFlux"] / ab_flux_zero_jy)
    out["pseudoBoloMag"] = -2.5 * out["logpart"]

    if drop_intermediate:
        out = out.drop(columns=[f"{b}flux" for b in BANDS] + ["logpart"], errors="ignore")
    return out


def linear_fit(x, y, with_cov: bool = True):
    """Simple ``numpy.polyfit`` wrapper returning ``(slope, intercept[, cov])``."""
    res = np.polyfit(x, y, 1, full=False, cov=with_cov)
    if with_cov:
        coeffs, cov = res
        return float(coeffs[0]), float(coeffs[1]), cov
    return float(res[0]), float(res[1])


def line_at(x, intercept):
    """Constant-line model used as a degenerate fit alternative."""
    return np.full_like(np.asarray(x, dtype=float), intercept)


def one_d_fit(slope, intercept, x):
    """``slope * x + intercept`` (kept for back-compat with VSPFunctions.py)."""
    return slope * np.asarray(x) + intercept
