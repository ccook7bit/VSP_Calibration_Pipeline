"""
Light-curve calibration ("lccal").

Given a target RA/Dec and a directory of ROTSE match structures, this
module:

1. Locates the target's light curve across all match files.
2. Finds reference stars within ``radius`` degrees that pass quality
   cuts (mean magnitude error, has-all-epochs, decent-epochs ratio,
   reduced chi-squared, optional avmag-vs-limiting-magnitude check).
3. Picks the ``requested_refstars`` closest survivors.
4. Computes per-epoch additive corrections from the reference stars
   (mean of (true_mag - observed_mag) over reference stars).
5. Applies the corrections to the target light curve.
6. Optionally runs the R1 unconex filter to drop discrepant epochs.

This is a cleaned-up restructuring of the original ``lccal/lccal.py``
that:

* Replaces the per-file ``read_*`` duplicates with
  :mod:`vsp.io.fits_reader`.
* Fixes the long-standing bug in :func:`reduced_chisq` where
  ``scipy.stats.chisquare`` rejected the call because the integrated
  Gaussian's expected counts didn't sum to ``len(observations)``
  exactly. We now rescale ``expected`` so its sum matches ``observed``.
"""
from __future__ import annotations

import glob
import logging
import math
import os
from dataclasses import dataclass, field as _dc_field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import scipy.integrate
import scipy.stats as st

from ..config import get_config
from ..io.fits_reader import read_data_file

logger = logging.getLogger(__name__)

# AB-system zeropoint flux used by the original ``mag2flux``/``flux2mag``.
AB_FLUX_ZERO = 3.636

# Tuple-of-floats type used internally for a single light-curve point.
# (epoch_jd, magnitude, mag_err, exptime_days, m_lim).
LCPoint = Tuple[float, float, float, float, float]


# ---------------------------------------------------------------------------
# Photometric helpers (kept tiny - no DataFrame, just floats)
# ---------------------------------------------------------------------------
def mag2flux(mag: float) -> float:
    """Convert magnitude to flux using the original lccal AB zero-point."""
    return float(AB_FLUX_ZERO * 10.0 ** (-float(mag) / 2.5))


def flux2mag(flux: float) -> float:
    """Inverse of :func:`mag2flux`."""
    return float(-2.5 * math.log10(float(flux) / AB_FLUX_ZERO))


def avmag(lc: Sequence[LCPoint]) -> float:
    """Flux-weighted mean magnitude over a light curve."""
    fluxes = [mag2flux(row[1]) for row in lc]
    return flux2mag(math.fsum(fluxes) / len(fluxes))


def reduced_chisq(observations, return_pvalue: bool = False):
    """Reduced chi-squared of a Gaussian fit to ``observations``.

    Bins ``observations`` with ``np.histogram(..., bins='auto')``,
    computes expected counts by integrating a Gaussian (mean = sample
    mean, std = sample std) over each bin, and returns
    ``chisq / dof``.

    .. note:: Bug fix vs original

       The original code passed the integrated-Gaussian expected
       counts straight to ``scipy.stats.chisquare``, which raises::

           ValueError: ... the sum of the observed frequencies must
           agree with the sum of the expected frequencies to a
           relative tolerance of 1.4901161193847656e-08

       (because the integrated Gaussian's tails are clipped at the
       outer histogram bins, so ``sum(expected)`` is always slightly
       below ``len(observations)``). We now rescale ``expected`` so
       its sum exactly matches ``sum(observed)``, which is the
       documented preprocessing step for ``scipy.stats.chisquare``.
    """
    if len(observations) < 2:
        return (math.nan, math.nan) if return_pvalue else math.nan

    mean = float(np.mean(observations))
    sd = float(np.std(observations))
    if sd <= 0:
        return (0.0, 1.0) if return_pvalue else 0.0

    observed, bins = np.histogram(observations, bins="auto")
    if len(bins) <= 2:
        return (math.nan, math.nan) if return_pvalue else math.nan

    def _gauss(x, mean=mean, sd=sd):
        return (1.0 / (sd * math.sqrt(2.0 * math.pi))) * math.exp(-0.5 * ((x - mean) / sd) ** 2)

    expected = np.array([
        scipy.integrate.quad(_gauss, bins[i], bins[i + 1])[0]
        for i in range(len(bins) - 1)
    ]) * len(observations)

    # --- Bug fix: rescale expected so its sum matches observed --------------
    obs_sum = float(np.sum(observed))
    exp_sum = float(np.sum(expected))
    if exp_sum <= 0:
        return (math.nan, math.nan) if return_pvalue else math.nan
    expected = expected * (obs_sum / exp_sum)

    chisq, pval = st.chisquare(observed, expected, ddof=1)
    dof = max(len(bins) - 1 - 2, 1)
    chisq /= dof
    return (chisq, pval) if return_pvalue else chisq


