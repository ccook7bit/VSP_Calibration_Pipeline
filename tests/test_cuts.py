"""Tests for the photometric quality cuts."""
import pandas as pd
import pytest

from vsp.calibration import cuts


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "RA": [10.0, 10.1, 10.2, 10.3],
        "Dec": [20.0, 20.1, 20.2, 20.3],
        "Mag": [10.0, 14.0, 26.0, 4.0],
        "Flags": [0, 1, 0, 2],
        "gMeanPSFMag":  [15.0,   16.0, -999.0, 17.0],
        "gMeanKronMag": [15.05,  16.10, 18.0,  17.5],
        "rMeanPSFMag":  [14.7,   15.7, 19.0,  16.5],
        "rMeanKronMag": [14.75,  15.80, 19.0,  16.55],
        "iMeanPSFMag":  [14.4,   15.4, 19.5,  16.2],
        "iMeanKronMag": [14.45,  15.45, 19.5,  16.25],
        "zMeanPSFMag":  [14.0,   15.0, 19.7,  15.9],
        "zMeanKronMag": [14.05,  15.05, 19.7,  15.95],
        "yMeanPSFMag":  [13.7,   14.7, 19.9,  15.6],
        "yMeanKronMag": [13.75,  14.75, 19.9,  15.65],
    })


def test_magnitude_window_drops_outside_range(sample_df):
    out = cuts.magnitude_window(sample_df, mag_min=5.0, mag_max=25.0)
    # rows with Mag=26.0 (>25) and Mag=4.0 (<5) should drop
    assert len(out) == 2


def test_drop_panstarrs_sentinels_drops_minus_999(sample_df):
    out = cuts.drop_panstarrs_sentinels(sample_df)
    # row 2 has gMeanPSFMag = -999
    assert -999 not in out["gMeanPSFMag"].values
    assert len(out) == 3


def test_kron_cut_keeps_close_psf_kron(sample_df):
    df = cuts.drop_panstarrs_sentinels(sample_df)
    out, kron, psf, name = cuts.kron_cut(df, band="g", max_dist=0.2)
    # all surviving rows have |PSF - Kron| < 0.2
    assert ((out[psf] - out[kron]).abs() < 0.2).all()
    assert kron == "gMeanKronMag" and psf == "gMeanPSFMag"


def test_color_cut_inserts_color_columns(sample_df):
    df = cuts.drop_panstarrs_sentinels(sample_df)
    out, *_ = cuts.color_cut(df, pair_1="gr", pair_2="ri")
    assert "color1" in out.columns
    assert "color2" in out.columns


def test_bitflag_cut(sample_df):
    out = cuts.bitflag_cut(sample_df, value=0)
    assert (out["Flags"] == 0).all()
    assert len(out) == 2
