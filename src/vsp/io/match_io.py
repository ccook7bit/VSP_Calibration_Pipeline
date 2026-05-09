"""
Higher-level helpers for locating and naming match files.

Centralizes the filename conventions that were previously hard-coded
throughout the codebase, e.g.::

    {data_dir}/00{night}_{field}_match.fit
    {panstarrs_dir}/MeanDR2pan{field}.csv
    {crossmatch_dir}/{field}00{night}_exp{n}.csv
    {summary_dir}/updated_{field}_night{night}_summary.csv
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..config import get_config, get_path


def match_file(field: str, night: str, ext: str = "fit") -> Path:
    """Path to the ROTSE match structure for a given field+night."""
    return get_path("data_dir") / f"00{night}_{field}_match.{ext}"


def panstarrs_csv(field: str) -> Path:
    """Per-field PanSTARRS DR2 reference catalog (one CSV per field)."""
    return get_path("panstarrs_dir") / f"MeanDR2pan{field}.csv"


def crossmatch_csv(field: str, night: str, exposure: int) -> Path:
    """Per-exposure ROTSE x PanSTARRS merge produced by `crossmatch.rotse_panstarrs`."""
    return get_path("crossmatch_dir") / f"{field}00{night}_exp{exposure}.csv"


def coords_csv(field: str, night: str, exposure: int) -> Path:
    """Per-exposure RA/Dec extent summary written alongside the merged CSV."""
    return get_path("crossmatch_dir") / f"coords{field}00{night}_exp{exposure}.csv"


def summary_csv(field: str, night: str) -> Path:
    """Per-night summary CSV (one row per exposure: slope/AB/counts/M_Lim/JD/...)."""
    return get_path("summary_dir") / f"updated_{field}_night{night}_summary.csv"


def lightcurve_csv(target_ra: float, target_dec: float) -> Path:
    """Final calibrated light-curve filename for a target."""
    base = get_path("lightcurves_dir")
    return base / f"lc_{target_ra:.6f}_{target_dec:.6f}.csv"


def list_nights_for_field(field: str, ext: str = "fit") -> list[str]:
    """Inspect ``data_dir`` and pull out every ``00XXXX_{field}_match.<ext>`` night tag."""
    pat = f"00*_{field}_match.{ext}"
    nights: list[str] = []
    for f in get_path("data_dir").glob(pat):
        # filename: 00XXXX_{field}_match.<ext>  -> XXXX
        stem = f.name.split("_")[0]
        if stem.startswith("00") and len(stem) >= 4:
            nights.append(stem[2:])
    return sorted(nights)


def existing_paths(paths: Iterable[Path]) -> list[Path]:
    """Filter an iterable of paths down to those that actually exist."""
    return [p for p in paths if Path(p).exists()]
