# Phase 1 data summary — for Kit

Short note for the Week 2 handover ("cleaned data CSV and data summary
document"). It's a checklist for your sanity-check role (data curation,
validation, clarity), not a repeat of `docs/phase1-writeup.md`, which has
the full working if you want it.

## What you're looking at

`data/processed/wildfires_processed.csv` — one row per real mainland
Portuguese wildfire, 2009–2025, 30 ha or larger, 3,785 rows:

| Column | What it is |
|---|---|
| `Date` | Real fire start date (EFFIS) |
| `Location` | Real NUTS2 region |
| `Burned_Area_ha` | Real mapped burned area |
| `Estimated_Loss_EUR` | Modeled loss, in that fire's own-year euros |
| `Estimated_Loss_EUR_2025` | Modeled loss, restated to 2025 euros |
| `Loss_Source` | Always `"modeled (area x central EUR/ha)"` — see below |

## Decisions made so far (flag anything that looks wrong)

- **Mainland Portugal only.** Madeira and the Azores are excluded (per the
  revised PRD's scope).
- **"Fire event" = a mapped fire of 30 ha or more, every year.** EFFIS's
  own mapping threshold only holds through 2018; from 2019 it maps much
  smaller fires too, so the 30 ha cut is applied explicitly rather than
  trusting the raw file. Re-tested at 100 ha (PRD ask): keeps half the
  events and 94.7% of the area, same conclusions. 30 ha kept as primary.
- **Loss type: direct economic damage** (not insured loss — insured loss
  is a small share, ~17% of the 2017 total).
- **Loss is modeled, not observed, for every row.** No source publishes
  loss per individual fire — only annual or event totals exist, and only
  2017 has an official one in this window. So every row's loss is area ×
  a EUR/ha figure, and `Loss_Source` says so explicitly rather than
  implying any row is a real reported number.
- **EUR/ha is a range, not one number: low 497 / central 2,296 / high
  3,167** (2025 euros). Only 2017 has an official total to calibrate
  against; the range brackets it rather than fitting it exactly. See
  `data/raw/loss_anchors.csv` for what backs each figure, including two
  I could **not verify** (Madeira 2016, 2003) — flagged there.
- **Backtest hold-out: 2021–2025** (train on 2009–2020). Keeps 2017 — the
  main severity anchor — in training; the hold-out mixes quiet years
  (2021, 2023) and severe ones (2022, 2024, 2025).

## What I'd want you to sanity-check

1. **2017 total:** modeled €1,057m (in 2017 euros) vs the official EU
   Solidarity Fund figure of €1,458m (72%). I derived that €1,458m by
   arithmetic from a search summary, not by reading the primary EU
   document — worth an independent look if you can access it.
2. **2024 and 2025:** no published *total* economic loss found for either
   year — only components (2024: €67m forest-sector loss + €17m+ insured
   claims ≈ €84m, vs a modeled €309m). If you know of a fuller 2023/2024/2025
   figure, that would let us test the PRD's "within published range"
   criterion, which currently has nothing to test against.
3. **Two open, unverified anchors in `data/raw/loss_anchors.csv`:**
   Madeira 2016 (€157m) and 2003 (>€800m) — both taken from your PRD
   revision, neither independently confirmed by me.
4. **A finding worth a second pair of eyes:** annual fire count and
   fire size are correlated (bad years have both more and bigger fires),
   and fires cluster on the same day (33 fires burned 196,476 ha on one
   day in October 2017). Full detail in the write-up's "What the data
   shows" section — flagging in case it changes how you'd want the
   simulation built.
5. **A new dataset I haven't integrated:** ICNF (via its own data
   manager) publishes a full per-fire national database, 1980–2025, all
   fire sizes, on Zenodo (`10.5281/zenodo.21427772`, CC-BY). It would let
   the record reach the PRD's 1980 target properly. It's a ~940 MB file,
   so pulling it in is a real decision, not a quick add. Not pursued for
   now — Phase 2 is already under way on EFFIS — but noted in
   `docs/worklog.md` if it's worth revisiting later.

## Where things stand (updated after this note was first written)

- **Phase 2, frequency: done.** Events are re-grouped into "fire-day"
  clusters (same start date) rather than modeled per raw polygon — see
  point 4 above, now acted on. A formal dispersion test rejects a plain
  Poisson decisively; Negative Binomial is the chosen frequency model, on
  the confirmed 2009–2020 training years, saved to `models/`.
- **Phase 2, severity: not yet done.** Lognormal body + Generalised Pareto
  tail, goodness-of-fit, still to come.
- **Phases 3–4: not started.**
- `data/processed/wildfires_processed.csv` isn't committed to git — it
  regenerates from `notebooks/01_eda.ipynb` (or `python main.py`).
