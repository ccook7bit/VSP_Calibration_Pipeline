"""CLI: per-exposure pseudo-bolometric slope/AB-offset fit for one field+night.

Example::

    python scripts/run_slopifier.py --field sky0001_1a --night 0824
"""
from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401
from vsp.calibration.slopifier import slopify_field, slopify_night
from vsp.config import setup_logging


def main() -> None:
    p = argparse.ArgumentParser(description="Run the slopifier per-exposure fit.")
    p.add_argument("--field", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--night", help="Single night tag, e.g. 0824")
    g.add_argument("--nights", help="Comma-separated list, e.g. 0824,0825,0901")
    p.add_argument("--no-fits-append", action="store_true",
                   help="Skip appending the summary HDU to the FITS file.")
    p.add_argument("--no-summary-csv", action="store_true",
                   help="Skip writing the per-night summary CSV.")
    args = p.parse_args()

    setup_logging()
    kwargs = dict(
        append_to_fits=not args.no_fits_append,
        write_summary_csv=not args.no_summary_csv,
    )
    if args.night:
        slopify_night(args.field, args.night, **kwargs)
    else:
        nights = [n.strip() for n in args.nights.split(",") if n.strip()]
        slopify_field(args.field, nights, **kwargs)


if __name__ == "__main__":
    main()
