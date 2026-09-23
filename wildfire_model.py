"""Shared, importable logic used by more than one phase notebook.

Kept out of the notebooks per the PRD's technical decision ("Entry point:
one main.py; notebooks for EDA only") - phase notebooks are read as EDA and
diagnostics, not as the owner of logic that other phases also depend on.
Only 01_eda.ipynb reads raw EFFIS data; from here on, phases 2-4 work from
data/processed/wildfires_processed.csv and this module.

Import from a notebook (which runs with the notebook's own directory as
its working directory) with:

    import sys
    sys.path.insert(0, "..")
    from wildfire_model import build_fire_day_events
"""

import pandas as pd

# Confirmed Phase 1 checkpoint decision (see docs/worklog.md): train on
# 2009-2020, hold out 2021-2025 for the Phase 4 backtest. Keeps 2017 - the
# main severity-tail anchor - in training; the hold-out mixes quiet years
# (2021, 2023) and severe ones (2022, 2024, 2025).
TRAIN_YEARS = (2009, 2020)
HOLDOUT_YEARS = (2021, 2025)


def build_fire_day_events(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-fire records into fire-day events.

    Individual EFFIS polygons are not independent events for modelling
    purposes: multiple fires on the same day are often the same
    weather-driven outbreak rather than unrelated ignitions (e.g. 33
    polygons burned 196,476 ha on 2017-10-15 alone). Grouping by start date
    is the event definition chosen during the Phase 1 review (see
    docs/worklog.md and the "What the data shows" section of
    docs/phase1-writeup.md): on the full 2009-2025 record it cuts annual
    overdispersion from ~41 (per-polygon) to ~5.5 (fire-day) and removes
    the significant count-vs-size correlation (rho 0.57, p = 0.02
    per-polygon vs rho 0.25, p = 0.33 fire-day); a residual dependence
    remains (annual-area SD is still ~1.8x an independent model's).

    This is a simple first choice (same calendar start date, national
    scope, no distinction between simultaneous fires in different
    regions) and is flagged in the worklog as something to revisit later
    (e.g. multi-day windows, in the style of a treaty hours clause).

    Parameters
    ----------
    df : pd.DataFrame
        Per-fire records with Date, Burned_Area_ha, Estimated_Loss_EUR and
        Estimated_Loss_EUR_2025 (as produced by 01_eda.ipynb).

    Returns
    -------
    pd.DataFrame
        One row per calendar day with at least one fire event, sorted by
        date. Columns: Date, N_Fires, Burned_Area_ha, Estimated_Loss_EUR,
        Estimated_Loss_EUR_2025 (all but N_Fires summed across that day's
        fires). Estimated_Loss_EUR is summed in each fire's own-year
        euros, which is exact here since a fire-day never spans a year
        boundary.
    """
    day = df["Date"].dt.normalize()
    events = df.groupby(day).agg(
        N_Fires=("Burned_Area_ha", "size"),
        Burned_Area_ha=("Burned_Area_ha", "sum"),
        Estimated_Loss_EUR=("Estimated_Loss_EUR", "sum"),
        Estimated_Loss_EUR_2025=("Estimated_Loss_EUR_2025", "sum"),
    )
    events.index.name = "Date"
    return events.reset_index().sort_values("Date").reset_index(drop=True)


def split_train_holdout(events: pd.DataFrame, date_col: str = "Date") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split events into the confirmed training and hold-out windows.

    Parameters
    ----------
    events : pd.DataFrame
        Event-level data with a date column (fire-day events or raw
        per-fire records both work).
    date_col : str
        Name of the date column.

    Returns
    -------
    (pd.DataFrame, pd.DataFrame)
        (train, holdout), split on TRAIN_YEARS / HOLDOUT_YEARS.
    """
    year = events[date_col].dt.year
    train = events[year.between(*TRAIN_YEARS)]
    holdout = events[year.between(*HOLDOUT_YEARS)]
    return train, holdout
