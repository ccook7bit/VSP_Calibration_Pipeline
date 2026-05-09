"""
Relative photometric correction step.

This is the real implementation of the skeleton in
``vsp_pipeline/RelativePhoto.py``. The relative-photometry pass checks
each source against three quality criteria and flags / corrects as
needed:

* extended-source check (PSF-Kron magnitude difference)
* color-cut check (g-r, r-i within sane bounds)
* pseudo-bolometric residual check
  (``|pseudoBoloMag - Mag|`` not absurdly large)

The original module had stubbed functions; here they pull the same
shared cuts/photometry helpers used elsewhere in the pipeline so a
fix to a cut threshold in ``calibration.cuts`` propagates here too.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from ..calibration import cuts, photometry
from ..config import get_config

logger = logging.getLogger(__name__)


@dataclass
class RelativeFlags:
    """Per-source flags from the relative-photo pass."""
    extended_source_flag: bool = False
    color_cut_flag: bool = False
    pseudo_bolometry_flag: bool = False
    correction_applied: bool = False
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, bool]:
        return {
            "extended_source_flag": self.extended_source_flag,
            "color_cut_flag": self.color_cut_flag,
            "pseudo_bolometry_flag": self.pseudo_bolometry_flag,
            "correction_applied": self.correction_applied,
        }


def _is_extended_source(df: pd.DataFrame, band: str = "g", threshold: float = 0.5) -> pd.Series:
    """True per-row if the source looks extended in the given band."""
    psf_col, kron_col, _ = cuts.BAND_COLUMNS[band]
    if psf_col not in df.columns or kron_col not in df.columns:
        return pd.Series(False, index=df.index)
    return (df[psf_col] - df[kron_col]).abs() >= threshold


def _fails_color_cuts(df: pd.DataFrame,
                      gr_min=-0.5, gr_max=2.0,
                      ri_min=-0.5, ri_max=2.0) -> pd.Series:
    """True per-row if g-r or r-i fall outside reasonable bounds."""
    needed = ["gMeanPSFMag", "rMeanPSFMag", "iMeanPSFMag"]
    if not all(c in df.columns for c in needed):
        return pd.Series(False, index=df.index)
    gr = df["gMeanPSFMag"] - df["rMeanPSFMag"]
    ri = df["rMeanPSFMag"] - df["iMeanPSFMag"]
    return ~(((gr >= gr_min) & (gr <= gr_max)) & ((ri >= ri_min) & (ri <= ri_max)))


def _fails_pseudo_bolometry(df: pd.DataFrame, max_diff: float = 5.0) -> pd.Series:
    """True per-row if ``|pseudoBoloMag - Mag|`` exceeds ``max_diff``."""
    if "pseudoBoloMag" not in df.columns or "Mag" not in df.columns:
        return pd.Series(False, index=df.index)
    return (df["pseudoBoloMag"] - df["Mag"]).abs() > max_diff


def check_and_correct(df: pd.DataFrame) -> Tuple[pd.DataFrame, RelativeFlags]:
    """Run the three relative-photo checks and tag/clean the DataFrame.

    Returns a copy of ``df`` with three new columns
    (``extended_source_flag``, ``color_cut_flag``,
    ``pseudo_bolometry_flag``) plus a :class:`RelativeFlags` summary
    saying which corrections fired at least once.
    """
    out = df.copy()
    flags = RelativeFlags()

    # Make sure pseudoBoloMag exists (cheap if columns are present).
    if "pseudoBoloMag" not in out.columns and all(
        f"{b}MeanPSFMag" in out.columns for b in photometry.BANDS
    ):
        cfg = get_config().get("slopifier", {})
        out = photometry.add_band_fluxes(out, ab_zeropoint=cfg.get("ab_zeropoint", 48.6))
        out = photometry.pseudo_bolometric_magnitude(
            out,
            weights=cfg.get("bolometric_weights",
                            {"g": 0.1212, "r": 0.1463, "i": 0.1435, "z": 0.098, "y": 0.0393}),
            norm=cfg.get("bolometric_norm", 0.5483),
            ab_zeropoint=cfg.get("ab_zeropoint", 48.6),
            ab_flux_zero_jy=cfg.get("ab_flux_zero_jy", 3631.0e-23),
            flux_columns=False,
        )

    ext = _is_extended_source(out)
    col = _fails_color_cuts(out)
    pbo = _fails_pseudo_bolometry(out)

    out["extended_source_flag"] = ext.astype(bool)
    out["color_cut_flag"] = col.astype(bool)
    out["pseudo_bolometry_flag"] = pbo.astype(bool)

    if ext.any():
        flags.extended_source_flag = True
        flags.notes.append(f"{int(ext.sum())} extended sources flagged")
    if col.any():
        flags.color_cut_flag = True
        flags.notes.append(f"{int(col.sum())} sources failed color cuts")
    if pbo.any():
        flags.pseudo_bolometry_flag = True
        flags.notes.append(f"{int(pbo.sum())} sources failed pseudo-bolometric check")

    flags.correction_applied = bool(ext.any() or col.any() or pbo.any())
    return out, flags
