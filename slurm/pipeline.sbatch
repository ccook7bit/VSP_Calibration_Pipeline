#!/bin/bash
#SBATCH --job-name=vsp_pipeline
#SBATCH --partition=standard-s
#SBATCH --cpus-per-task=64
#SBATCH --mem=256G
#SBATCH --time=24:00:00
#SBATCH --output=slurm-pipeline-%j.out

# End-to-end pipeline driver.
# Example:  sbatch --export=ALL,FIELD=sky0001_1a slurm/pipeline.sbatch

set -euo pipefail

module purge
module load conda

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

FIELD="${FIELD:-sky0001_1a}"
NIGHTS="${NIGHTS:-}"   # leave empty to auto-discover all nights for this field

if [ -n "$NIGHTS" ]; then
    python3 scripts/run_pipeline.py --field "$FIELD" --nights "$NIGHTS"
else
    python3 scripts/run_pipeline.py --field "$FIELD"
fi
