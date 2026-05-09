"""
Console-script entry points for the pipeline.

After ``pip install -e .`` (or a regular install), these become
shell commands on your ``$PATH``:

* ``vsp-menu``             - interactive menu
* ``vsp-fetch-panstarrs``  - download per-field PanSTARRS DR2 reference catalog
* ``vsp-crossmatch``       - ROTSE x PanSTARRS cross-match
* ``vsp-slopifier``        - per-exposure slope/AB-offset fit
* ``vsp-lccal``            - light-curve calibration for one target
* ``vsp-pipeline``         - end-to-end driver

Each delegates to the underlying ``scripts/*.py`` CLI.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

# Resolve the path to the in-tree scripts/ directory once.
# Layout: src/vsp/cli.py  -> parents[2] = repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO_ROOT / "scripts"


def _run_script(name: str) -> None:
    """Execute ``scripts/<name>.py`` as if it were called from the CLI."""
    target = _SCRIPTS / f"{name}.py"
    if not target.is_file():
        sys.stderr.write(f"vsp.cli: cannot find {target}\n")
        raise SystemExit(2)
    # Make sure ``scripts/`` is on sys.path so ``import _bootstrap`` works.
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    runpy.run_path(str(target), run_name="__main__")


def fetch_panstarrs_main() -> None:
    _run_script("fetch_panstarrs")


def crossmatch_main() -> None:
    _run_script("run_crossmatch")


def slopifier_main() -> None:
    _run_script("run_slopifier")


def lccal_main() -> None:
    _run_script("run_lccal")


def pipeline_main() -> None:
    _run_script("run_pipeline")


def menu_main() -> None:
    """Run the interactive menu (``menu.py`` at the repo root)."""
    target = _REPO_ROOT / "menu.py"
    if not target.is_file():
        sys.stderr.write(f"vsp.cli: cannot find {target}\n")
        raise SystemExit(2)
    runpy.run_path(str(target), run_name="__main__")
