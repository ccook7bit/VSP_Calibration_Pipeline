"""CLI: end-to-end pipeline driver for one field.

Example::

    python scripts/run_pipeline.py --field sky0001_1a --nights 0824,0825,0901
    python scripts/run_pipeline.py --field sky0001_1a   # all discovered nights
"""
from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401
from vsp.config import setup_logging
from vsp.pipeline.orchestrator import run_pipeline


def main() -> None:
    p = argparse.ArgumentParser(description="End-to-end VSP recalibration pipeline driver.")
    p.add_argument("--field", required=True)
    p.add_argument("--nights", default=None,
                   help="Comma-separated list. Default: all nights in data_dir for this field.")
    p.add_argument("--fetch-catalog", action="store_true",
                   help="Re-fetch the PanSTARRS DR2 reference catalog before running.")
    p.add_argument("--skip-crossmatch", action="store_true")
    p.add_argument("--skip-slopify", action="store_true")
    p.add_argument("--skip-plots", action="store_true")
    p.add_argument("--skip-photo-checks", action="store_true")
    args = p.parse_args()

    setup_logging()
    nights = None
    if args.nights:
        nights = [n.strip() for n in args.nights.split(",") if n.strip()]
    run_pipeline(
        field=args.field,
        nights=nights,
        fetch_catalog=args.fetch_catalog,
        do_crossmatch=not args.skip_crossmatch,
        do_slopify=not args.skip_slopify,
        do_plots=not args.skip_plots,
        do_photo_checks=not args.skip_photo_checks,
    )


if __name__ == "__main__":
    main()
