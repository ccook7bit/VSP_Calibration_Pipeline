"""CLI: fetch the per-field PanSTARRS DR2 reference catalog.

Example::

    python scripts/fetch_panstarrs.py --field sky0001_1a
"""
from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401
from vsp.catalog.fetch_field import fetch_field
from vsp.config import setup_logging


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch PanSTARRS DR2 reference catalog for a field.")
    p.add_argument("--field", required=True, help="Field name (must be defined in config).")
    p.add_argument("--output", default=None, help="Optional output CSV path override.")
    p.add_argument("--quiet", action="store_true", help="Suppress per-cone log lines.")
    args = p.parse_args()

    setup_logging()
    fetch_field(args.field, output=args.output, verbose=not args.quiet)


if __name__ == "__main__":
    main()
