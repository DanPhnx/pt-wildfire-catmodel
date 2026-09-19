# Portuguese Wildfire Catastrophe Loss Model (2023-2024)

A parametric catastrophe loss model for Portuguese wildfires, built as a portfolio
project demonstrating frequency/severity modeling, Monte Carlo simulation, and
tail-risk metrics (VaR, Expected Shortfall) as used in reinsurance pricing.

## Project structure

```
data/raw/          Raw fetched data and the loss calibration reference table
data/processed/    Cleaned, per-fire-event CSV ready for analysis
models/            Fitted distribution parameters (frequency, severity)
simulation/        Monte Carlo simulation output
notebooks/         Jupyter notebooks, one per project phase
docs/              Phase implementation plans
```

## Data sources

- **GWIS** (Global Wildfire Information System, JRC/Copernicus): live annual
  fire-count and burnt-area series for Portugal, fetched via Our World in
  Data's CSV mirror. EFFIS's own Statistics Portal has no public JSON API
  (it's a JS single-page app), so this mirror is used instead; GWIS is run
  by the same JRC/Copernicus program as EFFIS.
- **ICNF / OECD / press reporting**: published aggregate wildfire loss
  figures (EUR), used to derive a documented EUR/hectare calibration
  constant since no source publishes verified loss per individual fire.
- **Copernicus Emergency Management Service (EMS)**: named major-event
  references (e.g. EMSR618 Serra da Estrela 2022, EMSR748 Central Madeira
  2024) used as tail-plausibility anchors, cited in notebook comments.
- Full sourcing rationale and known data gaps: see `docs/phase1-plan.md`
  and the "Data gaps and assumptions" section in `01_eda.ipynb`.

## Methodology

1. **EDA**: fetch real annual aggregates, synthesize per-fire records
   consistent with those aggregates, explore frequency and loss patterns
2. **Distribution fitting**: Poisson frequency model, Lognormal/Pareto
   severity model, goodness-of-fit testing
3. **Monte Carlo simulation**: 10,000-scenario aggregate loss simulation,
   VaR(95%), Expected Shortfall
4. **Validation**: backtesting against held-out years, parameter
   sensitivity, climate scenario analysis
5. **Writeup**: technical note summarizing methodology, results, and
   limitations

## Usage

Run notebooks in order:

```
01_eda.ipynb
02_distribution_fitting.ipynb
03_monte_carlo.ipynb
04_validation.ipynb
```

### Installation

```
pip install -r requirements.txt
```

## Status

Phase 1 (data and EDA) complete: `01_eda.ipynb` runs end to end and produces
`data/processed/wildfires_processed.csv`. See notebook headers for
phase-by-phase task tracking.

## Contact

Dan
