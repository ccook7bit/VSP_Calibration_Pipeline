# Module Reference

Quick API map of the package. For deeper detail, read the docstrings on
each function/class - they are the source of truth.

## Top-level

```
menu.py            interactive menu (also reachable via `python -m vsp`)
scripts/           CLI wrappers (one per stage)
slurm/             SBATCH submission templates
config/            YAML configuration
src/vsp/           package source
notebooks/         interactive exploration
tests/             pytest unit tests
docs/              this directory
```

## Package layout

### `vsp.config`

| Symbol             | Purpose                                                     |
| ------------------ | ----------------------------------------------------------- |
| `load_config(path)`| Parse YAML, validate, cache, return the dict.               |
| `get_config()`     | Cached dict (calls `load_config()` on first use).           |
| `get_path(key)`    | Convenience for `cfg['paths'][key]` -> `Path`.              |
| `get_field(name)`  | Returns the per-field block (RA/Dec bounds, grid size).     |
| `setup_logging()`  | `logging.basicConfig` from the `logging:` block.            |

### `vsp.io`

| Module       | Symbols                                                        |
| ------------ | -------------------------------------------------------------- |
| `fits_reader`| `FitReader`, `read_data_file`, `read_fits_file`, `read_match_file`, `get_data` |
| `match_io`   | `match_file`, `panstarrs_csv`, `crossmatch_csv`, `coords_csv`, `summary_csv`, `lightcurve_csv`, `list_nights_for_field` |

### `vsp.catalog`

| Module           | Symbols                                                        |
| ---------------- | -------------------------------------------------------------- |
| `panstarrs_api`  | `ps1cone`, `ps1search`, `ps1metadata`, `mastQuery`, `resolve`, `checklegal` |
| `fetch_field`    | `fetch_field(field, output=None, verbose=True) -> Path`        |

### `vsp.crossmatch`

| Module             | Symbols                                                        |
| ------------------ | -------------------------------------------------------------- |
| `rotse_panstarrs`  | `crossmatch_night(field, night) -> List[Path]`                 |
|                    | `crossmatch_field(field, nights) -> dict`                      |

### `vsp.calibration`

| Module       | Symbols                                                                             |
| ------------ | ----------------------------------------------------------------------------------- |
| `cuts`       | `kron_cut`, `bitflag_cut`, `color_cut`, `drop_panstarrs_sentinels`, `magnitude_window`, `flag_is_true`, `BAND_COLUMNS`, `COLOR_PAIRS` |
| `photometry` | `mag_to_flux`, `flux_to_mag`, `add_band_fluxes`, `pseudo_bolometric_magnitude`, `linear_fit`, `BANDS` |
| `slopifier`  | `slopify_exposure`, `slopify_night`, `slopify_field`, `ExposureFit`, `NightSummary` |
| `lccal`      | `calibrate`, `RefStarCriteria`, `LccalResult`, `reduced_chisq`, `find_target`, `find_refstars`, `closest_refs`, `compute_corrections`, `apply_corrections` |

### `vsp.diagnostics`

| Module               | Symbols                                                  |
| -------------------- | -------------------------------------------------------- |
| `limiting_magnitude` | `find_limiting_magnitude`, `find_limiting_magnitude_for_file` |
| `plots`              | `plot_night_diagnostics`                                 |

### `vsp.pipeline`

| Module             | Symbols                                                  |
| ------------------ | -------------------------------------------------------- |
| `absolute_photo`   | `check_and_correct(df, fit) -> (df, AbsoluteFlags)`      |
| `relative_photo`   | `check_and_correct(df) -> (df, RelativeFlags)`           |
| `orchestrator`     | `run_pipeline(field, nights=None, ...) -> PipelineRun`   |

## Common entry points

### From a Python REPL / notebook

```python
from vsp.config import setup_logging
from vsp.crossmatch import crossmatch_night
from vsp.calibration import slopify_night
from vsp.diagnostics import plot_night_diagnostics

setup_logging()
crossmatch_night("sky0001_1a", "0824")
summary = slopify_night("sky0001_1a", "0824")
plot_night_diagnostics("sky0001_1a", "0824")
```

### Command line

```
python scripts/fetch_panstarrs.py --field sky0001_1a
python scripts/run_crossmatch.py  --field sky0001_1a --nights 0824,0825
python scripts/run_slopifier.py   --field sky0001_1a --nights 0824,0825
python scripts/run_lccal.py       --match-dir <dir> --target-ra ... --target-dec ...
python scripts/run_pipeline.py    --field sky0001_1a   # end-to-end
```

### Interactive menu

```
python menu.py
```
