# Pipeline Overview

The VSP Recalibration Pipeline ties ROTSE-1 / ROTSE-3 / VSP photometry to
the PanSTARRS DR2 reference catalog, produces per-exposure calibration
coefficients, and ultimately delivers calibrated light curves for
individual variable-star targets.

## End-to-end data flow

```
                    +-----------------------------------------+
                    | catalog.fetch_field                     |
                    | walks an N x M grid of 0.5 deg cone     |
                    | searches over a survey field's RA/Dec   |
                    | range and concatenates the CSV results. |
                    +-------------------+---------------------+
                                        |
                                        v
                       MeanDR2pan{field}.csv (one per field)
                                        |
                                        v
                    +-----------------------------------------+
                    | crossmatch.rotse_panstarrs              |
                    | for each field+night:                   |
                    |   read *_match.fit (RA, Dec, Mag, Flags)|
                    |   pre-filter PanSTARRS by 5 arcsec      |
                    |     to any ROTSE detection (and v.v.)   |
                    |   for each exposure:                    |
                    |     build cKDTree, match within 5"      |
                    |     emit {field}00{night}_exp{n}.csv    |
                    +-------------------+---------------------+
                                        |
                                        v
                    +-----------------------------------------+
                    | calibration.slopifier                   |
                    | for each exposure CSV:                  |
                    |   apply mag window + Kron/color cuts    |
                    |   compute pseudo-bolometric mag from    |
                    |     PanSTARRS grizy fluxes              |
                    |   linear fit Mag vs pseudoBoloMag       |
                    |   accumulate (slope, ABoffset, counts)  |
                    | write summary CSV + append HDU to FITS  |
                    +-------------------+---------------------+
                                        |
                                        v
                    +-----------------------------------------+
                    | diagnostics.plots                       |
                    | per night, render slope/AB/counts/M_lim |
                    | vs JD, weather, elevation               |
                    +-------------------+---------------------+
                                        |
                                        v
                    +-----------------------------------------+
                    | calibration.lccal                       |
                    | for a single target:                    |
                    |   find target in match structures       |
                    |   pick refstars within radius passing   |
                    |     mean-error / chisq / decent-epochs  |
                    |   compute per-epoch corrections         |
                    |   apply + (optional) unconex filter     |
                    |   write lightcurve_ra*_dec*.dat         |
                    +-----------------------------------------+
```

## Stage responsibilities

### 1. Catalog fetch (`vsp.catalog.fetch_field`)

Walks a configured RA/Dec grid for a field and assembles a single
PanSTARRS DR2 reference CSV. Field grids are defined in
`config/pipeline_config.yaml` under `fields:`.

This used to be three near-identical scripts (`DR2API_queries{,2,3}.py`)
that only differed in their hardcoded output filename and field bounds.

### 2. Cross-match (`vsp.crossmatch.rotse_panstarrs`)

For each `*_match.fit` file:
1. Reads the four parallel arrays (RA, Dec, Mag, Flags) via
   `vsp.io.fits_reader.FitReader`.
2. Coarse-filters PanSTARRS rows to those within 5 arcsec of any ROTSE
   detection using astropy's `match_to_catalog_sky`.
3. For every exposure, builds a `scipy.spatial.cKDTree` and matches
   PanSTARRS rows to ROTSE rows within 5 arcsec.
4. Writes the merged DataFrame to `{field}00{night}_exp{n}.csv` and a
   tiny `coords{field}00{night}_exp{n}.csv` describing the per-exposure
   RA/Dec extent.

This is the consolidated form of `AutoPSFinder.py`,
`AutoPSFinderRevamped.py`, and `PSFinderCanon.py`. The RA-wrap fix
(`PSFinderCanon` only) is preserved.

### 3. Slopifier (`vsp.calibration.slopifier`)

Per exposure:
1. Drop duplicate (RA, Dec) rows.
2. Apply a magnitude window (`mag_min`/`mag_max` from config).
3. Drop rows where any PanSTARRS PSF/Kron magnitude is the `-999`
   sentinel.
