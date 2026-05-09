# Data Formats

This document describes the file formats and column conventions the
pipeline reads and writes. None of these files live in the repository -
they sit in the directories configured under `paths:` in
`config/pipeline_config.yaml`.

## Inputs

### ROTSE match structures

ROTSE produces match structures in two formats. Both are read uniformly
via `vsp.io.fits_reader`.

**ROTSE-3 - FITS (`*_match.fit`)**

A multi-extension FITS file. The pipeline cares about three HDUs:

| HDU | Contents                                                                  |
| --- | ------------------------------------------------------------------------- |
| 1   | Object table - parallel arrays `RA`, `DEC`, `M`, `MERR`, `FLAGS`, `JD`, `EXPTIME`, etc. Each row is a single object across all exposures: `M` and `MERR` are 2D (`n_objects x n_exposures`), `RA` and `DEC` are 1D. |
| 2   | Per-exposure auxiliary table - `ELEV` (telescope elevation), `DMOON`, `VPrecip`, ...; one row per exposure. Used by `diagnostics.plots`. |
| -   | Optional appended HDU written by the slopifier: `(Slope, ABoffset, counts)`, one row per exposure. |

**ROTSE-1 - IDL save (`*_match.dat` / `*_match.datc`)**

Read with `scipy.io.readsav`. The `match` record exposes the same field
names (`RA`, `DEC`, `M`, ...).

### PanSTARRS DR2 reference catalog (`MeanDR2pan{field}.csv`)

Standard PanSTARRS DR2 mean-object table written by
`catalog.fetch_field`. The columns are configured under
`panstarrs.columns` in the YAML:

`objID`, `objInfoFlag`, `qualityFlag`, `raMean`, `decMean`,
`gMeanPSFMag`, `gMeanPSFMagErr`, `gMeanKronMag`, `gMeanKronMagErr`,
`gFlags`, ... (same set of `*MeanPSFMag/*MeanKronMag/*Flags` for r, i, z, y).

The pipeline assumes a row may contain a `-999` sentinel in any
magnitude column. `vsp.calibration.cuts.drop_panstarrs_sentinels`
removes those rows.

## Intermediate outputs

### Per-exposure cross-match CSV (`{field}00{night}_exp{n}.csv`)

Written by `crossmatch.rotse_panstarrs`. One row per matched (ROTSE,
PanSTARRS) source. Columns are the union of:

* ROTSE block: `RA`, `Dec`, `Mag`, `Flags`
* PanSTARRS block: every column from `PAN_COLUMNS_DEFAULT` in
  `crossmatch/rotse_panstarrs.py`.

### Per-exposure RA/Dec extent (`coords{field}00{night}_exp{n}.csv`)

A 1-row CSV with `Min_RA`, `Max_RA`, `Min_Dec`, `Max_Dec`.

### Per-night summary (`updated_{field}_night{night}_summary.csv`)

Written by `calibration.slopifier`. One row per exposure:

| Column     | Meaning                                                       |
| ---------- | ------------------------------------------------------------- |
| Exposure   | 0-indexed exposure within the night                           |
| Slope      | linear-fit slope of `Mag` vs `pseudoBoloMag`                  |
| ABoffset   | linear-fit intercept                                          |
| Counts     | number of rows surviving the cuts                             |
| JulianDate | from HDU 1 `JD[exposure]`                                     |
| M_Lim      | brightest non-99 mag in this exposure (limiting-mag proxy)    |

### Pipeline run summary (`pipeline_run_{field}.json`)

Written by `pipeline.orchestrator`. Lists per-night row counts, plot
paths, and absolute/relative-photometry flags raised.

## Final outputs

### Calibrated light curve (`lightcurve_ra{ra}_dec{dec}.dat`)

Plain-text whitespace-separated table, one row per surviving epoch:

`JD  Mag  MagErr  Exptime_days  M_Lim`

Written by `calibration.lccal.save_lightcurve`. The companion
`log_ra{ra}_dec{dec}.dat` records the run's filtration / averaging
statistics.

## Filename conventions in code

All filenames are derived in `vsp.io.match_io`. Use those helpers
instead of hard-coding strings:

```python
from vsp.io.match_io import (
    match_file, panstarrs_csv, crossmatch_csv,
    coords_csv, summary_csv, lightcurve_csv,
)

match_file("sky0001_1a", "0824")          # -> {data_dir}/000824_sky0001_1a_match.fit
panstarrs_csv("sky0001_1a")               # -> {panstarrs_dir}/MeanDR2pansky0001_1a.csv
crossmatch_csv("sky0001_1a", "0824", 5)   # -> {crossmatch_dir}/sky0001_1a000824_exp5.csv
```
