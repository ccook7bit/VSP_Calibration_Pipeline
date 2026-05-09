# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2026-05-08

The first packaged release. Consolidates the pipeline previously
distributed across nine separate zip archives
(`autopsfinder`, `datmanip`, `lccal`, `matchedmanip`, `panstarrs_api`,
`pyfiles`, `slopifier`, `updatedpanapi`, `vsp_pipeline`) into a single
installable Python package, with documentation, tests, and CI.

### Added

- `vsp` Python package under `src/`, with submodules
  `io`, `catalog`, `crossmatch`, `calibration`, `diagnostics`, `pipeline`.
- Single canonical `FitReader` (replaces four duplicate copies).
- YAML-driven configuration (`config/pipeline_config.yaml`) for paths,
  field RA/Dec grids, cut thresholds, and PanSTARRS API settings.
- Interactive menu at `menu.py` that dispatches to every pipeline stage.
- CLI entry points (`scripts/`) for catalog fetch, cross-match,
  slopifier, light-curve calibration, and end-to-end pipeline.
- SLURM submission templates (`slurm/`).
- Pytest suite covering config loading, cuts, photometry, the chi-square
  bug fix, and module-import smoke tests.
- Documentation in `docs/`: pipeline overview, data formats,
  calibration math, module reference.
- 19 keeper notebooks under `notebooks/`, renumbered and outputs
  cleared.
- `pyproject.toml` (PEP 621 packaging), GitHub Actions CI, MIT license,
  CITATION.cff.

### Changed

- `RelativePhoto.py` and `AbsolutePhoto.py` (previously empty / stubbed)
  are now real implementations driving the relative- and absolute-photo
  flag flow.
- The end-to-end orchestrator (formerly `vsp_pipeline/Pipeline.py`)
  actually wires up cross-match -> slopifier -> diagnostics ->
  photo-checks instead of calling stubs.
- The PanSTARRS field fetcher is parameterized on field RA/Dec bounds
  via YAML; replaces three near-duplicate scripts that differed only in
  hard-coded grid extents.

### Fixed

- `lccal` `get_chisq` no longer raises `ValueError` from
  `scipy.stats.chisquare`. The integrated-Gaussian expected counts are
  now rescaled so their sum exactly matches the observed counts before
  the call. See `docs/calibration_math.md` and the comment in
  `vsp.calibration.lccal.reduced_chisq`.

### Removed

- The MPI-AMRVAC `reader.py` (originally in `datmanip/`) was unrelated
  to ROTSE photometry and has been dropped.
- All committed `__pycache__/`, `.ipynb_checkpoints/`, and
  `slurm-*.out` files.
