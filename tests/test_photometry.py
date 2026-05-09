"""Tests for AB flux/mag and pseudo-bolometric helpers."""
import numpy as np
import pandas as pd
import pytest

from vsp.calibration import photometry


def test_mag_flux_round_trip():
    mags = np.array([10.0, 12.5, 18.3])
    flux = photometry.mag_to_flux(mags)
    back = photometry.flux_to_mag(flux)
    assert np.allclose(back, mags, atol=1e-9)


def test_pseudo_bolometric_columns_present():
    df = pd.DataFrame({
        "gMeanPSFMag": [15.0, 16.0],
        "rMeanPSFMag": [14.7, 15.7],
        "iMeanPSFMag": [14.4, 15.4],
        "zMeanPSFMag": [14.0, 15.0],
        "yMeanPSFMag": [13.7, 14.7],
    })
    df = photometry.add_band_fluxes(df)
    df = photometry.pseudo_bolometric_magnitude(
        df,
        weights={"g": 0.1212, "r": 0.1463, "i": 0.1435, "z": 0.098, "y": 0.0393},
        norm=0.5483,
        flux_columns=True,
    )
    assert "pseudoBoloMag" in df.columns
    assert "totalFlux" in df.columns
    # brighter PSF mags -> brighter (smaller) pseudo-bolometric mag
    assert df.loc[0, "pseudoBoloMag"] < df.loc[1, "pseudoBoloMag"]


def test_linear_fit_recovers_known_slope():
    rng = np.random.default_rng(42)
    x = np.linspace(0, 10, 20)
    y = 0.7 * x + 1.5 + rng.normal(scale=1e-9, size=x.shape)
    slope, intercept, _ = photometry.linear_fit(x, y)
    assert slope == pytest.approx(0.7, rel=1e-3)
    assert intercept == pytest.approx(1.5, rel=1e-3)
