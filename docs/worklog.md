# Worklog

Running notes on what was tried, what worked, what didn't, and why, as the
project went. Kept separate from `docs/phase1-plan.md` (the forward-looking
plan) since this is a backward-looking record.

## Environment setup

- Git, GitHub CLI (`gh`), and Python were not preinstalled on this machine.
  Installed all three via `winget`. Each install requires the current
  PowerShell session's `PATH` to be refreshed manually (new installs don't
  appear until a fresh shell, or until `$env:PATH` is patched in-session).
- `gh auth login` is the actual "connect your GitHub account" step: a
  one-command device-code flow that opens the browser for a one-click
  authorization. No separate account-linking step exists.
- `gh auth login` alone does not wire credentials into plain `git` commands
  (`git push` still fails with "terminal prompts disabled"). Needed
  `gh auth setup-git` afterward to make `git push`/`pull` work without `gh`
  in front of every command.

## Finding real data sources (Phase 1)

- The PRD named EFFIS, MODIS, Copernicus, and ICNF as data sources. In
  practice:
  - **EFFIS's own Statistics Portal** (forest-fire.emergency.copernicus.eu)
    is a JS single-page app with no public JSON API. Scraping it directly
    (via WebFetch) returns either a loading placeholder or the raw SPA
    shell, never data.
  - **Our World in Data** publishes a plain CSV mirror of GWIS (Global
    Wildfire Information System, the same JRC/Copernicus program behind
    EFFIS) at predictable URLs
    (`ourworldindata.org/grapher/<slug>.csv`), no auth needed. This is
    what actually made live, scriptable annual data possible:
    `annual-number-of-fires.csv` and
    `annual-area-burnt-by-wildfires-gwis.csv`.
  - **No public source publishes verified EUR loss per individual fire.**
    Only annual/period aggregates exist (ICNF, OECD, press reporting), and
    they vary a lot year to year (a long-run 1975-2021 average implies
    roughly EUR 1,900/ha, but the catastrophic 2017 season implies closer
    to EUR 2,900/ha, since fatalities and structure loss dominate in bad
    wildland-urban-interface years, not hectares burned).
  - **Copernicus EMS** gives free, no-auth, per-fire geospatial downloads,
    but only for activations it triggers on (major/large fires), e.g.
    EMSR618 (Serra da Estrela, 2022, ~25,000 ha) and EMSR748 (Central
    Madeira, 2024, >5,000 ha). Useful as named tail-plausibility anchors,
    not a systematic per-fire feed.

- Given no free bulk per-fire micro-data was available up front, the first
  working version of `01_eda.ipynb` synthesized individual fire records:
  real annual fire count and real annual total burnt area (from the OWID/
  GWIS mirror) were preserved exactly, but each year's total was split
  across synthetic individual fires using a Lognormal shape. This was
  explicitly documented as illustrative, not ground truth, in the
  notebook's "Data gaps and assumptions" section.

## A reproducibility gap, found and fixed

- The PRD's success criteria include "fresh clone -> same results." The
  first implementation didn't actually satisfy this: OWID/GWIS is a live,
  continually-updated source (the in-progress current season updates as it
  goes, and historical figures can be revised), and the fetch had no year
  cap. A rerun next month could silently include more of an in-progress
  year or picked-up revisions.
- Fixed by: freezing a `MAX_YEAR = 2024` cap in the notebook, and
  committing the fetched raw CSVs to git as the authoritative snapshot
  (they were previously gitignored, so nothing was actually pinned).

## A schema mismatch, found and fixed

- The Phase 2-4 notebook skeletons (written before Phase 1's real
  implementation existed) assumed lowercase column names
  (`date`, `estimated_loss_eur`). Phase 1's actual output uses the PRD's
  capitalized schema (`Date`, `Estimated_Loss_EUR`). Found during a
  deliberate "recap and find holes" pass, not by running Phase 2 and
  hitting a KeyError. Fixed in both files.

## Getting real per-fire data

- Submitted EFFIS's official Data Request Form
  (forest-fire.emergency.copernicus.eu/apps/data.request.form/) for
  Portugal, 2010-01-01 to 2024-12-31, dataset option "Burnt area mapped
  using Sentinel2/MODIS images" (not the VIIRS/MODIS thermal-anomaly
  options, which are point detections, not per-fire burned-area polygons).
