"""
Per-exposure photometric calibration fit ("slopifier").

For each exposure of a field+night:

1. Read the merged ROTSE x PanSTARRS CSV produced by
   :mod:`vsp.crossmatch.rotse_panstarrs`.
2. Apply quality cuts (mag window, drop ``-999`` sentinels, optional
   Kron/color cut).
3. Compute a pseudo-bolometric magnitude per row from the PanSTARRS
   grizy magnitudes (see :mod:`vsp.calibration.photometry`).
4. Linear-fit ``Mag`` vs ``pseudoBoloMag`` to get
   ``(slope, ABoffset, counts)``.

Per-exposure rows are appended as a new BinTable HDU to a copy of the
match FITS file, and a per-night summary CSV is written to
``cfg['paths']['summary_dir']``.

Replaces ``slopifier/Slopifier.py`` and the per-night looped versions in
``BigSlopifier.ipynb`` / ``Big2Slopifer.ipynb``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

import numpy as np
import pandas as pd
from astropy.io import fits
from astropy.table import Table

from ..config import get_config
from ..io.match_io import crossmatch_csv, match_file, summary_csv
from . import cuts, photometry

logger = logging.getLogger(__name__)


@dataclass
class ExposureFit:
    """Fit result for a single exposure."""
    exposure: int
    slope: float
    ab_offset: float
    counts: int
    julian_date: Optional[float] = None
    m_lim: Optional[float] = None


@dataclass
class NightSummary:
    """Aggregate slopifier results for one field+night."""
    field: str
    night: str
    fits: List[ExposureFit] = field(default_factory=list)

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "Exposure": fit_.exposure,
                "Slope": fit_.slope,
                "ABoffset": fit_.ab_offset,
                "Counts": fit_.counts,
                "JulianDate": fit_.julian_date,
                "M_Lim": fit_.m_lim,
            }
            for fit_ in self.fits
        ])


def slopify_exposure(csv_path: Path, slop_cfg: Optional[dict] = None) -> Optional[ExposureFit]:
    """Fit a single exposure CSV; returns ``None`` if data is too sparse for ``polyfit``."""
    if slop_cfg is None:
        slop_cfg = get_config()["slopifier"]

    if not Path(csv_path).is_file():
        logger.warning("Exposure CSV missing: %s", csv_path)
        return None

    df = pd.read_csv(csv_path)
    df = df.drop_duplicates(subset=["RA", "Dec"])
    df = cuts.magnitude_window(df, mag_col="Mag",
                               mag_min=slop_cfg["mag_min"], mag_max=slop_cfg["mag_max"])
    if slop_cfg.get("drop_panstarrs_sentinels", True):
        df = cuts.drop_panstarrs_sentinels(df)

    df = photometry.add_band_fluxes(df, ab_zeropoint=slop_cfg["ab_zeropoint"])
    df = photometry.pseudo_bolometric_magnitude(
        df,
        weights=slop_cfg["bolometric_weights"],
        norm=slop_cfg["bolometric_norm"],
        ab_zeropoint=slop_cfg["ab_zeropoint"],
        ab_flux_zero_jy=slop_cfg["ab_flux_zero_jy"],
        flux_columns=True,
    )

    df["Difference"] = df["pseudoBoloMag"] - df["Mag"]

    if slop_cfg.get("apply_color_cut"):
        df, *_ = cuts.color_cut(df,
                                pair_1=slop_cfg.get("color_pair_1", "gr"),
                                pair_2=slop_cfg.get("color_pair_2", "ri"))

    if slop_cfg.get("apply_kron_cut", True):
        df, *_ = cuts.kron_cut(df,
                               band=slop_cfg.get("kron_band", "g"),
                               max_dist=slop_cfg.get("kron_dist", 0.5))

    if len(df) < 2:
        logger.warning("%s: not enough rows after cuts (%d) -- skipping fit", csv_path, len(df))
        return None

    slope, intercept, _ = photometry.linear_fit(df["Mag"], df["pseudoBoloMag"], with_cov=True)
    # Exposure index is encoded in the filename: ..._exp{n}.csv
    try:
        exposure = int(Path(csv_path).stem.rsplit("_exp", 1)[-1])
    except ValueError:
        exposure = -1
    return ExposureFit(
        exposure=exposure,
        slope=slope,
        ab_offset=intercept,
        counts=len(df),
    )


def slopify_night(field: str, night: str,
                  exposures: Optional[Iterable[int]] = None,
                  append_to_fits: bool = True,
                  write_summary_csv: bool = True) -> NightSummary:
    """Run :func:`slopify_exposure` over every exposure for ``field``+``night``."""
    cfg = get_config()
    slop_cfg = cfg["slopifier"]

    if exposures is None:
        exposures = _discover_exposures(field, night)

    summary = NightSummary(field=field, night=night)
    julian_dates, limiting_mags = _read_jd_and_mlim(field, night)

    for n in exposures:
        csv_path = crossmatch_csv(field, night, n)
        fit_ = slopify_exposure(csv_path, slop_cfg)
        if fit_ is None:
            continue
        if julian_dates is not None and 0 <= n < len(julian_dates):
            fit_.julian_date = float(julian_dates[n])
        if limiting_mags is not None and 0 <= n < len(limiting_mags):
            fit_.m_lim = float(limiting_mags[n])
        summary.fits.append(fit_)
        logger.debug("Exposure %d: slope=%.4f offset=%.4f n=%d",
                     fit_.exposure, fit_.slope, fit_.ab_offset, fit_.counts)

    if append_to_fits:
        _append_summary_to_fits(field, night, summary)
    if write_summary_csv:
        out_path = summary_csv(field, night)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        summary.to_dataframe().to_csv(out_path, index=False)
        logger.info("Wrote per-night summary CSV: %s", out_path)

    return summary


def slopify_field(field: str, nights: Iterable[str], **kwargs) -> dict:
    """Run :func:`slopify_night` over a sequence of nights."""
    return {n: slopify_night(field, n, **kwargs) for n in nights}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _discover_exposures(field: str, night: str) -> List[int]:
    """List the exposure indices for which we have a crossmatch CSV on disk."""
    cfg = get_config()
    base = Path(cfg["paths"]["crossmatch_dir"])
    pattern = f"{field}00{night}_exp*.csv"
    expos: List[int] = []
    for f in base.glob(pattern):
        try:
            expos.append(int(f.stem.rsplit("_exp", 1)[-1]))
        except ValueError:
            continue
    return sorted(expos)


def _read_jd_and_mlim(field: str, night: str):
    """Pull JD + a per-exposure limiting magnitude from the match FITS, if available."""
    fits_path = match_file(field, night, ext="fit")
    if not fits_path.is_file():
        return None, None
    try:
        with fits.open(fits_path) as hdul:
            data = hdul[1].data
            if "JD" not in data.columns.names or "M" not in data.columns.names:
                return None, None
            jd_arr = np.asarray(data["JD"][0])
            m_arr = np.asarray(data["M"][0])
            # Limiting mag per exposure: take the brightest detection.
            # (Crude proxy used by the original `find_limiting_magnitude`.)
            n_exp = m_arr.shape[-1] if m_arr.ndim >= 1 else 0
            m_lim = []
            for i in range(n_exp):
                col = m_arr[..., i].ravel()
                col = col[(col > 0) & (col < 99)]
                m_lim.append(np.nanmax(col) if len(col) else np.nan)
            return jd_arr, np.asarray(m_lim)
    except Exception as exc:
        logger.warning("Could not extract JD/M from %s: %s", fits_path, exc)
        return None, None


def _append_summary_to_fits(field: str, night: str, summary: NightSummary) -> None:
    """Append the (slope, ABoffset, counts) Table as a new HDU on the match FITS."""
    fits_path = match_file(field, night, ext="fit")
    if not fits_path.is_file():
        logger.warning("No FITS to append summary to: %s", fits_path)
        return
    table = Table(
        [
            [f.slope for f in summary.fits],
            [f.ab_offset for f in summary.fits],
            [f.counts for f in summary.fits],
        ],
        names=("Slope", "ABoffset", "counts"),
    )
    hdu = fits.BinTableHDU(table, name=f"SLOP_{night}")
    with fits.open(fits_path, mode="update") as hdul:
        hdul.append(hdu)
        hdul.flush()
    logger.info("Appended slopifier HDU to %s", fits_path)
