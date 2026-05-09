#!/bin/bash
#SBATCH --job-name=vsp_crossmatch
#SBATCH --partition=standard-s
#SBATCH --cpus-per-task=64
#SBATCH --mem=256G
#SBATCH --time=24:00:00
#SBATCH --output=slurm-xmatch-%j.out

# Cross-match ROTSE x PanSTARRS for a field+nights.
# Example:  sbatch --export=ALL,FIELD=sky0001_1a,NIGHTS=0824,0825,0901 slurm/crossmatch.sbatch

set -euo pipefail

module purge
module load conda

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

FIELD="${FIELD:-sky0001_1a}"
NIGHTS="${NIGHTS:?Set NIGHTS=0824,0825,...}"

python3 scripts/run_crossmatch.py --field "$FIELD" --nights "$NIGHTS"
