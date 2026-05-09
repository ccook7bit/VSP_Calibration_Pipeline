"""``python -m vsp`` entry point - delegates to the top-level menu file."""
from __future__ import annotations

import runpy
from pathlib import Path

# The menu lives at the repo root as ``menu.py`` (named that way to avoid
# the package-shadowing collision that ``vsp.py`` would create when the
# repo root is on ``sys.path``).
REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    runpy.run_path(str(REPO_ROOT / "menu.py"), run_name="__main__")


if __name__ == "__main__":
    main()
