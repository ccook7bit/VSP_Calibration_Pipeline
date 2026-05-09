"""
Per-exposure limiting-magnitude estimator.

Implements the helper used inline by ``BigSlopifier.ipynb`` /
``Big2Slopifer.ipynb`` to extract a per-exposure limiting magnitude from
a ROTSE match FITS file's ``M`` and ``JD`` columns.

The "limiting magnitude" here is a coarse heuristic: the brightest
non-99 magnitude in each exposure's column. It is good enough as a
diagnostic input but should not be quoted as the formal photometric
limiting magnitude of the survey.
"""
from __future__ import annotations

import logging
from typing import Tuple

import numpy as np
from astropy.io import fits

logger = logging.getLogger(__name__)


def find_limiting_magnitude(data) -> Tuple[np.ndarray, np.ndarray]:
    """Return ``(julian_dates, limiting_mags)`` from a match-table HDU's data.

    Parameters
    ----------
    data
        ``hdu.data`` from a match-structure FITS HDU. Must expose
        ``M`` (mags array) and ``JD`` (julian-date array).

    Returns
    -------
    julian_dates : np.ndarray, shape (n_exposures,)
    limiting_mags : np.ndarray, shape (n_exposures,)
    """
    if "M" not in data.columns.names or "JD" not in data.columns.names:
        raise ValueError("HDU does not contain both 'M' and 'JD' columns")

    magnitudes = data["M"]
    jd = data["JD"]

    n_exposures = magnitudes.shape[2] if magnitudes.ndim >= 3 else magnitudes.shape[-1]
    julian_dates = []
    limiting_mags = []
    for i in range(n_exposures):
        # `M` is shape (1, n_objects, n_exposures) for per-object per-exposure mags.
        col = magnitudes[0, :, i] if magnitudes.ndim >= 3 else magnitudes[..., i]
        col = np.asarray(col).ravel()
        valid = col[(col > 0) & (col < 99)]
        if len(valid) == 0:
            limiting_mags.append(np.nan)
        else:
            limiting_mags.append(float(np.nanmax(valid)))
        julian_dates.append(float(jd[0, i]) if jd.ndim >= 2 else float(jd[i]))

    return np.asarray(julian_dates), np.asarray(limiting_mags)


def find_limiting_magnitude_for_file(fits_path) -> Tuple[np.ndarray, np.ndarray]:
    """Convenience wrapper that opens a FITS path and reads HDU 1."""
    with fits.open(fits_path) as hdul:
        if len(hdul) < 2:
            raise ValueError(f"Match FITS {fits_path} has no extension HDU")
        return find_limiting_magnitude(hdul[1].data)
