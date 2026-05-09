"""
Absolute photometric correction step.

The original ``vsp_pipeline/AbsolutePhoto.py`` was an empty file.
This module provides the real implementation of the planned absolute
photometric correction stage: tie the per-exposure raw magnitudes to
the AB system using the ``(slope, ABoffset)`` calibration from
:mod:`vsp.calibration.slopifier`.

Inputs
------
A merged ROTSE x PanSTARRS DataFrame for a single exposure, plus a
:class:`~vsp.calibration.slopifier.ExposureFit` describing the fit for
that exposure.

Outputs
-------
A copy of the DataFrame with an extra ``Mag_AB`` column, plus a flag
dictionary indicating which corrections fired.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import pandas as pd

from ..calibration.slopifier import ExposureFit

logger = logging.getLogger(__name__)


@dataclass
class AbsoluteFlags:
    """Diagnostic flags raised during the absolute-photo correction."""
    correction_applied: bool = False
    slope_outside_expected: bool = False
    ab_offset_outside_expected: bool = False
    low_count_warning: bool = False
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, bool]:
        return {
            "correction_applied": self.correction_applied,
            "slope_outside_expected": self.slope_outside_expected,
            "ab_offset_outside_expected": self.ab_offset_outside_expected,
            "low_count_warning": self.low_count_warning,
        }


# Empirical sanity bounds. These match the ranges the diagnostic plots
# already enforced (Slope in [0, 1], ABoffset in [0, 12], Counts > ~50).
SLOPE_RANGE = (0.0, 1.0)
ABOFFSET_RANGE = (0.0, 12.0)
MIN_COUNTS = 50


def needs_correction(fit: ExposureFit) -> bool:
    """Quick heuristic: return True if the fit's slope/offset/counts look unhealthy."""
    if not (SLOPE_RANGE[0] <= fit.slope <= SLOPE_RANGE[1]):
        return True
    if not (ABOFFSET_RANGE[0] <= fit.ab_offset <= ABOFFSET_RANGE[1]):
        return True
    if fit.counts < MIN_COUNTS:
        return True
    return False


def check_and_correct(
    df: pd.DataFrame,
    fit: Optional[ExposureFit],
    *,
    mag_col: str = "Mag",
    out_col: str = "Mag_AB",
) -> Tuple[pd.DataFrame, AbsoluteFlags]:
    """Apply the (slope, ABoffset) correction to ``df[mag_col]``.

    The corrected magnitude is::

        Mag_AB = slope * Mag + ABoffset

    Parameters
    ----------
    df
        Merged ROTSE x PanSTARRS DataFrame (one exposure).
    fit
        The slopifier fit for this exposure. If ``None``, the function
        is a no-op and only sets the ``low_count_warning`` flag.
    mag_col
        Source column. Default ``"Mag"`` (raw ROTSE magnitude).
    out_col
        Name of the new column. Default ``"Mag_AB"``.

    Returns
    -------
    (df_out, flags)
    """
    flags = AbsoluteFlags()
    out = df.copy()
    if fit is None:
        flags.low_count_warning = True
        flags.notes.append("No ExposureFit provided")
        return out, flags

    if fit.counts < MIN_COUNTS:
        flags.low_count_warning = True

    if not (SLOPE_RANGE[0] <= fit.slope <= SLOPE_RANGE[1]):
        flags.slope_outside_expected = True
        flags.notes.append(f"slope={fit.slope:.4f} outside {SLOPE_RANGE}")

    if not (ABOFFSET_RANGE[0] <= fit.ab_offset <= ABOFFSET_RANGE[1]):
        flags.ab_offset_outside_expected = True
        flags.notes.append(f"ab_offset={fit.ab_offset:.4f} outside {ABOFFSET_RANGE}")

    out[out_col] = fit.slope * out[mag_col] + fit.ab_offset
    flags.correction_applied = True
    logger.debug("Applied absolute correction (slope=%.4f, off=%.4f) -> %s",
                 fit.slope, fit.ab_offset, out_col)
    return out, flags
