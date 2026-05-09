"""
Canonical reader for ROTSE match structures.

ROTSE-1 stores match data in IDL ``.dat`` save files (read with
``scipy.io.readsav``); ROTSE-3 stores them in FITS files (read with
``astropy.io.fits``). This module dispatches based on the file extension
and exposes a single uniform tuple ``(ra, dec, mag, flags)``.

Replaces four duplicate copies that previously lived in
``autopsfinder/``, ``matchedmanip/``, ``updatedpanapi/``, ``pyfiles/``.
"""
from __future__ import annotations

import logging
import os
from typing import Tuple

import numpy as np
from astropy.io import fits
from scipy.io import readsav

logger = logging.getLogger(__name__)

# Telescope tags returned alongside the match record.
ROTSE3 = "ROTSE3"
ROTSE1 = "ROTSE1"


def read_fits_file(file: str | os.PathLike, fits_index: int = 1):
    """Read the data table from a ROTSE-3 ``*_match.fit`` file.

    Parameters
    ----------
    file
        Path to the FITS file.
    fits_index
        HDU index containing the match table (default ``1``).

    Returns
    -------
    (record, telescope) : tuple
        ``record`` is the ``hdu.data`` table; ``telescope`` is ``"ROTSE3"``.
    """
    try:
        hdus = fits.open(str(file), memmap=True)
        match = hdus[fits_index].data
    except Exception as exc:  # pragma: no cover - re-raised with context
        raise IOError(f"cannot read fits data from file: {file}") from exc
    return match, ROTSE3


def read_match_file(file: str | os.PathLike, *_, **__):
    """Read a ROTSE-1 IDL ``.dat`` match save file."""
    try:
        match = readsav(str(file))["match"]
    except Exception as exc:  # pragma: no cover
        raise IOError(f"cannot read match data from file: {file}") from exc
    return match, ROTSE1


def get_data_file_rotse(file: str | os.PathLike) -> int:
    """Return the canonical FITS HDU index based on the file extension."""
    if not os.path.isfile(file):
        raise FileNotFoundError(f"file not found: {file}")
    ext = str(file).rpartition(".")[2].lower()
    return 3 if ext == "fit" else 1


def read_data_file(file: str | os.PathLike, fits_index: int = 1, tmpdir: str = "/tmp"):
    """Dispatch to FITS or IDL-save reader based on the file extension."""
    if not os.path.isfile(file):
        raise FileNotFoundError(f"file not found: {file}")
    ext = str(file).rpartition(".")[2].lower()
    if ext == "fit":
        return read_fits_file(file, fits_index)
    return read_match_file(file)


def get_data(refra: float, refdec: float, match) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Pull RA/Dec/Mag/Flags arrays from a match record (or a path)."""
    if isinstance(match, str):
        match, _ = read_data_file(match)
    match_ra = match.field("RA")[0]
    match_dec = match.field("DEC")[0]
    match_mag = match.field("M")[0]
    match_flags = match.field("FLAGS")[0]
    return match_ra, match_dec, match_mag, match_flags


def FitReader(file: str | os.PathLike) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Convenience wrapper - return ``(ra, dec, mag, flags)`` from a FITS match file.

    This is the entry point most callers want; it preserves the public
    signature of the original ``FitReader.py`` modules so existing scripts
    can be migrated by replacing the import line.
    """
    match, _ = read_fits_file(file)
    # Original FitReader passed dummy 0,0 reference coords - get_data ignores them.
    return get_data(0.0, 0.0, match)
