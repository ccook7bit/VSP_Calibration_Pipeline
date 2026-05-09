#!/usr/bin/env python3
"""
VSP Recalibration Pipeline - top-level interactive menu.

Run this from anywhere with::

    python menu.py

(Equivalently, ``python -m vsp`` after putting ``src/`` on PYTHONPATH.)

It is the friendliest entry point into the pipeline:

* Shows a description of every stage (catalog fetch, cross-match,
  slopifier, diagnostics, lccal, end-to-end orchestrator).
* Lets you launch any stage interactively, prompting for the field /
  nights / target coordinates as needed.
* Surfaces the active config and which fields/paths are configured.

For non-interactive use, the same stages are exposed as
``python -m scripts.<name>`` CLIs in the ``scripts/`` directory.
"""
from __future__ import annotations

import argparse
import importlib
import logging
import os
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

# Make `vsp` importable.
REPO_ROOT = Path(__file__).resolve().parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vsp.config import get_config, load_config, setup_logging  # noqa: E402

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------------
BANNER = r"""
+---------------------------------------------------------------+
|              VSP / ROTSE Recalibration Pipeline               |
|                            v2.0                               |
+---------------------------------------------------------------+
"""


PIPELINE_OVERVIEW = textwrap.dedent("""
    Pipeline stages
    ---------------
      1. catalog.fetch_field      Pull PanSTARRS DR2 reference catalog
                                  for a survey field (writes one CSV).
      2. crossmatch               Match ROTSE detections in each
                                  *_match.fit/.dat against the PanSTARRS
                                  CSV (KDTree + 5 arcsec) and emit a
                                  per-exposure merged CSV.
      3. calibration.slopifier    For each exposure, fit Mag vs
                                  pseudo-bolometric mag to get
                                  (slope, ABoffset, counts) per
                                  exposure. Append HDU to the FITS file
                                  and write a per-night summary CSV.
      4. diagnostics.plots        Render diagnostic PNGs of slope /
                                  AB-offset / counts / limiting-mag vs
                                  Julian Date, weather, elevation.
      5. calibration.lccal        Light-curve calibration for a single
                                  target: refstar selection, per-epoch
                                  corrections, optional unconex filter.
      6. pipeline.orchestrator    End-to-end driver chaining 2-4 (and
                                  optionally 1) over a field+nights.

    Each stage is a Python module under ``src/vsp/`` and a CLI under
    ``scripts/``. The interactive menu just dispatches to those.
""")


def banner():
    print(BANNER)


def section(title: str):
    print()
    print(f"--- {title} ".ljust(63, "-"))


# ---------------------------------------------------------------------------
# Menu actions
# ---------------------------------------------------------------------------
@dataclass
class MenuItem:
    key: str
    title: str
    description: str
    handler: Callable[[], None]


def _ask(prompt: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"  {prompt}{suffix}: ").strip()
    return val if val else (default or "")


def _ask_required(prompt: str) -> str:
    while True:
        val = input(f"  {prompt}: ").strip()
        if val:
            return val
        print("    (required)")


def _ask_float(prompt: str, default: Optional[float] = None) -> float:
    while True:
        try:
            return float(_ask(prompt, str(default) if default is not None else None))
        except ValueError:
            print("    (please enter a number)")


def _ask_int(prompt: str, default: Optional[int] = None) -> int:
    while True:
        try:
            return int(_ask(prompt, str(default) if default is not None else None))
        except ValueError:
            print("    (please enter an integer)")


def show_overview():
    section("Pipeline overview")
    print(PIPELINE_OVERVIEW)


def show_config():
    section("Loaded configuration")
    cfg = get_config()
    print("Paths:")
    for k, v in cfg["paths"].items():
        print(f"  {k:18s} -> {v}")
    print()
    print("Fields:")
    for name, body in cfg.get("fields", {}).items():
        print(f"  {name:14s} RA=[{body['ra_min']:>7.2f}, {body['ra_max']:>7.2f}]"
              f"  Dec=[{body['dec_min']:>6.2f}, {body['dec_max']:>6.2f}]"
              f"  grid={body['num_ra']}x{body['num_dec']}")
    print()
    print(f"PanSTARRS release/table: {cfg['panstarrs']['release']}/{cfg['panstarrs']['table']}")
    print(f"Cross-match radius:      {cfg['crossmatch']['match_radius_arcsec']} arcsec")
    print(f"Slopifier mag window:    [{cfg['slopifier']['mag_min']}, {cfg['slopifier']['mag_max']}]")


def show_modules():
    section("Module reference")
    print(textwrap.dedent("""
        src/vsp/
          config.py                -- YAML loader + path/field accessors
          io/fits_reader.py        -- canonical ROTSE-1/3 match reader
          io/match_io.py           -- filename conventions
          catalog/panstarrs_api.py -- DR1/DR2 MAST API client
          catalog/fetch_field.py   -- per-field grid fetcher
          crossmatch/rotse_panstarrs.py -- KDTree match + per-exposure CSV
          calibration/cuts.py      -- KronCut, BitFlagCut, ColorCut
          calibration/photometry.py -- mag/flux conversions, pseudo-bolometric
          calibration/slopifier.py -- per-exposure (slope, ABoffset, counts)
          calibration/lccal.py     -- light-curve calibration for one target
          diagnostics/plots.py     -- per-night diagnostic PNGs
          diagnostics/limiting_magnitude.py
          pipeline/absolute_photo.py
          pipeline/relative_photo.py
          pipeline/orchestrator.py -- end-to-end runner
    """))


