"""CLI: light-curve calibration for a single target.

Replaces the original ``LccalWrapper.py``. Example::

    python scripts/run_lccal.py \
        --match-dir /lustre/.../datafiles/xtetrans_c \
        --target-ra 185.4975 --target-dec 37.380222 \
        --refstars 5 --radius 5 --max-mean-error 0.06 --chisq 10
"""
from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401
from vsp.calibration.lccal import RefStarCriteria, calibrate
from vsp.config import setup_logging


def main() -> None:
    p = argparse.ArgumentParser(description="Light-curve calibrator for VSP/ROTSE-1/ROTSE-3.")
    p.add_argument("--match-dir", required=True,
                   help="Directory containing the *_match.fit / *_match.dat files for the target.")
    p.add_argument("--target-ra", type=float, required=True)
    p.add_argument("--target-dec", type=float, required=True)
    p.add_argument("--refstars", type=int, default=5)
    p.add_argument("--radius", type=float, default=5.0, help="Reference-star search radius (deg).")
    p.add_argument("--max-mean-error", type=float, default=0.06)
    p.add_argument("--chisq", type=float, default=10.0)
    p.add_argument("--decent-epochs", type=float, default=0.9)
    p.add_argument("--no-avmag", action="store_true")
    p.add_argument("--output-dir", default=None)
    p.add_argument("--no-log", action="store_true")
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()

    setup_logging()
    criteria = RefStarCriteria(
        requested_refstars=args.refstars,
        radius_deg=args.radius,
        max_mean_error=args.max_mean_error,
        max_chisq=args.chisq,
        decent_epochs=args.decent_epochs,
        require_avmag_within_limits=not args.no_avmag,
    )
    result = calibrate(
        match_structures=args.match_dir,
        target_ra=args.target_ra,
        target_dec=args.target_dec,
        criteria=criteria,
        output_dir=args.output_dir,
        verbose=args.verbose,
        write_log=not args.no_log,
    )
    print(f"Calibrated light curve: {result.light_curve_path}")
    if result.log_path:
        print(f"Log: {result.log_path}")


if __name__ == "__main__":
    main()
