"""Tests for the YAML config loader."""
import pytest

from vsp.config import get_config, get_field, get_path


def test_default_config_loads():
    cfg = get_config()
    assert "paths" in cfg
    assert "fields" in cfg
    assert "panstarrs" in cfg


def test_get_path_returns_pathlike():
    p = get_path("data_dir")
    assert hasattr(p, "joinpath")  # pathlib.Path


def test_get_field_round_trip():
    f = get_field("sky0002_1a")
    assert f["ra_min"] == pytest.approx(344.66)
    assert f["dec_max"] == pytest.approx(22.97)
    assert f["num_ra"] == 25


def test_get_field_unknown_raises():
    with pytest.raises(KeyError):
        get_field("not_a_field_xyz")
