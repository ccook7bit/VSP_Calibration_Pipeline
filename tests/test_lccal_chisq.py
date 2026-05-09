"""
Tests for the chi-square bug fix in lccal.

The original ``get_chisq`` raised ``ValueError`` because the integrated
Gaussian's expected counts didn't sum to ``len(observations)``. The new
``reduced_chisq`` rescales ``expected`` first, so it should always
return a finite number for non-degenerate inputs.
"""
import math

import numpy as np
import pytest

from vsp.calibration.lccal import reduced_chisq


def test_chisq_finite_on_normal_sample():
    rng = np.random.default_rng(0)
    observations = rng.normal(loc=15.0, scale=0.05, size=500)
    chisq = reduced_chisq(observations)
    assert math.isfinite(chisq)
    # A clean Gaussian sample should give reduced chi-squared ~ O(1).
    assert 0.0 < chisq < 5.0


def test_chisq_handles_constant_input():
    # All observations equal -> std = 0 -> short-circuit to 0.0
    chisq = reduced_chisq([12.0] * 50)
    assert chisq == 0.0


def test_chisq_with_pvalue():
    rng = np.random.default_rng(1)
    chisq, pval = reduced_chisq(rng.normal(loc=15.0, scale=0.05, size=300), return_pvalue=True)
    assert math.isfinite(chisq)
    assert 0.0 <= pval <= 1.0


def test_chisq_too_few_observations_returns_nan():
    chisq = reduced_chisq([1.0])
    assert math.isnan(chisq)
