"""CLI: run the ROTSE x PanSTARRS cross-match for one field over a list of nights.

Example::

    python scripts/run_crossmatch.py --field sky0001_1a --nights 0824,0825,0901
"""
from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401
from vsp.config import setup_logging
from vsp.crossmatch.rotse_panstarrs import crossmatch_field


def main() -> None:
    p = argparse.ArgumentParser(description="Cross-match ROTSE detections against PanSTARRS DR2.")
    p.add_argument("--field", required=True)
    p.add_argument("--nights", required=True,
                   help="Comma-separated list of night tags, e.g. 0824,0825,0901")
    args = p.parse_args()

    setup_logging()
    nights = [n.strip() for n in args.nights.split(",") if n.strip()]
    crossmatch_field(args.field, nights)


if __name__ == "__main__":
    main()
