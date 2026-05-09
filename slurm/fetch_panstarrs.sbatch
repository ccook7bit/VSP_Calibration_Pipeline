#!/bin/bash
#SBATCH --job-name=panstarrs_fetch
#SBATCH --partition=standard-s
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=slurm-fetch-%j.out

# Pull the per-field PanSTARRS DR2 catalog. Override FIELD on the command
# line, e.g.:  sbatch --export=ALL,FIELD=sky0002_1c slurm/fetch_panstarrs.sbatch

set -euo pipefail

module purge
module load conda

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

FIELD="${FIELD:-sky0001_1a}"
echo "Fetching PanSTARRS catalog for field=$FIELD"

python3 scripts/fetch_panstarrs.py --field "$FIELD"
