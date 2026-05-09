"""
Walk a survey field with overlapping cone searches and assemble a single
PanSTARRS DR2 reference catalog CSV.

Replaces the three near-identical scripts ``DR2API_queries.py``,
``DR2API_queries2.py``, and ``DR2API_queries3.py``, which only differed
in their hard-coded RA/Dec grid and output filename.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
from astropy.io import ascii

from ..config import get_config, get_field
from ..io.match_io import panstarrs_csv
from .panstarrs_api import ps1cone

logger = logging.getLogger(__name__)


def fetch_field(field: str, output: Optional[Path] = None, verbose: bool = True) -> Path:
    """Build a PanSTARRS DR2 reference catalog for ``field``.

    The function reads the field's RA/Dec grid from
    ``cfg['fields'][field]`` and ``cfg['panstarrs']`` from the config,
    walks a ``num_ra x num_dec`` grid of cone searches at
    ``cone_radius_deg``, and concatenates all returned CSV bodies.

    Parameters
    ----------
    field
        Field name (must be a key in ``cfg['fields']``).
    output
        Optional override for the output CSV path. Defaults to
        ``{panstarrs_dir}/MeanDR2pan{field}.csv``.
    verbose
        If True, log the URL of each cone-search request.

    Returns
    -------
    Path to the written CSV.
    """
    cfg = get_config()
    field_cfg = get_field(field)
    pan_cfg = cfg["panstarrs"]

    ra_grid = np.linspace(field_cfg["ra_min"], field_cfg["ra_max"], num=field_cfg["num_ra"])
    dec_grid = np.linspace(field_cfg["dec_min"], field_cfg["dec_max"], num=field_cfg["num_dec"])

    constraints = {"nDetections.gt": pan_cfg.get("min_detections", 1)}
    columns = [c.strip() for c in pan_cfg["columns"] if c and not c.strip().startswith("#")]

    radius = pan_cfg["cone_radius_deg"]
    release = pan_cfg["release"]
    table = pan_cfg["table"]
    base_url = pan_cfg["base_url"]

    logger.info(
        "Fetching PanSTARRS %s/%s for field=%s : %d x %d grid, radius=%.2f deg",
        release, table, field, len(ra_grid), len(dec_grid), radius,
    )

    chunks: list[str] = []
    for i, ra in enumerate(ra_grid):
        for j, dec in enumerate(dec_grid):
            payload = ps1cone(
                ra, dec, radius,
                table=table, release=release, columns=columns,
                baseurl=base_url, verbose=verbose, **constraints,
            )
            # Drop the header row on every grid point after the first.
            lines = payload.split("\n")
            if chunks:
                lines = lines[1:]
            chunks.append("\n".join(lines))
            if verbose:
                logger.debug("Grid (%d, %d) -> %d rows", i, j, len(lines) - 1)

    combined = "\n".join(chunks)
    table_data = ascii.read(combined)

    out_path = Path(output) if output is not None else panstarrs_csv(field)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ascii.write(table_data, out_path, format="csv", overwrite=True)
    logger.info("Wrote %d rows to %s", len(table_data), out_path)
    return out_path