- First response only covered 2010-2014 (suggested the system might
  auto-chunk large requests). Resubmitting for the full range worked on
  the second attempt and returned the complete 2010-2024 window in one
  file, so chunking wasn't actually required.
- Result: EFFIS's real Rapid Damage Assessment (MODIS-based) database for
  Portugal, 6,608 real fire records, 2010-2024, with real dates, real
  NUTS2 region locations, and real burned areas in hectares.
- Important caveat, per EFFIS's own documentation bundled with the data:
  this product only maps fires of roughly 30 ha or larger. That subset
  still represents an estimated 75-80% of Portugal's total burnt area
  despite being a small fraction of total fire *count* (most fires are
  small).

## Real data integration (done)

- Copied the real EFFIS CSV into `data/raw/effis_fire_database_pt_2010_2024.csv`
  (plus its `.readme.txt`) and committed both to git (updated `.gitignore`
  accordingly). It's a static, one-time export, not a live API, so there's
  no reproducibility drift risk for this component at all.
- The suspected encoding issue turned out not to be real: accented
  characters like "Tâmega" displayed as "TÃ¢mega" only in the PowerShell
  console (a display/codepage artifact), not in the actual file bytes.
  `pd.read_csv(..., encoding="utf-8")` reads it correctly with no fixup
  needed. Lesson: don't trust terminal display for encoding diagnosis,
  check what pandas actually loads.
- `initialdate` has mixed timestamp formats (some with fractional
  seconds), which broke a plain `pd.to_datetime` call. Fixed with
  `format="mixed"`.
- 40 of 6,608 raw rows had `area_ha <= 0`; dropped as non-physical mapping
  artifacts (EFFIS's own documentation mentions small/unmapped islands
  within a burn scar as a known cause).
- Replaced `synthesize_fire_events` and `_fire_season_weights` entirely
  with `load_effis_fire_database`, which reads the real file directly.
  Frequency is now defined as "real large-fire (~30ha+) events per year,"
  per the decision below, not "all fires."

## Frequency scope decision (made with the user)

- Real severity data only covers large (~30ha+) fires, while the
  previously-used OWID frequency series counted every fire including tiny
  ones, an inconsistent pairing once real severity data existed.
- Decision: frequency (Poisson lambda) = count of real large-fire records
  per year, dropping the all-fires OWID count from the primary pipeline.
  Rationale: for a catastrophe loss model focused on tail risk (VaR,
  Expected Shortfall), immaterial small fires don't drive the numbers that
  matter, and this keeps frequency and severity internally consistent,
  both drawn from the same real dataset. A "fire event" in this model now
  specifically means a mapped ~30ha+ fire, not every ignition in Portugal,
  an explicit, documented scope choice.

## Two real discrepancies found during cross-validation

Kept the live OWID/GWIS fetch in the notebook specifically to cross-check
the real EFFIS data against an independent source, rather than just
trusting one dataset. That check surfaced two genuine mismatches, one
explained by methodology, one investigated further and mostly resolved
(see "Assessing the discrepancies" below).

1. **Count**: EFFIS's large-fire-only annual counts are sometimes *higher*
   than OWID's all-fire counts for the same year (e.g. 2022: ~1,210 real
   large-fire records vs. 465 in OWID's all-fire series). Backwards at
   first glance, but explained by differing methodologies: EFFIS's MODIS
   Rapid Damage Assessment maps burnt-area polygons at 250m resolution,
   refined by visual interpretation, while OWID/GWIS's fire count is built
   from VIIRS thermal-anomaly point detections clustered into events, a
   different sensor and a different definition of "one fire."
2. **Area**: summed real large-fire area exceeds GWIS's reported total
   burnt area in every single year in the dataset (85%-197%, mean 116.6%
   as first reported), which should be impossible if large fires were
   truly a subset of the total, as EFFIS's own documentation (~75-80% at
   EU level) implies.

## Assessing the discrepancies (deeper investigation, at the user's request)

The user asked to actually assess these rather than leave them as "probably
methodology differences." Concrete checks run against the raw data:

- **The "116.6% mean" statistic was itself misleading.** It's an unweighted
  average of per-year ratios, so a tiny year like 2021 (197% ratio, but
  only a ~16,000 ha absolute gap) counts the same as a huge year like 2017
  (108% ratio). The properly weighted total-to-total ratio across all 15
  years (sum of real area / sum of GWIS area) is **106.1%**, a modest
  overshoot well within the normal disagreement range between independent
  satellite burnt-area products. Lesson: check whether a summary statistic
  is actually the right one to report before treating it as the finding.
