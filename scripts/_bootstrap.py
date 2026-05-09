"""Make ``src/`` importable when scripts are run as standalone files.

Each CLI script can ``import _bootstrap`` (or use
``from . import _bootstrap``) to ensure ``vsp`` resolves regardless of
where the script was invoked from.
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
