# Phase 1: Data & EDA - implementation plan

## Context

Phase 1 (weeks 1-2 of the PRD) needs real Portuguese wildfire data flowing into `notebooks/01_eda.ipynb`, producing a clean `data/processed/wildfires_processed.csv` with schema `Date | Location | Burned_Area_ha | Estimated_Loss_EUR`. The notebook currently has function stubs only.

Research done during this planning pass found three hard constraints that shape the approach:

1. **EFFIS has no simple one-shot bulk API for full per-fire granularity across 2010-2024.** The public Statistics Portal (forest-fire.emergency.copernicus.eu/apps/effis.statistics/estimates/PRT) is a JS single-page app; annual country-level totals are available as downloadable files, but a full historic per-fire extract for Portugal requires submitting JRC's official Data Request Form, with unknown turnaround time.
2. **Copernicus EMS gives free, no-auth, per-fire geospatial data, but only for activated events** (major/large fires that triggered Rapid Mapping, e.g. EMSR748 for the 2024 Madeira wildfire). It won't cover every fire in the 2010-2024 window, only the flagship ones, which happen to line up well with the project's 2023-2024 focus.
3. **No source publishes verified EUR loss per individual fire.** Published figures are annual aggregates from ICNF/government/OECD, and vary wildly year to year (e.g. long-run ICNF figure implies roughly EUR 1,900/ha averaged over 1975-2021 across 5.2M ha and >EUR 10bn losses, but 2017 alone was ~EUR 1.5bn government-estimated against a much smaller burned area, i.e. a far higher EUR/ha for catastrophic wildland-urban-interface years).

Given this, and the choices already confirmed with the user (fetch live data rather than wait on Kit; derive per-fire EUR via a documented burned-area x calibration-factor approach), Phase 1 needs a layered data pipeline with clearly logged manual-step fallbacks, not a single clean download. This matches the notebook's existing "Data gaps and assumptions" section, which should be filled with the real findings from this process rather than left as placeholder text.

## Recommended approach

### 1. Frequency data - annual fire counts (2010-2024, Portugal)
- Implement `fetch_effis_api` / `load_effis_data` to pull Portugal's annual fire-count and burnt-area totals from the EFFIS Statistics Portal. Since the page is JS-rendered, the notebook code needs to call the underlying data endpoint the frontend uses (found by inspecting the portal's network requests at implementation time) rather than scraping HTML.
- Fallback if no clean endpoint is found in a reasonable debugging window: manually download the portal's annual export and drop it into `data/raw/effis_annual_stats_prt.csv`, with a `# TODO (Kit)` comment marking this as a manual step so `load_effis_data` still works from the same file either way.

### 2. Severity data - per-fire burned area
- Pull the Copernicus EMS Rapid Mapping activations for Portugal's 2023-2024 wildfires (e.g. EMSR748 Madeira 2024, plus equivalent EMSR codes for mainland fires, identified from mapping.emergency.copernicus.eu/activations/ filtered to Portugal) via their public GeoJSON download links into `data/raw/copernicus_ems/`. These are real per-fire burned-area polygons for the flagship events.
- Submit the EFFIS historic Data Request Form in parallel (recommend Dan/Kit start this today, given unknown turnaround) to try to get the fuller 2010-2024 per-fire extract. If it doesn't arrive in time, explicitly document that the severity fit is calibrated mainly on major/EMS-activated fires - a real, citable limitation rather than a hidden gap.
- Descope the separate "MODIS per-fire" loader: repurpose `load_modis_burn_extent` into a lighter cross-validation check against a public MODIS-derived annual burnt-area aggregate (e.g. GWIS), instead of a raster/per-fire pull. This keeps the pipeline inside the PRD's numpy/scipy/pandas/matplotlib/requests stack (no geopandas/rasterio needed) while still using MODIS as named in the PRD's data sources.

### 3. Loss calibration - Estimated_Loss_EUR per fire
- Build `data/raw/annual_loss_calibration.csv` with columns `year, total_burned_area_ha, total_estimated_loss_eur, source_url, notes`. Seed it with the figures found today (ICNF long-run 1975-2021 baseline, 2017 outlier-year figures) and flag 2023/2024 for a closer look during implementation, since more specific recent figures likely exist.
- In `clean_and_merge`, apply a single documented EUR/ha calibration constant to `Burned_Area_ha` to produce `Estimated_Loss_EUR`, with an explicit comment that real losses aren't strictly linear in area (structures, fatalities, wildland-urban-interface proximity matter). This becomes a named modeling limitation, feeding directly into the PRD's Phase 4/5 "Limitations" write-up.

### 4. Notebook wiring
- Replace the stubs in `notebooks/01_eda.ipynb` (`fetch_effis_api`, `load_effis_data`, `load_modis_burn_extent`, `load_copernicus_losses`, `clean_and_merge`) with real implementations per the above.
- Leave `plot_annual_fire_counts`, `plot_loss_histogram`, `plot_empirical_cdf` as-is (already implemented) - just run them against the real merged output.
- Fill in the notebook's existing "Data gaps and assumptions" markdown cell with what actually happened: EFFIS historic per-fire archive needs a manual request, loss-per-hectare is a simplifying linear assumption, severity sample skews toward major/EMS-activated fires unless the historic extract arrives in time.

## Files touched
- `notebooks/01_eda.ipynb` - main implementation target
- `data/raw/effis_annual_stats_prt.csv`, `data/raw/copernicus_ems/*.geojson`, `data/raw/annual_loss_calibration.csv` - new real inputs
- `data/processed/wildfires_processed.csv` - generated output
- `README.md` - small update once the real access method (API vs. manual download vs. request form) is confirmed

## Verification
- Run `01_eda.ipynb` top to bottom on a fresh kernel; confirm `wildfires_processed.csv` is produced with no unexplained NaNs.
- Visual sanity check: `plot_annual_fire_counts` should show the known 2017 and 2023/2024 spikes.
- Order-of-magnitude sanity check: modeled `Estimated_Loss_EUR` totals for 2023/2024 should land in the same ballpark (tens to hundreds of millions EUR) as the published aggregate figures gathered during research - doing the PRD's "Domain Validation" check early rather than waiting for Phase 4.
- Confirm the "Data gaps and assumptions" section accurately reflects what was actually obtained vs. what needed a manual/fallback step.
