#!/bin/bash
#SBATCH --job-name=vsp_lccal
#SBATCH --partition=standard-s
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=24:00:00
#SBATCH --output=slurm-lccal-%j.out

# Light-curve calibration for a single target.
# Example:
#   sbatch --export=ALL,MATCH_DIR=/users/cdcook/VSP/datafiles/xtetrans_c,RA=185.4975,DEC=37.380222 \
#       slurm/lccal.sbatch

set -euo pipefail

module purge
module load conda

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

MATCH_DIR="${MATCH_DIR:?Set MATCH_DIR=/path/to/datafiles/...}"
RA="${RA:?Set RA=...}"
DEC="${DEC:?Set DEC=...}"
REFSTARS="${REFSTARS:-5}"
RADIUS="${RADIUS:-5}"

python3 scripts/run_lccal.py \
    --match-dir "$MATCH_DIR" \
    --target-ra "$RA" --target-dec "$DEC" \
    --refstars "$REFSTARS" --radius "$RADIUS"