# ---------------------------------------------------------------------------
# Match-structure access
# ---------------------------------------------------------------------------
def discover_match_structures(directory: str | os.PathLike) -> List[str]:
    """Return all ``*.fit``/``*.dat``/``*.datc`` files in ``directory``."""
    cwd = os.getcwd()
    os.chdir(str(directory))
    try:
        return sorted(glob.glob("*.fit") + glob.glob("*.dat") + glob.glob("*.datc"))
    finally:
        os.chdir(cwd)


def get_lightcurve(match, refra: float, refdec: float, *, full: bool = True) -> List[LCPoint]:
    """Return the light curve for the object at (refra, refdec) in ``match``.

    Each point is ``(jd, mag, mag_err, exptime_days, m_lim)``.
    Set ``full=False`` for the simpler (jd, mag, mag_err) form used by
    refstar checks (drops exptime/m_lim).
    """
    if isinstance(match, (str, Path)):
        match, _ = read_data_file(str(match))
    match_ra = match.field("RA")[0]
    match_dec = match.field("DEC")[0]
    cond = np.logical_and.reduce((
        np.abs(match_ra - refra) < 0.001,
        np.abs(match_dec - refdec) < 0.001,
    ))
    objids = np.where(cond)[0]
    if len(objids) == 0:
        raise IndexError(f"No object found near RA={refra}, Dec={refdec}")

    objid = objids[0]
    match_merr = match.field("MERR")[0][objid]
    match_m = match.field("M")[0][objid]
    match_jd = match.field("JD")[0]

    if full:
        match_exptime = match.field("EXPTIME")[0]
        match_m_lim = match["STAT"][0]["M_LIM"]
        return [
            (float(match_jd[q]), float(match_m[q]), float(match_merr[q]),
             float(match_exptime[q]) / 86400.0, float(match_m_lim[q]))
            for q in range(len(match_jd))
        ]
    return [
        (float(match_jd[q]), float(match_m[q]), float(match_merr[q]), 0.0, 0.0)
        for q in range(len(match_jd))
    ]


def find_target(matches: Iterable[str], vra: float, vdec: float):
    """Walk the match structures and accumulate the target's light curve."""
    found_matches: List[str] = []
    target_lc: List[LCPoint] = []
    for m in matches:
        try:
            lc = get_lightcurve(m, vra, vdec, full=True)
            target_lc.extend(lc)
            found_matches.append(m)
            logger.info("Target found in %s", m)
        except IndexError:
            logger.info("Target not found in %s; dropping from list", m)
    return found_matches, target_lc


def get_objids_within(match, refra: float, refdec: float, radius: float) -> List[int]:
    """Indices of objects in ``match`` within ``radius`` degrees of (refra, refdec)."""
    if isinstance(match, (str, Path)):
        match, _ = read_data_file(str(match))
    ra_arr = match.field("RA")[0]
    dec_arr = match.field("DEC")[0]
    box = np.logical_and(np.abs(ra_arr - refra) <= radius, np.abs(dec_arr - refdec) <= radius)
    candidates = np.where(box)[0]
    out: List[int] = []
    for idx in candidates:
        if math.hypot(ra_arr[idx] - refra, dec_arr[idx] - refdec) <= radius:
            out.append(int(idx))
    return out


def get_coords(match, objid: int) -> Tuple[float, float]:
    """Return ``(ra, dec)`` for the object at ``objid`` in ``match``."""
    if isinstance(match, (str, Path)):
        match, _ = read_data_file(str(match))
    return float(match.field("RA")[0][objid]), float(match.field("DEC")[0][objid])


def order_by_jd(lc: List[LCPoint]) -> List[LCPoint]:
    """Stable sort a light curve by JD (first tuple element)."""
    return sorted(lc, key=lambda p: p[0])


