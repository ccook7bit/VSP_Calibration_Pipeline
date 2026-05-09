#!/bin/bash
#SBATCH --job-name=vsp_slopifier
#SBATCH --partition=standard-s
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=slurm-slopifier-%j.out

# Per-exposure slope/AB-offset fit for a field+nights.
# Example:  sbatch --export=ALL,FIELD=sky0001_1a,NIGHTS=0824,0825 slurm/slopifier.sbatch

set -euo pipefail

module purge
module load conda

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

FIELD="${FIELD:-sky0001_1a}"
NIGHTS="${NIGHTS:?Set NIGHTS=0824,0825,...}"

python3 scripts/run_slopifier.py --field "$FIELD" --nights "$NIGHTS"
