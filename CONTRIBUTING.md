# Contributing

Thanks for your interest in the VSP Recalibration Pipeline. This is
primarily a research codebase, but external contributions are welcome.

## Reporting bugs / requesting features

Open an issue on GitHub. For bugs, please include:

* OS + Python version (`python --version`)
* `pip freeze` output
* Minimal command to reproduce
* Full traceback

## Development setup

```bash
git clone https://github.com/ccook7bit/VSP_Calibration_Pipeline
cd VSP_Calibration_Pipeline
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"            # editable install + pytest, ruff, black, ...
pre-commit install                  # auto-runs ruff/black/nbstripout on commit
```

## Running the test suite

```bash
pytest                              # all tests
pytest tests/test_cuts.py -k kron   # one test
pytest --cov=vsp                    # with coverage
```

## Code style

* `black` for formatting (line length 100).
* `ruff` for linting (config in `pyproject.toml`).
* Type hints encouraged but not required.
* Docstrings: short summary line, then a more detailed description if
  useful. NumPy style for parameter / return blocks.

## Notebooks

Notebook outputs **must not** be committed. `nbstripout` (installed via
`pre-commit`) clears them automatically. If you skipped pre-commit, run
manually before committing:

```bash
nbstripout notebooks/*.ipynb
```

## Pull-request checklist

- [ ] Tests added or updated for the change
- [ ] `pytest` passes locally
- [ ] `ruff check` and `black --check` are clean
- [ ] Notebooks have no committed outputs
- [ ] Documentation in `docs/` updated if behaviour changed
- [ ] `CHANGELOG.md` "Unreleased" section updated

## What not to commit

* FITS / `.dat` / `.cobj` data files (use the configured `data_dir`).
* PanSTARRS catalog CSVs (regenerate with `vsp-fetch-panstarrs`).
* Per-exposure cross-match CSVs (regenerate with `vsp-crossmatch`).
* SLURM `.out` logs.
* Per-user paths in code: put them in `config/pipeline_config.yaml` or
  use `VSP_CONFIG=<path>` for local overrides.