4. Compute `gflux..yflux` from `{band}MeanPSFMag`.
5. Compute `pseudoBoloMag` from a weighted sum of band fluxes (see
   [`calibration_math.md`](calibration_math.md)).
6. Optional Kron-cut and color-cut.
7. `polyfit(Mag, pseudoBoloMag, deg=1)` -> `(slope, intercept)`.

Per night, the (slope, ABoffset, counts) row table is written to a
summary CSV and (optionally) appended as a new BinTable HDU to the
match FITS file.

### 4. Diagnostic plots (`vsp.diagnostics.plots`)

Reads the per-night summary CSV plus the `ELEV` column from HDU 2 of
the match FITS, and produces three multi-panel PNGs:

| File                                | Panels                                                    |
| ----------------------------------- | --------------------------------------------------------- |
| `{field}_{night}_combined_plot.png` | Slope, ABoffset, Counts, M_Lim vs Julian Date             |
| `{field}_{night}_diag3plots.png`    | Slope/ABoffset/Counts vs Counts; DMoon, VPrecip vs Counts |
| `{field}_{night}_diag4plots.png`    | Elevation vs JD; Counts/M_Lim/Slope vs Elevation          |

### 5. Light-curve calibration (`vsp.calibration.lccal`)

Per target (RA, Dec):
1. Walk a directory of match structures, accumulate the target's light
   curve across all nights.
2. Find candidate reference stars within `radius` degrees that pass:
   - `max_mean_error` (default 0.06 mag)
   - `decent_epochs` (default 90% of epochs valid)
   - `max_chisq` (reduced chi-squared of nightly Gaussian fits)
   - has-all-epochs (refstar epochs == target epochs)
   - optional avmag-vs-limiting-magnitude window
3. Pick the `requested_refstars` closest survivors.
4. For each target epoch, compute
   `correction = mean(true_mag - observed_mag)` over reference stars.
5. Apply the corrections to the target light curve.
6. Optionally run the R1 unconex filter to drop discrepant epochs.

**Bug fix**: the original `get_chisq` passed integrated-Gaussian
expected counts to `scipy.stats.chisquare` without rescaling. Because
the integrated Gaussian's tails are clipped at the outer histogram
bins, `sum(expected) < len(observations)` always, and recent SciPy
raises a `ValueError`. The new `reduced_chisq` rescales `expected` so
its sum matches `sum(observed)` before calling `chisquare`. See the
note in `calibration/lccal.py`.

### 6. Orchestrator (`vsp.pipeline.orchestrator`)

Chains stages 2-4 (and optionally 1) for a given field and a list of
nights, plus runs `pipeline.absolute_photo` and `pipeline.relative_photo`
on each per-exposure CSV. Writes a JSON summary of the run.

## Configuration

All paths and tunable parameters live in
[`config/pipeline_config.yaml`](../config/pipeline_config.yaml). Override
with `--config <path>` or `VSP_CONFIG=<path>`.

## Where the pieces came from

| Original zip       | Migrated to                                      |
| ------------------ | ------------------------------------------------ |
| `panstarrs_api`    | `catalog/`                                       |
| `updatedpanapi`    | `catalog/` + `crossmatch/`                       |
| `autopsfinder`     | `crossmatch/` (superseded by `updatedpanapi`)    |
| `slopifier`        | `calibration/`                                   |
| `matchedmanip`     | `diagnostics/`                                   |
| `lccal`            | `calibration/lccal.py`                           |
| `vsp_pipeline`     | `pipeline/` (real implementations of the stubs)  |
| `pyfiles`          | distributed across `calibration/photometry.py`,  |
|                    | `crossmatch/`, `calibration/lccal.py`            |
| `datmanip`         | `reader.py` was unrelated MPI-AMRVAC code -      |
|                    | dropped. `reader2.py` was a tiny .dat helper -   |
|                    | folded into `io/` if needed later.               |
