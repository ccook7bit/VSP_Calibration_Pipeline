# Notebooks

Interactive notebooks preserved from the original archives, renumbered
for easier navigation. The numeric prefix is sort order, not a
recommended workflow order.

| #   | File                              | Original location                              | What it shows                                     |
| --- | --------------------------------- | ---------------------------------------------- | ------------------------------------------------- |
| 01  | `01_slopifier_interactive.ipynb`  | `slopifier/SlopifierNotebook.ipynb`            | Single-night slopifier - per-exposure fit walk-through |
| 02  | `02_slopifier_per_night.ipynb`    | `slopifier/BigSlopifier.ipynb`                 | Per-night looped slopifier with `find_limiting_magnitude` |
| 03  | `03_subimager_flag_decoder.ipynb` | `slopifier/SubImager.ipynb`                    | Decoding `objInfoFlag` / `qualityFlag` bitmasks   |
| 04  | `04_diagnostics_explore.ipynb`    | `matchedmanip/Reading.ipynb`                   | Exploration of the per-night summary CSVs         |
| 05  | `05_diagnostics_full.ipynb`       | `matchedmanip/Reading2.ipynb`                  | Full diagnostic-plot battery                      |
| 06  | `06_diagnostics_writing.ipynb`    | `matchedmanip/Writing.ipynb`                   | Writing summary tables (companion to 05)          |
| 07  | `07_lccal_wrapper.ipynb`          | `lccal/lccalwrapper.ipynb`                     | Light-curve calibration walkthrough               |
| 08  | `08_panstarrs_dr2_example.ipynb`  | `panstarrs_api/DR2API_example.ipynb`           | The MAST PanSTARRS DR2 API example                |
| 09  | `09_datreader.ipynb`              | `datmanip/DatReader.ipynb`                     | Quick `.dat` exploration                          |
| 10  | `10_noteread.ipynb`               | `datmanip/NoteRead.ipynb`                      | Notes-style record reading                        |
| 11  | `11_band_plots.ipynb`             | `pyfiles/bandPlots.ipynb`                      | grizy band-by-band magnitude plots                |
| 12  | `12_band_subtract.ipynb`          | `pyfiles/bandSubtract.ipynb`                   | Per-band subtraction analysis                     |
| 13  | `13_bolometric_plot.ipynb`        | `pyfiles/bolometricPlot.ipynb`                 | Pseudo-bolometric vs ROTSE mag plots              |
| 14  | `14_color_cut_fail.ipynb`         | `pyfiles/colorCutFail.ipynb`                   | Diagnostic for sources that fail color cuts       |
| 15  | `15_color_cut_plot.ipynb`         | `pyfiles/colorCutPlot.ipynb`                   | Color-cut visualization                           |
| 16  | `16_color_subtract.ipynb`         | `pyfiles/colorSubtract.ipynb`                  | Color subtraction analysis                        |
| 17  | `17_kron_diff.ipynb`              | `pyfiles/kronDiff.ipynb`                       | PSF - Kron magnitude differences                  |
| 18  | `18_deblended_flags.ipynb`        | `pyfiles/DeblendedFlags.ipynb`                 | Deblended-flag analysis                           |
| 19  | `19_noinfo_filter_flags.ipynb`    | `pyfiles/NoInfoFilterFlags.ipynb`              | "No info" filter-flag inspection                  |

## Migrating a notebook to use the new package

The originals import via the old paths (`import VSPFunctions as vsp`,
`import FitReader as fr`). To use the new package, replace those at the
top of the notebook with:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd().parent / "src"))   # if running from notebooks/

from vsp.io.fits_reader import FitReader
from vsp.calibration import cuts, photometry
from vsp.calibration.slopifier import slopify_exposure, slopify_night
from vsp.calibration.lccal import calibrate, RefStarCriteria
from vsp.crossmatch import crossmatch_night
from vsp.diagnostics.plots import plot_night_diagnostics
```

The functions take the same conceptual inputs but return cleaner
objects (DataFrames, dataclasses) instead of bare lists.
