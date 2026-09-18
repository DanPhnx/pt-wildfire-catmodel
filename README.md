# Portuguese Wildfire Catastrophe Loss Model (2023–2024)

A parametric catastrophe loss model for Portuguese wildfires, built as a portfolio
project demonstrating frequency/severity modeling, Monte Carlo simulation, and
tail-risk metrics (VaR, Expected Shortfall) as used in reinsurance pricing.

## Project structure

```
data/raw/          Raw EFFIS fire occurrence data, MODIS burn extent, Copernicus loss estimates
data/processed/     Cleaned CSVs ready for analysis
models/             Fitted distribution parameters (frequency, severity)
simulation/         Monte Carlo simulation output
notebooks/          Jupyter notebooks, one per project phase
```

## Data sources

- **EFFIS** (European Forest Fire Information System) — fire occurrence records
- **MODIS** — satellite-derived burn extent
- **Copernicus Emergency Management Service** — loss/damage estimates
- **ICNF** (Instituto da Conservação da Natureza e das Florestas) — Portuguese national fire statistics

## Methodology

1. **EDA** — load and clean raw data, explore annual fire counts and loss distributions
2. **Distribution fitting** — Poisson frequency model, Lognormal/Pareto severity model, goodness-of-fit testing
3. **Monte Carlo simulation** — 10,000-scenario aggregate loss simulation, VaR(95%), Expected Shortfall
4. **Validation** — backtesting against held-out years, parameter sensitivity, climate scenario analysis
5. **Writeup** — technical note summarizing methodology, results, and limitations

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

Work in progress — see notebook headers for phase-by-phase task tracking.

## Contact

Dan
