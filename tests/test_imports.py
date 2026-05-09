"""Smoke test - every package and module imports cleanly."""
import importlib

import pytest

MODULES = [
    "vsp",
    "vsp.config",
    "vsp.io",
    "vsp.io.fits_reader",
    "vsp.io.match_io",
    "vsp.catalog",
    "vsp.catalog.panstarrs_api",
    "vsp.catalog.fetch_field",
    "vsp.crossmatch",
    "vsp.crossmatch.rotse_panstarrs",
    "vsp.calibration",
    "vsp.calibration.cuts",
    "vsp.calibration.photometry",
    "vsp.calibration.slopifier",
    "vsp.calibration.lccal",
    "vsp.diagnostics",
    "vsp.diagnostics.limiting_magnitude",
    "vsp.diagnostics.plots",
    "vsp.pipeline",
    "vsp.pipeline.absolute_photo",
    "vsp.pipeline.relative_photo",
    "vsp.pipeline.orchestrator",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    mod = importlib.import_module(name)
    assert mod is not None
