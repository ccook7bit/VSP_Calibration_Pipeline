"""
Cross-match ROTSE detections against the PanSTARRS DR2 catalog.

For a given field+night this module:

1. Loads the ROTSE ``*_match.fit`` (RA/Dec/Mag/Flags arrays).
2. Loads the per-field PanSTARRS reference catalog CSV.
3. Pre-filters PanSTARRS rows to those within ``match_radius_arcsec`` of
   any ROTSE detection (and vice-versa) using astropy's catalog matcher.
4. For each exposure in the match structure, builds a merged DataFrame of
   matched (ROTSE, PanSTARRS) rows using a SciPy ``cKDTree`` and writes
   it to ``{field}00{night}_exp{n}.csv``. A small RA/Dec extent summary
   is written alongside as ``coords{field}00{night}_exp{n}.csv``.

Replaces ``AutoPSFinder.py``, ``AutoPSFinderRevamped.py`` (autopsfinder zip),
and ``PSFinderCanon.py`` (updatedpanapi zip). Keeps the RA-wrap fix from
``PSFinderCanon`` and the coords-summary output.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, List

import numpy as np
import pandas as pd
from astropy import units as u
from astropy.coordinates import Angle, SkyCoord
from scipy.spatial import cKDTree

from ..config import get_config
from ..io.fits_reader import FitReader
from ..io.match_io import (
    coords_csv,
    crossmatch_csv,
    match_file,
    panstarrs_csv,
)

logger = logging.getLogger(__name__)


PAN_COLUMNS_DEFAULT: List[str] = [
    "objID", "raMean", "decMean",
    "gMeanPSFMag", "gMeanPSFMagErr", "gMeanKronMag", "gMeanKronMagErr",
    "rMeanPSFMag", "rMeanPSFMagErr", "rMeanKronMag", "rMeanKronMagErr",
    "iMeanPSFMag", "iMeanPSFMagErr", "iMeanKronMag", "iMeanKronMagErr",
    "zMeanPSFMag", "zMeanPSFMagErr", "zMeanKronMag", "zMeanKronMagErr",
    "yMeanPSFMag", "yMeanPSFMagErr", "yMeanKronMag", "yMeanKronMagErr",
]


def _wrap_ra(ra_array):
    """Subtract 360 from any RA values that are > 360 (mod-360 wrap)."""
    return np.array([ra - 360.0 if ra > 360.0 else ra for ra in ra_array])


def _flag_within(angles, max_arcsec: float) -> List[int]:
    """Return indices of ``angles`` that are within ``max_arcsec``."""
    bound = f"{max_arcsec}s"
    return [i for i, n in enumerate(angles) if Angle(n).is_within_bounds(None, bound)]


def crossmatch_night(field: str, night: str) -> List[Path]:
    """Run the per-night cross-match. Returns the list of output CSVs (one per exposure)."""
    cfg = get_config()
    xm_cfg = cfg["crossmatch"]
    radius_arcsec = xm_cfg["match_radius_arcsec"]
    ra_wrap = xm_cfg.get("ra_wrap", True)

    fits_path = match_file(field, night, ext="fit")
    pan_path = panstarrs_csv(field)
    logger.info("Cross-matching %s night=%s -> %s", field, night, fits_path)

    in_ra, in_dec, in_mag, in_flags = FitReader(str(fits_path))
    if ra_wrap:
        in_ra = _wrap_ra(in_ra)

    n_exposures = len(in_mag[0]) - 1
    exposures = list(range(n_exposures))
    logger.debug("%d exposures available", n_exposures)

    pan_df = pd.read_csv(pan_path)
    pan_df["raMean"] = pd.to_numeric(pan_df["raMean"], errors="coerce")
    pan_df["decMean"] = pd.to_numeric(pan_df["decMean"], errors="coerce")
    pan_df.dropna(subset=["raMean", "decMean"], inplace=True)
    if ra_wrap:
        pan_df["raMean"] = pan_df["raMean"].apply(lambda r: r - 360.0 if r > 360.0 else r)

    rotse_skycoord = SkyCoord(in_ra * u.degree, in_dec * u.degree)
    pan_skycoord = SkyCoord(
        pan_df["raMean"].tolist(), pan_df["decMean"].tolist(),
        frame="icrs", unit="deg",
    )

    # PanSTARRS rows close to any ROTSE detection.
    pan_idx, pan_d2d, _ = rotse_skycoord.match_to_catalog_sky(pan_skycoord)
    pan_keep = _flag_within(pan_d2d, radius_arcsec)
    flagged_pan = [pan_idx[i] for i in pan_keep]

    # ROTSE rows close to any PanSTARRS detection.
    rotse_idx, rotse_d2d, _ = pan_skycoord.match_to_catalog_sky(rotse_skycoord)
    rotse_keep = _flag_within(rotse_d2d, radius_arcsec)
    flagged_rotse = [rotse_idx[i] for i in rotse_keep]

    logger.info(
        "Coarse filter: %d ROTSE near PanSTARRS, %d PanSTARRS near ROTSE",
        len(flagged_rotse), len(flagged_pan),
    )

    written: List[Path] = []
    for exposure in exposures:
        out_csv = _process_exposure(
            field=field, night=night, exposure=exposure,
            in_ra=in_ra, in_dec=in_dec, in_mag=in_mag, in_flags=in_flags,
            pan_df=pan_df, flagged_rotse=flagged_rotse, flagged_pan=flagged_pan,
            radius_arcsec=radius_arcsec,
        )
        if out_csv is not None:
            written.append(out_csv)

    logger.info("Wrote %d exposure CSV(s) for %s night=%s", len(written), field, night)
    return written


def _process_exposure(
    *, field, night, exposure,
    in_ra, in_dec, in_mag, in_flags,
    pan_df, flagged_rotse, flagged_pan, radius_arcsec,
) -> Path | None:
    """Inner per-exposure merge -> CSV. Returns the written path, or None on empty match."""
    valid_pan = [i for i in flagged_pan if i in pan_df.index]
    pan_subset = pan_df.loc[valid_pan, [c for c in PAN_COLUMNS_DEFAULT if c in pan_df.columns]]

    rot_df = pd.DataFrame({
        "RA": in_ra,
        "Dec": in_dec,
        "Mag": np.transpose(in_mag)[exposure],
        "Flags": np.transpose(in_flags)[exposure],
    })
    # Astropy/numpy can hand back big-endian columns; pandas merges below
    # blow up unless we coerce to native byte-order.
    rot_df = rot_df.astype(rot_df.dtypes.apply(lambda t: t.newbyteorder("<")))

    rot_subset = rot_df.loc[flagged_rotse, ["RA", "Dec", "Mag", "Flags"]]
    if rot_subset.empty or pan_subset.empty:
        logger.warning("Exposure %d: no surviving matches; skipping", exposure)
        return None

    rot_coords = np.radians(rot_df[["RA", "Dec"]].values)
    pan_coords = np.radians(pan_df[["raMean", "decMean"]].values)
    tree = cKDTree(rot_coords)
    distances, indices = tree.query(pan_coords, distance_upper_bound=np.radians(radius_arcsec / 3600.0))
    mask = ~np.isinf(distances)

    matched_rot = rot_df.iloc[indices[mask]].reset_index(drop=True)
    matched_pan = pan_df[mask].reset_index(drop=True)
    merged = pd.concat([matched_rot, matched_pan], axis=1)

    out_csv = crossmatch_csv(field, night, exposure)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_csv, index=False)

    summary = pd.DataFrame({
        "Min_RA":  [merged["RA"].min()],  "Max_RA":  [merged["RA"].max()],
        "Min_Dec": [merged["Dec"].min()], "Max_Dec": [merged["Dec"].max()],
    })
    summary.to_csv(coords_csv(field, night, exposure), index=False)

    logger.debug("Exposure %d: %d matched rows -> %s", exposure, len(merged), out_csv)
    return out_csv


def crossmatch_field(field: str, nights: Iterable[str]) -> dict:
    """Run :func:`crossmatch_night` over a sequence of nights for one field."""
    out = {}
    for night in nights:
        try:
            out[night] = crossmatch_night(field, night)
        except FileNotFoundError as exc:
            logger.warning("Skipping %s night=%s: %s", field, night, exc)
            out[night] = []
    return out