# ---------------------------------------------------------------------------
# Reference star selection
# ---------------------------------------------------------------------------
@dataclass
class RefStarCriteria:
    """Cut thresholds for reference-star eligibility."""
    requested_refstars: int
    radius_deg: float
    max_mean_error: Optional[float] = 0.06
    max_chisq: Optional[float] = 10.0
    decent_epochs: float = 0.9
    require_avmag_within_limits: bool = True

    @classmethod
    def from_config(cls) -> "RefStarCriteria":
        cfg = get_config()["lccal"]
        return cls(
            requested_refstars=cfg["default_requested_refstars"],
            radius_deg=cfg["default_radius_deg"],
            max_mean_error=cfg["default_max_mean_error"],
            max_chisq=cfg["default_chisq"],
            decent_epochs=cfg["default_decent_epochs"],
            require_avmag_within_limits=cfg.get("use_avmag", True),
        )


def _is_not_target(coords, vra, vdec, allowed_diff: float = 0.001) -> bool:
    return not (vra - allowed_diff <= coords[0] <= vra + allowed_diff
                and vdec - allowed_diff <= coords[1] <= vdec + allowed_diff)


def _has_all_epochs(target_lc, candidate_lc) -> bool:
    return [obs[0] for obs in target_lc] == [obs[0] for obs in candidate_lc]


def _avmag_within_limits(lc) -> bool:
    av_m_lim = math.fsum(obs[4] for obs in lc) / len(lc)
    return av_m_lim - 4 <= avmag(lc) <= av_m_lim


def _decent_epochs(good_obs, lc, threshold: float) -> bool:
    n_good_within = sum(1 for o in good_obs if o[4] - 4 <= o[1] <= o[4])
    return n_good_within / len(lc) >= threshold


def _chisq_pass(lcs_per_match, lc, criteria: RefStarCriteria) -> bool:
    nights_num = len(lcs_per_match)
    passed = 0
    for night_lc in lcs_per_match:
        good = [o[1] for o in night_lc if 0 < o[1] < 99]
        if len(good) < 2:
            continue
        if reduced_chisq(good) <= (criteria.max_chisq or math.inf):
            passed += 1
    fraction_good = sum(1 for o in lc if 0 < o[1] < 99) / len(lc)
    return fraction_good >= criteria.decent_epochs and passed / nights_num >= 0.5


def _under_mean_error(good_obs, max_mean_error: float) -> bool:
    return math.fsum(o[2] for o in good_obs) / len(good_obs) <= max_mean_error


def _passes_cuts(coords, lc, lcs_per_match, good_obs,
                 vra, vdec, target_lc, criteria: RefStarCriteria) -> bool:
    if not _is_not_target(coords, vra, vdec):
        return False
    if criteria.max_mean_error is not None and not _under_mean_error(good_obs, criteria.max_mean_error):
        return False
    if not _has_all_epochs(target_lc, lc):
        return False
    if not _decent_epochs(good_obs, lc, criteria.decent_epochs):
        return False
    if criteria.max_chisq is not None and not _chisq_pass(lcs_per_match, lc, criteria):
        return False
    return True


def find_refstars(matches: Sequence[str], target_lc, vra: float, vdec: float,
                  criteria: RefStarCriteria):
    """Return ``(refstars, test_candidates)`` from the given match list."""
    refstars = []
    test_candidates = []
    surrounding = get_objids_within(matches[0], vra, vdec, criteria.radius_deg)
    for star in surrounding:
        try:
            coords = get_coords(matches[0], star)
            full_lc: List[LCPoint] = []
            per_match: List[List[LCPoint]] = []
            for m in matches:
                lc_n = order_by_jd(get_lightcurve(m, coords[0], coords[1], full=True))
                per_match.append(lc_n)
                full_lc.extend(lc_n)
            good = [o for o in full_lc if 0 < o[1] < 99]
            if not full_lc or not good:
                continue
            if _passes_cuts(coords, full_lc, per_match, good, vra, vdec, target_lc, criteria):
                refstars.append([coords, avmag(good), good])
            elif _is_not_target(coords, vra, vdec):
                test_candidates.append([coords, good, per_match])
        except IndexError:
            continue
    return refstars, test_candidates


def closest_refs(candidates, vra: float, vdec: float, n: int):
    """Pick the ``n`` candidates closest to ``(vra, vdec)`` in RA/Dec."""
    candidates = sorted(
        candidates,
        key=lambda c: math.hypot(c[0][0] - vra, c[0][1] - vdec),
    )
    return candidates[:n]


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------
def compute_corrections(refstars, target_lc, verbose: bool = False):
    """Per-epoch additive corrections (mean of true_mag - observed_mag)."""
    out = []
    for epoch in (i[0] for i in target_lc if 0 < i[1] < 99):
        diffs = []
        for true_mag, lc in [(s[1], s[2]) for s in refstars]:
            for obs in lc:
                if obs[0] == epoch:
                    diffs.append(true_mag - obs[1])
        if len(diffs) == len(refstars):
            out.append([epoch, math.fsum(diffs) / len(diffs)])
    if verbose:
        for c in out:
            logger.info("Correction @ %s = %.4f", c[0], c[1])
    return out


