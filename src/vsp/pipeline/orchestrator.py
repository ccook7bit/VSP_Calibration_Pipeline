"""
End-to-end pipeline orchestrator.

Replaces the skeleton ``vsp_pipeline/Pipeline.py``. The real flow for a
given field+nights is:

1. (Optional) fetch the PanSTARRS reference catalog if it's missing.
2. Cross-match ROTSE detections against PanSTARRS, write per-exposure CSVs.
3. Run the slopifier per night to get the per-exposure
   ``(slope, ABoffset, counts)`` calibration tables.
4. Generate diagnostic plots.
5. Run the absolute and relative photometric checks on each exposure
   (these were the stubbed ``ap.check_and_correct`` /
   ``rp.check_and_correct`` calls in the original ``Pipeline.py``).

The function logs the per-night flags and writes a single end-of-run
summary log under ``cfg['paths']['summary_dir']``.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

from ..calibration.slopifier import NightSummary, slopify_night
from ..catalog.fetch_field import fetch_field
from ..config import get_config, setup_logging
from ..crossmatch.rotse_panstarrs import crossmatch_night
from ..diagnostics.plots import plot_night_diagnostics
from ..io.match_io import (
    crossmatch_csv,
    list_nights_for_field,
    panstarrs_csv,
    summary_csv,
)
from . import absolute_photo, relative_photo

logger = logging.getLogger(__name__)


@dataclass
class PipelineRun:
    field: str
    nights: List[str]
    panstarrs_csv: Optional[Path] = None
    crossmatched: dict = field(default_factory=dict)
    slopifier: dict = field(default_factory=dict)
    plots: dict = field(default_factory=dict)
    flags: dict = field(default_factory=dict)


def run_pipeline(
    field: str,
    nights: Optional[Iterable[str]] = None,
    *,
    fetch_catalog: bool = False,
    do_crossmatch: bool = True,
    do_slopify: bool = True,
    do_plots: bool = True,
    do_photo_checks: bool = True,
) -> PipelineRun:
    """Run the full pipeline for one field over a list of nights.

    Parameters
    ----------
    field
        Field name (must be defined in the config).
    nights
        Iterable of night tags. If ``None``, every night discovered in
        ``cfg['paths']['data_dir']`` for ``field`` is used.
    fetch_catalog
        If True, run :func:`vsp.catalog.fetch_field.fetch_field` first.
        Otherwise the existing per-field PanSTARRS CSV is used.
    do_crossmatch / do_slopify / do_plots / do_photo_checks
        Toggles for individual stages, in case a previous run already
        produced their outputs.
    """
    setup_logging()
    cfg = get_config()
    nights = list(nights) if nights is not None else list_nights_for_field(field)
    run = PipelineRun(field=field, nights=nights)

    if fetch_catalog:
        run.panstarrs_csv = fetch_field(field)
    else:
        run.panstarrs_csv = panstarrs_csv(field)
        if not run.panstarrs_csv.exists():
            logger.warning("PanSTARRS CSV not found at %s -- run with fetch_catalog=True",
                           run.panstarrs_csv)

    for night in nights:
        try:
            if do_crossmatch:
                run.crossmatched[night] = crossmatch_night(field, night)
            if do_slopify:
                run.slopifier[night] = slopify_night(field, night)
            if do_plots:
                try:
                    run.plots[night] = plot_night_diagnostics(field, night)
                except Exception as exc:
                    logger.warning("Plotting failed for %s night=%s: %s", field, night, exc)
            if do_photo_checks:
                run.flags[night] = _photo_checks_for_night(field, night, run.slopifier.get(night))
        except FileNotFoundError as exc:
            logger.warning("Skipping %s night=%s: %s", field, night, exc)

    _write_run_summary(run)
    return run


def _photo_checks_for_night(field: str, night: str, summary: Optional[NightSummary]) -> dict:
    """Run absolute_photo.check_and_correct + relative_photo.check_and_correct per exposure."""
    if summary is None:
        return {}
    flags_per_exposure: dict = {}
    fits_by_exposure = {f.exposure: f for f in summary.fits}
    for exposure, fit_ in fits_by_exposure.items():
        csv_path = crossmatch_csv(field, night, exposure)
        if not csv_path.is_file():
            continue
        try:
            df = pd.read_csv(csv_path)
        except Exception:
            continue
        df_abs, abs_flags = absolute_photo.check_and_correct(df, fit_)
        df_rel, rel_flags = relative_photo.check_and_correct(df_abs)
        flags_per_exposure[exposure] = {
            "absolute": abs_flags.as_dict(),
            "relative": rel_flags.as_dict(),
            "n_rows_in": int(len(df)),
            "n_rows_out": int(len(df_rel)),
            "abs_notes": list(abs_flags.notes),
            "rel_notes": list(rel_flags.notes),
        }
    return flags_per_exposure


def _write_run_summary(run: PipelineRun) -> Path:
    """Drop a JSON summary of this run into ``cfg['paths']['summary_dir']``."""
    cfg = get_config()
    out_dir = Path(cfg["paths"]["summary_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"pipeline_run_{run.field}.json"
    serializable = {
        "field": run.field,
        "nights": run.nights,
        "panstarrs_csv": str(run.panstarrs_csv) if run.panstarrs_csv else None,
        "crossmatched_counts": {k: len(v) for k, v in run.crossmatched.items()},
        "slopifier_counts": {k: len(v.fits) for k, v in run.slopifier.items()},
        "plots": {k: [str(p) for p in v] for k, v in run.plots.items()},
        "flags_per_night": run.flags,
    }
    out.write_text(json.dumps(serializable, indent=2))
    logger.info("Wrote run summary to %s", out)
    return out
