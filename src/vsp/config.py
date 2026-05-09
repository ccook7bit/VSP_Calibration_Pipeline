"""
Configuration loader for the VSP recalibration pipeline.

The pipeline reads its settings from a YAML file (default
``config/pipeline_config.yaml``). This module is the single point that
loads, validates, and exposes that configuration.

Resolution order
----------------
1. Path passed explicitly to :func:`load_config`.
2. ``$VSP_CONFIG`` environment variable.
3. ``config/pipeline_config.yaml`` relative to the repository root.

Example
-------
>>> from vsp.config import get_config
>>> cfg = get_config()
>>> cfg["paths"]["data_dir"]
'/lustre/work/client/users/cdcook/fits_structs'
>>> cfg["fields"]["sky0002_1a"]["ra_min"]
344.66
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

# In-process cache so repeated calls don't re-parse YAML.
_CACHED_CONFIG: Optional[Dict[str, Any]] = None
_CACHED_PATH: Optional[Path] = None

logger = logging.getLogger(__name__)


def _repo_root() -> Path:
    """Return the repository root (vsp_pipeline_v2/)."""
    # This file: <repo>/src/vsp/config.py  -> parents[2] = <repo>
    return Path(__file__).resolve().parents[2]


def _default_config_path() -> Path:
    return _repo_root() / "config" / "pipeline_config.yaml"


def load_config(path: Optional[os.PathLike] = None) -> Dict[str, Any]:
    """
    Load the pipeline configuration from YAML.

    Parameters
    ----------
    path
        Optional explicit path to a YAML config file. If ``None``,
        ``$VSP_CONFIG`` is consulted, then the project default.

    Returns
    -------
    dict
        Parsed configuration mapping.
    """
    global _CACHED_CONFIG, _CACHED_PATH

    if path is None:
        env_path = os.environ.get("VSP_CONFIG")
        path = Path(env_path) if env_path else _default_config_path()
    else:
        path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"Pipeline config not found: {path}")

    with open(path, "r") as f:
        cfg = yaml.safe_load(f)

    _validate(cfg)
    _CACHED_CONFIG = cfg
    _CACHED_PATH = path
    logger.debug("Loaded config from %s", path)
    return cfg


def get_config() -> Dict[str, Any]:
    """Return the cached config, loading the default file if necessary."""
    if _CACHED_CONFIG is None:
        return load_config()
    return _CACHED_CONFIG


def get_path(key: str) -> Path:
    """Look up a key in ``cfg['paths']`` and return it as a :class:`Path`."""
    cfg = get_config()
    try:
        return Path(cfg["paths"][key])
    except KeyError as exc:
        raise KeyError(f"Unknown path key: {key!r} (cfg['paths'] missing it)") from exc


def get_field(field_name: str) -> Dict[str, Any]:
    """Return the field-specific block of the config (RA/Dec bounds, grid size)."""
    cfg = get_config()
    fields = cfg.get("fields", {})
    if field_name not in fields:
        known = ", ".join(sorted(fields)) or "(none)"
        raise KeyError(f"Unknown field {field_name!r}. Known: {known}")
    return fields[field_name]


def setup_logging(cfg: Optional[Dict[str, Any]] = None) -> None:
    """Configure ``logging`` from the ``logging`` block of the config."""
    if cfg is None:
        cfg = get_config()
    log_cfg = cfg.get("logging", {})
    level = log_cfg.get("level", "INFO")
    fmt = log_cfg.get("format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format=fmt)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
_REQUIRED_TOP = {"paths", "fields", "panstarrs", "crossmatch", "slopifier", "lccal"}
_REQUIRED_PATHS = {
    "data_dir",
    "panstarrs_dir",
    "crossmatch_dir",
    "summary_dir",
    "graphics_dir",
    "lightcurves_dir",
}


def _validate(cfg: Dict[str, Any]) -> None:
    """Light-touch validation - shout if obvious things are missing."""
    if not isinstance(cfg, dict):
        raise ValueError("Config root must be a mapping.")
    missing = _REQUIRED_TOP - cfg.keys()
    if missing:
        raise ValueError(f"Config is missing required top-level keys: {sorted(missing)}")
    paths = cfg.get("paths") or {}
    missing_paths = _REQUIRED_PATHS - paths.keys()
    if missing_paths:
        raise ValueError(f"cfg['paths'] missing keys: {sorted(missing_paths)}")