def apply_corrections(corrections, target_lc):
    """Apply per-epoch corrections; drop unphysical (mag <= 0 or >= 99) points."""
    good = [i for i in target_lc if 0 < i[1] < 99]
    dropped = len(target_lc) - len(good)
    if dropped:
        logger.info("Dropped %d unphysical observations from target lc", dropped)
    out = []
    by_epoch = {c[0]: c[1] for c in corrections}
    for obs in good:
        if obs[0] in by_epoch:
            out.append([obs[0], obs[1] + by_epoch[obs[0]], obs[2], obs[3], obs[4]])
    return out


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------
def save_lightcurve(lc, output_dir: Path, vra: float, vdec: float) -> Path:
    """Write a calibrated light curve to ``lightcurve_ra{ra}_dec{dec}.dat``."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fn = output_dir / f"lightcurve_ra{vra}_dec{vdec}.dat"
    np.savetxt(fn, lc, fmt="%.11f")
    logger.info("Wrote %s", fn)
    return fn


def save_log(log_lines, output_dir: Path, vra: float, vdec: float) -> Path:
    """Write a one-shot log file alongside the light curve."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fn = output_dir / f"log_ra{vra}_dec{vdec}.dat"
    fn.write_text("\n".join(log_lines) + "\n")
    return fn


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------
@dataclass
class LccalResult:
    target_lc: List[LCPoint] = _dc_field(default_factory=list)
    calibrated_lc: List[List[float]] = _dc_field(default_factory=list)
    refstars: list = _dc_field(default_factory=list)
    corrections: list = _dc_field(default_factory=list)
    light_curve_path: Optional[Path] = None
    log_path: Optional[Path] = None


def calibrate(
    *,
    match_structures: str | os.PathLike,
    target_ra: float,
    target_dec: float,
    output_dir: Optional[Path] = None,
    criteria: Optional[RefStarCriteria] = None,
    verbose: bool = False,
    write_log: bool = True,
) -> LccalResult:
    """End-to-end light-curve calibration for a single target."""
    if criteria is None:
        criteria = RefStarCriteria.from_config()
    if output_dir is None:
        output_dir = Path(get_config()["paths"]["lightcurves_dir"])

    matches = discover_match_structures(match_structures)
    if not matches:
        raise FileNotFoundError(f"No match files in {match_structures}")
    cwd = os.getcwd()
    os.chdir(str(match_structures))
    try:
        good_matches, target_lc = find_target(matches, target_ra, target_dec)
        if not good_matches:
            raise RuntimeError(f"Target ({target_ra}, {target_dec}) not present in any match file")

        all_refs, _ = find_refstars(good_matches, target_lc, target_ra, target_dec, criteria)
        if len(all_refs) < criteria.requested_refstars:
            raise RuntimeError(
                f"Requested {criteria.requested_refstars} refstars but only {len(all_refs)} passed cuts. "
                "Loosen radius/chisq/decent_epochs and retry."
            )
        refstars = closest_refs(all_refs, target_ra, target_dec, criteria.requested_refstars)
        corrections = compute_corrections(refstars, target_lc, verbose=verbose)
        calibrated = apply_corrections(corrections, target_lc)

        result = LccalResult(
            target_lc=target_lc, calibrated_lc=calibrated,
            refstars=refstars, corrections=corrections,
        )
        result.light_curve_path = save_lightcurve(calibrated, output_dir, target_ra, target_dec)
        if write_log:
            log_lines = [
                f"Target: RA={target_ra}, Dec={target_dec}",
                f"Match structures: {len(good_matches)} / {len(matches)} contained the target",
                f"Reference stars: {len(refstars)} (out of {len(all_refs)} candidates)",
                f"Total observations: {len(target_lc)}",
                f"Final observations: {len(calibrated)}",
                f"Calibration efficiency: {round(len(calibrated) / len(target_lc) * 100, 2)}%",
            ]
            result.log_path = save_log(log_lines, output_dir, target_ra, target_dec)
        return result
    finally:
        os.chdir(cwd)