- **Found and fixed a real, separate data-quality defect**: 69 rows in the
  raw export are exact duplicates (same parish `admlvl5`, same `area_ha`,
  same `initialdate` down to the minute, but a different `id`), all tiny
  fires (1-12 ha), concentrated in 2021-2024. Total excess area: ~104 ha
  out of 1.71M ha (0.01%), immaterial to the model, but a confirmed export
  artifact rather than a methodology difference, so deduplicated in
  `load_effis_fire_database` (down to 6,533 usable records from 6,568).
- **A real, smaller pattern remains, not fully explained**: a 3-year
  rolling comparison shows ~92-108% agreement through 2012-2019, rising to
  ~114-134% for 2020-2024. Checked and ruled out the duplicate records
  above as the cause (too small in area to move this). Left as an open
  question rather than force-resolved - possible causes not yet checked:
  GWIS/OWID's most recent years being less finalized/revised than older
  years, or a genuine change in EFFIS's own detection methodology over
  time.
- **Bonus find while investigating the top outlier fires**: the 5 largest
  fires in the real dataset all check out against known history (the two
  ~67,500 ha and ~64,300 ha October 2017 fires match the well-documented
  2017 catastrophic complex). A 35,523 ha fire in Centro region, September
  2024, is very likely the mainland fire behind Copernicus EMS activation
  EMSR760 (Sever do Vouga), which earlier research couldn't find a hectare
  figure for. Added as a reference point in the notebook's domain
  validation section, flagged as plausible but not confirmed against the
  activation record itself.

## Sensor break in the EFFIS export, found and fixed (Sept 2026 review)

A review of Phase 1 found that the "all records are ~30 ha or larger"
assumption above is only true for part of the export. This supersedes the
"Frequency scope decision" and the count/area discrepancy notes above.

- `map_source` is `modis` for 2010-2018, `modis/sentinel2` for 2019 and
  `sentinel2` for 2020-2024. The smallest mapped fire drops from 12-24 ha to
  1 ha in 2020, and 62-82% of 2020-2024 records are under 30 ha (1-9% in
  2010-2018). Unfiltered mean annual counts go from ~248 (2010-2019) to
  ~811 (2020-2024).
- That was previously read as "more, smaller large fires in recent years".
  It is a sensor artifact. It would also have broken Phase 2 (a non-
  stationary frequency series) and the Phase 4 backtest (last five years =
  entirely the Sentinel-2 era).
- Fix: `MIN_FIRE_AREA_HA = 30` applied uniformly in
  `load_effis_fire_database`. Leaves 3,291 of 6,533 cleaned records and
  98.2% of mapped area. Filtered mean counts: 232/yr (2010-2019) vs 194/yr
  (2020-2024), i.e. no trend.
- Count discrepancy vs OWID: fully resolved by the filter (0 of 13 years
  where EFFIS >= 30 ha count exceeds OWID's all-fire count). The MODIS-vs-
  VIIRS explanation recorded above was wrong for this.
- Area discrepancy vs GWIS: only partly resolved. Weighted ratio 106.1% ->
  104.2%. 2010-2019 stays ~102%; 2020-2024 goes ~120% -> ~112%. An initial
  expectation that the filter would explain most of the gap was too
  optimistic (it explains roughly 40% of the excess). Residual is still
  open; candidate causes are GWIS's latest years being less finalized, and
  Sentinel-2 10 m perimeters vs 250 m MODIS.
- Annual counts are strongly overdispersed (variance/mean ~44), flagged for
  Phase 2 (test Negative Binomial).
- Lesson: an assumed property of a dataset taken from its documentation (here,
  "maps fires of ~30 ha or larger") should be checked against the data
  itself, per subgroup (here, per year and per `map_source`) before it is
  used as a modeling premise.

## Open items

- Phases 2-4 (distribution fitting, Monte Carlo, validation) haven't
  started yet.
- The residual 2020-2024 area-ratio divergence (~112% vs GWIS after the 30 ha filter) is still an open question.
- Copernicus EMS 2023-24 loss data not yet obtained; modeled 2023/2024 totals not yet compared with published figures.
