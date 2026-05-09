<<<<<<< HEAD
This directory houses the pipeline for calibration of the VSP/ROTSE-1/ROTSE-III datasets
=======
# VSP Recalibration Pipeline

[![tests](https://github.com/ccook7bit/VSP_Calibration_Pipeline/actions/workflows/tests.yml/badge.svg)](https://github.com/ccook7bit/VSP_Calibration_Pipeline/actions/workflows/tests.yml)
[![python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![license](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Photometric recalibration pipeline for the VSP / ROTSE-1 / ROTSE-III variable-star surveys.

This is the consolidated, parameterized version of the codebase that previously lived in nine
separate zip archives (`autopsfinder`, `datmanip`, `lccal`, `matchedmanip`, `panstarrs_api`,
`pyfiles`, `slopifier`, `updatedpanapi`, `vsp_pipeline`).

## Installation

Requires Python 3.10 or newer.

```bash
# Clone and editable-install
git clone https://github.com/ccook7bit/VSP_Calibration_Pipeline
cd VSP_Calibration_Pipeline
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
```

For development (tests, linters, pre-commit hooks):

```bash
pip install -e ".[dev]"
pre-commit install
```

For the interactive notebooks:

```bash
pip install -e ".[notebooks]"
```

After installation, the CLI is available as console scripts:

```bash
vsp-menu                            # interactive menu
vsp-fetch-panstarrs --field sky0001_1a
vsp-crossmatch      --field sky0001_1a --nights 0824,0825,0901
vsp-slopifier       --field sky0001_1a --night 0824
vsp-lccal           --match-dir <path> --target-ra 185.4975 --target-dec 37.380222
vsp-pipeline        --field sky0001_1a
```

## Quick start

```bash
# 1. Edit config/pipeline_config.yaml so the `paths:` block points at your data.
# 2. Either use the menu:
vsp-menu

# 3. ...or run individual stages from the command line:
vsp-fetch-panstarrs --field sky0001_1a
vsp-crossmatch      --field sky0001_1a --nights 0824,0825,0901
vsp-slopifier       --field sky0001_1a --nights 0824,0825,0901
vsp-pipeline        --field sky0001_1a   # end-to-end
```

All paths and field bounds live in [`config/pipeline_config.yaml`](config/pipeline_config.yaml).
The ROTSE data directory (the `*_match.fit` / `*_match.dat` files) sits **outside** this
repository and is referenced by `paths.data_dir` in the config.

## Pipeline overview

```
+----------------------+    +----------------------+    +----------------------+
| catalog.fetch_field  | -> | crossmatch           | -> | calibration.slopifier|
| (PanSTARRS DR2 API)  |    | (ROTSE x PanSTARRS,  |    | (per-exposure        |
|                      |    |  KDTree, 5 arcsec)   |    |  pseudo-bolometric   |
|                      |    |                      |    |  slope/AB-offset fit)|
+----------------------+    +----------------------+    +----------------------+
                                                                   |
                                       +---------------------------+
                                       v
                       +------------------------------+
                       | diagnostics.plots            |
                       | (Slope/ABoff/Counts vs JD,   |
                       |  weather, elevation)         |
                       +------------------------------+
                                       |
                                       v
                       +------------------------------+
                       | calibration.lccal            |
                       | (target light curve from     |
                       |  reference stars + cuts)     |
                       +------------------------------+
```

The end-to-end driver in `pipeline.orchestrator` reads a match structure, runs absolute
and relative photometry checks (`pipeline.absolute_photo`, `pipeline.relative_photo`),
merges the results, and writes the corrected output.

See [`docs/pipeline_overview.md`](docs/pipeline_overview.md) for the full architecture
write-up and [`docs/module_reference.md`](docs/module_reference.md) for per-module API
docs.

## Directory layout

```
VSP_Calibration_Pipeline/
├── menu.py                    # interactive menu (also reachable via `vsp-menu`)
├── config/pipeline_config.yaml
├── src/vsp/
│   ├── config.py              # YAML loader
│   ├── cli.py                 # console-script entry points
│   ├── io/                    # FITS / .dat readers (single canonical FitReader)
│   ├── catalog/               # PanSTARRS DR2 API client + field fetcher
│   ├── crossmatch/            # ROTSE x PanSTARRS KDTree match
│   ├── calibration/           # cuts, photometry, slopifier, lccal
│   ├── diagnostics/           # limiting magnitude + diagnostic plots
│   └── pipeline/              # orchestrator + abs/rel photometry checks
├── scripts/                   # thin CLI wrappers (mirror the console scripts)
├── slurm/                     # SBATCH submission templates
├── notebooks/                 # interactive exploration (outputs stripped)
├── tests/                     # pytest unit tests
└── docs/                      # architecture, data formats, calibration math
```

## Configuration

Override paths or thresholds without editing the default config:

```bash
# Inline override
VSP_CONFIG=/path/to/my_local.yaml vsp-pipeline --field sky0001_1a

# Or pass --config to menu.py
python menu.py --config /path/to/my_local.yaml
```

## Running on a SLURM cluster

The `slurm/` directory contains submission templates. Each accepts environment overrides:

```bash
sbatch --export=ALL,FIELD=sky0001_1a,NIGHTS=0824,0825 slurm/crossmatch.sbatch
sbatch --export=ALL,FIELD=sky0001_1a               slurm/pipeline.sbatch
```

## Testing

```bash
pytest                              # full suite
pytest tests/test_cuts.py -k kron   # one test
pytest --cov=vsp                    # with coverage report
```

The test suite covers config loading, photometric cuts, the
pseudo-bolometric magnitude derivation, the lccal chi-square fix, and
import-time smoke tests for every module.

## How to cite

If you use this pipeline in published work, please cite it. GitHub will
render a "Cite this repository" button using the metadata in
[`CITATION.cff`](CITATION.cff). Or use the BibTeX-friendly form:

```
Cook, C. (2026). VSP Recalibration Pipeline (Version 2.0.0)
[Computer software]. https://github.com/ccook7bit/VSP_Calibration_Pipeline
```

## Contributing

Issue reports and pull requests are welcome.
See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the development workflow.

## License

MIT - see [`LICENSE`](LICENSE).

## Source archive provenance

| New module                          | Original source                                                       |
| ----------------------------------- | --------------------------------------------------------------------- |
| `io/fits_reader.py`                 | `FitReader.py` (deduped from autopsfinder, matchedmanip, updatedpanapi, pyfiles) |
| `catalog/panstarrs_api.py`          | `panstarrs_api/DR2API_queries.py`, `updatedpanapi/DR2API_que.py`      |
| `catalog/fetch_field.py`            | `panstarrs_api/DR2API_queries{,2,3}.py` (deduped, parameterized)      |
| `crossmatch/rotse_panstarrs.py`     | `updatedpanapi/PSFinderCanon.py` (with RA-wrap fix)                   |
| `calibration/cuts.py`               | helper block from `slopifier/Slopifier.py`                            |
| `calibration/photometry.py`         | `pyfiles/VSPFunctions.py` + slopifier flux block                      |
| `calibration/slopifier.py`          | `slopifier/Slopifier.py` + `BigSlopifier.ipynb` per-night loop        |
| `calibration/lccal.py`              | `lccal/lccal.py` (with `chisquare` normalization fix)                 |
| `diagnostics/plots.py`              | `matchedmanip/Reading2.py`                                            |
| `pipeline/orchestrator.py`          | `vsp_pipeline/Pipeline.py` (real implementation)                      |
| `pipeline/relative_photo.py`        | `vsp_pipeline/RelativePhoto.py` (real implementation)                 |
| `pipeline/absolute_photo.py`        | `vsp_pipeline/AbsolutePhoto.py` (was empty)                           |
>>>>>>> 44c20ce (Initial release v2.0.0)