# --- Stage launchers --------------------------------------------------------
def _list_fields():
    return list(get_config().get("fields", {}).keys())


def launch_fetch():
    section("Fetch PanSTARRS reference catalog")
    field = _ask_required(f"Field name (one of: {', '.join(_list_fields())})")
    from vsp.catalog.fetch_field import fetch_field
    out = fetch_field(field)
    print(f"  -> wrote {out}")


def launch_crossmatch():
    section("Cross-match ROTSE x PanSTARRS")
    field = _ask_required("Field name")
    nights = _ask_required("Nights (comma-separated, e.g. 0824,0825,0901)")
    from vsp.crossmatch.rotse_panstarrs import crossmatch_field
    crossmatch_field(field, [n.strip() for n in nights.split(",") if n.strip()])


def launch_slopifier():
    section("Run slopifier")
    field = _ask_required("Field name")
    nights = _ask_required("Nights (comma-separated)")
    from vsp.calibration.slopifier import slopify_field
    slopify_field(field, [n.strip() for n in nights.split(",") if n.strip()])


def launch_diagnostics():
    section("Render diagnostic plots")
    field = _ask_required("Field name")
    nights = _ask_required("Nights (comma-separated)")
    from vsp.diagnostics.plots import plot_night_diagnostics
    for n in [x.strip() for x in nights.split(",") if x.strip()]:
        plot_night_diagnostics(field, n)


def launch_lccal():
    section("Light-curve calibration")
    match_dir = _ask_required("Match-structures directory")
    ra = _ask_float("Target RA (deg)")
    dec = _ask_float("Target Dec (deg)")
    refstars = _ask_int("Number of refstars", 5)
    radius = _ask_float("Search radius (deg)", 5.0)
    from vsp.calibration.lccal import RefStarCriteria, calibrate
    criteria = RefStarCriteria.from_config()
    criteria.requested_refstars = refstars
    criteria.radius_deg = radius
    res = calibrate(match_structures=match_dir, target_ra=ra, target_dec=dec, criteria=criteria)
    print(f"  -> {res.light_curve_path}")


def launch_pipeline():
    section("End-to-end pipeline")
    field = _ask_required("Field name")
    nights = _ask("Nights (comma-separated; leave blank to auto-discover)")
    fetch = _ask("Fetch PanSTARRS catalog first? (y/N)", "n").lower().startswith("y")
    from vsp.pipeline.orchestrator import run_pipeline
    nights_list = [n.strip() for n in nights.split(",") if n.strip()] if nights else None
    run_pipeline(field, nights=nights_list, fetch_catalog=fetch)


def open_docs():
    section("Documentation")
    docs_dir = REPO_ROOT / "docs"
    if not docs_dir.is_dir():
        print(f"  (no docs/ directory at {docs_dir})")
        return
    files = sorted(docs_dir.glob("*.md"))
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f.name}")
    choice = _ask("Open which? (number, or blank to cancel)")
    if not choice:
        return
    try:
        f = files[int(choice) - 1]
    except (ValueError, IndexError):
        print("  (invalid choice)")
        return
    print()
    print(f.read_text())


# ---------------------------------------------------------------------------
# Menu loop
# ---------------------------------------------------------------------------
MENU: list[MenuItem] = [
    MenuItem("1", "Pipeline overview", "Show a description of every stage", show_overview),
    MenuItem("2", "Show config",        "Print the loaded YAML config",      show_config),
    MenuItem("3", "Module reference",   "Map of source files",               show_modules),
    MenuItem("4", "Fetch PanSTARRS catalog", "(catalog.fetch_field)",        launch_fetch),
    MenuItem("5", "Run cross-match",    "(crossmatch.rotse_panstarrs)",      launch_crossmatch),
    MenuItem("6", "Run slopifier",      "(calibration.slopifier)",           launch_slopifier),
    MenuItem("7", "Diagnostic plots",   "(diagnostics.plots)",               launch_diagnostics),
    MenuItem("8", "Light-curve calibration", "(calibration.lccal)",          launch_lccal),
    MenuItem("9", "End-to-end pipeline", "(pipeline.orchestrator)",          launch_pipeline),
    MenuItem("d", "Open docs",          "Browse markdown in docs/",          open_docs),
    MenuItem("q", "Quit",               "Exit the menu",                     lambda: sys.exit(0)),
]


def menu_loop():
    while True:
        section("Main menu")
        for item in MENU:
            print(f"  {item.key}) {item.title:30s} {item.description}")
        choice = input("\nChoose: ").strip().lower()
        item = next((m for m in MENU if m.key == choice), None)
        if item is None:
            print("  (no such option)")
            continue
        try:
            item.handler()
        except KeyboardInterrupt:
            print("\n  (cancelled)")
        except Exception as exc:  # surface errors but stay alive
            logger.exception("Stage failed: %s", exc)
            print(f"  ERROR: {exc}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default=None, help="Override config YAML path.")
    p.add_argument("--no-banner", action="store_true")
    args = p.parse_args()

    if args.config:
        load_config(args.config)
    setup_logging()

    if not args.no_banner:
        banner()
    show_overview()
    menu_loop()


if __name__ == "__main__":
    main()
