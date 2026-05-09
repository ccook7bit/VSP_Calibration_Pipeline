# Calibration Math

A short walkthrough of the magnitude / flux / pseudo-bolometric formulas
the pipeline uses, and why the slope/AB-offset fit is a useful
calibration handle.

## AB magnitudes <-> flux

The slopifier uses the standard AB convention. With a magnitude `m` in
the AB system,

```
  flux(m) = 10 ** ((m + 48.6) / -2.5)        [erg s^-1 cm^-2 Hz^-1]
  m(flux) = -2.5 * log10(flux) - 48.6
```

`vsp.calibration.photometry.mag_to_flux` and `flux_to_mag` are vectorized
versions. `vsp.calibration.lccal.mag2flux` is the older scalar
implementation kept for the lccal algorithm specifically; it uses an
AB zero-flux of `3.636` (a consistent simplification within the lccal
algorithm).

## Pseudo-bolometric magnitude

The slopifier compresses the five PanSTARRS grizy magnitudes into a
single broadband "pseudo-bolometric" magnitude that is then compared
against the ROTSE detection magnitude.

### Step 1 - per-band fluxes

For each band `b in {g, r, i, z, y}`,

```
  f_b = 10 ** ((m_b + 48.6) / -2.5)
```

where `m_b` is `{band}MeanPSFMag` from the PanSTARRS DR2 catalog.

### Step 2 - weighted sum

The total flux is a weighted sum of band fluxes:

```
  F_total = (w_g f_g + w_r f_r + w_i f_i + w_z f_z + w_y f_y) / N
```

with the weights and normalization controlled in
`config/pipeline_config.yaml`. The defaults match the original
`Slopifier.py`:

| Band | weight `w_b` |
|------|--------------|
| g    | 0.1212       |
| r    | 0.1463       |
| i    | 0.1435       |
| z    | 0.0980       |
| y    | 0.0393       |

with `N = 0.5483` (the sum of the weights divided by an empirically
chosen factor; see the `bolometric_weights` / `bolometric_norm` block in
the YAML to override).

### Step 3 - back to a magnitude

```
  m_pBolo = -2.5 * log10(F_total / F_AB0)
```

with `F_AB0 = 3631e-23 erg s^-1 cm^-2 Hz^-1` (i.e. the flux density
corresponding to AB = 0).

## The slope / AB-offset fit

For every exposure the slopifier fits

```
  m_pBolo = slope * m_ROTSE + ABoffset
```

with `np.polyfit(..., deg=1)` over all (ROTSE detection, PanSTARRS
match) pairs surviving the cuts.

A "healthy" exposure has:

* `slope` ~ 1 (pseudo-bolometric and ROTSE magnitudes track each other
  one-for-one).
* `ABoffset` modest (a few mag, depending on instrument zero-point).
* `counts` >> a few dozen surviving matches.

Trends in (slope, ABoffset) vs Julian Date / elevation / weather are
the diagnostic signal `matchedmanip/Reading2.py` (now
`diagnostics/plots.py`) was producing.

## Reduced chi-squared (lccal)

`reduced_chisq(observations)` bins `observations` with
`np.histogram(..., bins='auto')`, integrates a Gaussian fit (mean = sample
mean, std = sample std) over each bin to get expected counts, and
returns

```
  chi^2 / dof
```

where `dof = (n_bins - 1) - 2`.

### Why the original got a `ValueError`

The original code wrote:

```python
chisq, pval = st.chisquare(observed, expected, 1)
```

`scipy.stats.chisquare` requires `sum(observed) == sum(expected)` to
within ~1.5e-8 relative tolerance. The integrated Gaussian's tails are
clipped at the outermost histogram bins, so `sum(expected)` is always
slightly **less than** `len(observations)`. Recent SciPy raises:

```
ValueError: For each axis slice, the sum of the observed frequencies must
agree with the sum of the expected frequencies to a relative tolerance of
1.4901161193847656e-08, but the percent differences are: 0.031901391...
```

(see `lccal/lccal.txt` in the original repo for the captured failure).

The fix is to rescale `expected` so its sum matches `sum(observed)`:

```python
expected = expected * (np.sum(observed) / np.sum(expected))
```

This is the documented preprocessing step from the SciPy docs and is
what `vsp.calibration.lccal.reduced_chisq` does now.
