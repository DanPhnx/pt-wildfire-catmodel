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

## Published-loss benchmarks for 2024 (Sept 2026 review)

Looked for published 2023/2024 loss figures to test the EUR/ha calibration,
and for Copernicus EMS data, since the PRD lists both as Phase 1 tasks.

- Found and recorded in `data/raw/published_loss_benchmarks.csv` (each row
  sourced): AGIF national 2024 burnt area 137,667 ha (EFFIS 30 ha+: 143,684 ha,
  +4%); forest-sector loss EUR 67m (forest only); provisional insured claims
  >EUR 17m (Sep 15-19 fires only); Copernicus EMS burnt area 111,323.6 ha
  across four September 2024 areas of interest, EMSR760 alone 21,262.5 ha.
- **Not found: any published total economic loss for 2023 or 2024.** The
  EUR 638m figure in the AGIF report is state spending on the fire system,
  not a loss. So the modeled 2024 total (~EUR 276m) is bracketed by
  component figures (~EUR 84m measured floor) but not validated, and the
  PRD's "within ~20% of published reports" test has no benchmark yet.
- Corrected an earlier notebook claim: the 35,523 ha Centro record from
  September 2024 was called "plausibly the fire behind EMSR760". Copernicus
  reports 21,262.5 ha for EMSR760, so that cannot be the same perimeter.
- The 2017 "sense check" (EUR 1.08bn modeled vs ~EUR 1.5bn) is not
  independent: it restates the 1,923 vs 2,865 EUR/ha calibration gap.
- Copernicus EMS per-fire geometries were not downloaded; only the
  published burnt-area totals were used. Per-fire EMS polygons would need
  geospatial tooling outside the PRD stack and are not needed for the model.

## Decisions and corrections after the revised-PRD review (Sept 2026)

Reviewed the proposed PRD revision against the data. Decisions made with
the user, and what changed:

- **Mainland only (applied).** 48 raw records are Madeira (44) or Azores (4)
  (`admlvl1` other than "Continente"); the 28 Madeira records that survived
  cleaning were 1.9% of area. `load_effis_fire_database` now filters them.
  Result: 3,263 events (was 3,291). This also corrected an earlier claim
  that 2024 area agreed with AGIF "within 4%": mainland 137,564 ha vs AGIF
  137,667 ha is 99.9%; the 4% came from including Madeira.
- **Duplicate count corrected.** Earlier notes said "69 duplicates". 69 is
  the number of rows sitting in duplicate sets (33 pairs and one triple); 35
  are redundant copies and are what is removed (~104 ha). Cleaning waterfall:
  6,608 -> 6,560 mainland -> 6,520 area > 0 -> 6,485 deduplicated -> 3,263 at
  >= 30 ha.
- **Recomputed on the mainland basis:** total-to-total area ratio vs GWIS
  102.2% filtered (104.1% unfiltered); 2010-2019 100.7%, 2020-2024 108.1%
  (116.0% unfiltered). The 30 ha filter explains about half of the
  2020-2024 excess, not most of it. GWIS's "Portugal" may include the
  islands, not checked.
- **Frequency-severity dependence is real (bad).** Count vs median fire
  size rho 0.58, permutation p = 0.026 (holds without 2017); an independent
  model gives annual-area SD ~61k ha vs 134k ha observed and never produces
  a 2017-sized year. Bad for the PRD's "count, then independent severities"
  engine, but modelable.
- **Event unit: fire-day clusters (decision).** Polygons on the same start
  date are one event: 1,106 events, overdispersion ~6, count-size
  correlation not significant. Clustering alone does not remove the
  dependence (annual SD still ~1.85x the independent value), so Phase 2-3
  add a year-level severity factor and a whole-year bootstrap cross-check.
  **TO REVISIT LATER:** the fire-day rule (same start date, national
  scope) is a simple first choice. Test multi-day windows (treaty hours-
  clause style), and check the 2017-10-15 cluster's sensitivity to the
  window.
- **EUR/ha is a range, with one mainland anchor.** Built
  `data/raw/loss_anchors.csv` (evidence table) and rebuilt
  `annual_loss_calibration.csv` as low 487 / central 1,923 / high 2,593. The
  old "2,865" high figure divided a 2017 loss by GWIS area; the new one uses
  the same EFFIS mainland area basis as the model. 2017 EUSF total EUR
  1,458m is derived by arithmetic (0.832% of GNI vs a EUR 1,051.6m
  threshold), primary document not opened. Madeira 2016 (EUR 157m over
  5,409 ha, ~EUR 29,000/ha) excluded as out of scope; 2003 (>EUR 800m,
  ~425,000 ha) is a candidate second anchor needing verification of both
  figures. Not verified: the Madeira 2016 and 2003 damage figures come from
  the proposed PRD revision.
- **EFFIS re-export (done, see next section).** Still pending on the user:
  look at what ICNF publishes (per-fire or size-class data, or annual
  totals only). Scope left as the revised PRD has it.
- **Not yet done:** per the revised PRD, `Estimated_Loss_EUR` should be
  filled only where a sourced figure exists; today every event gets the
  central-scenario value.

## EFFIS re-export: 2008-2026 delivered, record set to 2009-2025 (Sept 2026)

Requested a second EFFIS export (Portugal, 2000-01-01 to 2025-12-31) to
extend the record and add 2025, as the revised PRD asks.

- **Delivered:** 9,262 records, 2008-04-26 to 2026-09-17. **Nothing before
  2008 came back**, so the PRD's 1980 target (and a 2000 start) is not
  available from EFFIS; the record can grow by 2008, 2009 and 2025 only.
  The file came without a readme; the earlier readme (same product) is kept
  beside it with a note explaining this.
- **Overlap check passed:** all 6,608 records for 2010-2024 match the
  earlier export exactly (same ids; zero mismatches in area, dates,
  locations, `map_source`, coordinates). Same data version, so the new file
  replaces the old one (git history retains it) rather than sitting beside
  it.
- **Decision (user): 2009-2025.** 2008 excluded: 33 records, the first on
  2008-04-26; 5,350 ha at >= 30 ha is 79% of GWIS's 6,762 ha, so it looks
  real but low-information, with uncertain early-season coverage. 2026
  excluded: partial year (to 17 Sept). 2025 included but provisional.
  Loader now takes `start_year`/`end_year` (`START_YEAR = 2009`,
  `MAX_YEAR = 2025`).
- **Cleaning waterfall (2009-2025):** 9,262 -> 9,212 mainland (50 island
  records) -> 7,900 in window (33 from 2008, 1,279 from 2026) -> 7,809 area
  > 0 -> 7,749 deduplicated (60 redundant copies; 115 rows in duplicate
  sets; ~157 ha) -> **3,785 events at >= 30 ha**.
- **Everything recomputed:** mean counts 239 (2009-2019) vs 193 (2020-2025);
  variance/mean ~41; GWIS ratio 102.9% filtered (104.7% unfiltered), 101.2%
  for 2009-2019 and 106.5% for 2020-2025 (111.7% unfiltered), so the
  filter explains close to half of the recent excess and ~6.5% remains;
  count discrepancy vs OWID still 0 of 14 years. Dependence finding
  strengthened slightly with more data: count vs median size rho 0.57,
  permutation p = 0.019 (n = 17; p = 0.023 without 2017); annual-area SD
  ~133k ha observed vs ~64k independent (2.1x). Fire-day events: 1,283,
  overdispersion ~5.5, count-size rho 0.25 (not significant), annual SD
  still ~1.8x the independent value.
- **2025 checked against the revised PRD's claim:** 200 mainland events,
  278,917 ha, vs "roughly 274,000-278,000 ha" in the PRD (about 0.3% above
  the top of that range) and GWIS 266,907 ha (EFFIS is 104.5% of it). 2025
  is 2nd by area but 9th by count: an average number of fires, very large
  ones (83% of area in August; four polygons on 2025-08-10 cover 113,675
  ha). A second extreme year of a different character from 2017, and
  provisional. Modeled 2025 under the EUR/ha range: EUR 136m / 536m / 723m;
  no published 2025 loss figure has been looked up yet.
- **2003 and 2005** are not in the EFFIS export. The GWIS snapshot in
  `data/raw/` has annual burnt area from 2002 (e.g. 2005: 332,485 ha),
  usable as annual-area context but not for per-fire fits.

## Inflation adjustment to 2025 euros (Sept 2026)

Revised-PRD Phase 1 item "inflation-adjust losses to 2025 euros". Chosen
design (user): two per-fire columns, one in the euros of the fire's own
year and one in 2025 euros.

- **Deflator:** Eurostat `prc_hicp_aind`, Portugal, all-items, annual
  average index (2015 = 100), fetched in the notebook and committed as
  `data/raw/pt_hicp_annual.csv` (same snapshot pattern as OWID). Uplifts to
  2025: x1.022 from 2024, x1.194 from 2021, x1.221 from 2017, x1.526 from
  2003. HICP is a general consumer index, not construction cost.
- **Columns:** `Estimated_Loss_EUR` (each fire's own-year euros) and
  `Estimated_Loss_EUR_2025`. Per-fire loss is still area x the central
  EUR/ha for every event; "fill only where sourced" is still pending.
- **Restated EUR/ha (2025 prices):** low 497 (was 487), central 2,296 (was
  1,923), high 3,167 (was 2,593). Low and high have known price years (2024,
  2017). **Central's price year is unknown** (cumulative 1975-2021 total in
  mixed-year euros, via OECD/press): assumed 2021 (`CENTRAL_PRICE_YEAR`),
  the smallest possible uplift, so it is a floor and likely understated.
  Change the constant to test sensitivity.
- **Effects on earlier claims:** the 2017 check moves from 74% to 72% (in
  2017 euros, central EUR 1,057m vs official EUR 1,458m). 2024 central
  total is EUR 309m in 2024 euros (was 265m), against a EUR 84m component
  floor (27%). Modeled 2025 (provisional): EUR 139m / 640m / 883m in 2025
  euros. Madeira 2016 restates to ~EUR 36,000/ha (2025 prices) and 2003 to
  ~EUR 2,900/ha, which lies between central and high, so the central
  scenario sits below both catastrophic anchors.
- **Assumption to keep visible:** real EUR/ha constant over time (no value
  growth); the PRD's +/-5%/yr value-growth sensitivity is the place to test
  it.

## Phase 1 close-out: threshold sensitivity and reproducibility scaffolding (Sept 2026)

- **100 ha re-run (PRD Phase 1 technical decision), done in `01_eda.ipynb`.**
  100 ha keeps 1,893 of 3,785 events (50%) and 94.7% of the 30 ha
  threshold's total area. Overdispersion persists (39.1 vs 40.96); the
  count-vs-median-size correlation weakens (rho 0.46, p = 0.061 vs 0.57,
  p = 0.017) but the sample is smaller, so this doesn't read as the
  dependence going away. Decision: keep 30 ha as the primary threshold - it
  retains far more area and doesn't depend on ICNF's administrative
  "major fire" line, which the model doesn't otherwise use.
- **Reproducibility scaffolding.** `requirements.txt` pinned to exact
  versions (was `>=`). Added `main.py`: runs each phase notebook in order
  via `nbconvert`, detects a still-`NotImplementedError` phase and skips it
  with a message instead of a confusing traceback (today: Phases 2-4).
  README rewritten: installation, usage (`python main.py`), what's
  scriptable (OWID/GWIS/HICP) vs a one-time manual export (EFFIS, already
  committed so a fresh clone needs no re-request), and an honest
  Phase 1 complete / Phases 2-4 not started status.
- **Open conflict, not resolved: "fill Estimated_Loss_EUR only where a
  sourced figure exists" (revised PRD, Phase 1 deliverable) vs the
  per-fire schema.** No source publishes loss at the per-fire grain the
  CSV schema uses (`Date | Location | Burned_Area_ha | Estimated_Loss_EUR`,
  one row per fire) - only annual/event aggregates exist, and only one
  (2017) is inside the model's mainland/2009-2025 window. Filling "only
  where sourced" at that grain would leave the column almost entirely
  empty, which is arguably more honest but breaks every downstream
  consumer (Phase 2's severity fit, Phase 3's simulation) that expects a
  populated per-fire loss. Current state (every event gets the
  area x central-EUR/ha value) is unchanged pending a decision from Dan on
  how to reconcile this.
- **Checkpoint decisions still open (need Dan/Kit):** loss type - assumed
  direct economic damage throughout, not yet explicitly confirmed; backtest
  hold-out years - suggested 2021-2025 (5 years, includes both extreme
  years 2017 falls outside the holdout and 2025 inside), not yet confirmed.
- **Kit handover:** the write-up (`docs/phase1-writeup.md`) and README
  together cover the Week 2 "cleaned data CSV + data summary" handover; no
  separate document has been made. Flag if a standalone summary is wanted.

## ICNF check: answered, and it's bigger than expected (Sept 2026)

Looked into what ICNF actually publishes (the item pending since the
revised-PRD review). Short answer: a full per-fire national database,
1980-2025, all fire sizes, not just annual totals.

- **Found:** "Portuguese Rural Fire Database (PRDF), 1980-2025"
  (zenodo.org/records/21427772, DOI 10.5281/zenodo.21427772), uploaded
  22 July 2026, version V2025.1. First author Rui Lopes Almeida, listed as
  a data manager at ICNF; co-authors from the Forest Research Centre
  (TERRA) and INESC TEC/FEUP. It is a new version of the dataset behind a
  peer-reviewed 2011 NHESS paper on the 1980-2005 Portuguese rural fire
  database (a known, cited source in the wildfire literature), extended to
  2025. Open access, CC-BY 4.0 (confirmed via the Zenodo API).
- **What it has:** mainland Portugal, per-fire records (`fogos.gpkg`,
  942.7 MB) with total burned area (`AREATOTAL`) and a burned-area class
  (`CLASSEAREA`) per fire, alert/intervention/resolution timestamps,
  cause, location down to parish, and per-fire physical/weather covariates
  (slope, road density, FWI/DC/DMC/ISI/BUI indices, wind, temperature,
  humidity, rate of spread). Also `PBA.gpkg` (251 MB, burned-area
  perimeters, 1975-2025), `METEO.csv` (1.2 GB, hourly weather during
  active fires), `FRP.csv` (32 MB, fire radiative power, 2004-2024).
- **Why this matters:** it directly answers the PRD's open question
  ("source that drives frequency: ICNF or EFFIS?") and would let the
  record reach the PRD's target 1980 start, with every fire size (so
  "large fire" becomes a modeling choice on `AREATOTAL`, not a side-effect
  of which satellite product mapped a given year, as with the EFFIS
  MODIS/Sentinel-2 split found earlier).
- **Not integrated. Flagged for a decision, not done automatically:**
  the main file is a 942.7 MB GeoPackage (a SQLite database with a
  geometry column). Its attribute table is likely readable with the
  standard library's `sqlite3` plus pandas, without geopandas, since only
  `AREATOTAL`/dates/location are needed and the geometry blob can be
  ignored - but this is unverified, the file is large to download, and
  swapping or supplementing the primary frequency/severity source this
  late in Phase 1 is a real scope decision, not a mechanical fix. Left for
  Dan to decide whether to pursue for Phase 2, and if so, whether as a
  replacement for EFFIS, a from-1980 frequency-only extension, or an
  independent cross-check alongside it.

## Loss-column conflict: resolved (Sept 2026)

Resolved the tension flagged earlier between the revised PRD's "loss
filled only where a sourced figure exists" and the per-fire CSV schema.

- No source publishes loss at the per-fire grain the schema uses; only
  annual/event aggregates exist, and only 2017 sits inside the
  mainland/2009-2025 window (see `data/raw/loss_anchors.csv`). Filling
  "only where sourced" at that grain would leave the column almost
  entirely empty and break Phase 2 (severity fit) and Phase 3
  (simulation), both of which need a populated per-fire loss.
- **Resolution:** every row keeps its modeled value (area x central
  EUR/ha, as before), and a new `Loss_Source` column labels every value
  `"modeled (area x central EUR/ha)"`, so a modeled figure is never
  presented as if it were observed. The PRD's actual intent - checking
  modeled loss against sourced figures - is met at the annual level, which
  is already where sourced figures exist (the 2017 official-total check
  and the 2024 component-floor check, both in the notebook).

## Phase 1 checkpoint decisions confirmed (Sept 2026)

Per the revised PRD's open questions and Week 2 checklist ("event
definition and loss type agreed"):

- **Loss type: direct economic damage.** This was the working assumption
  throughout Phase 1 and is now confirmed. Every anchor used (EUSF total,
  AGIF forest-sector loss) measures this, not insured loss, which the PRD
  itself notes is a small share of total damage (APS 2017 insured ~EUR
  250m against a ~EUR 1,458m official total, ~17%).
- **Event definition: mainland, >= 30 ha, applied uniformly.** Confirmed
  (re-tested at 100 ha; see the Phase 1 close-out entry above).
- **Backtest hold-out: 2021-2025 (5 years), train on 2009-2020 (12
  years).** Confirmed. This keeps 2017 (the main severity-tail anchor) in
  training, and the hold-out contains a mix of quiet years (2021, 2023) and
  severe ones (2022, 2024, and 2025, the second-largest year in the
  record), so it does not test only one kind of year.

## Kit data-summary handover (Sept 2026)

Per the revised PRD's Week 2 handover ("cleaned data CSV and data summary
document"), wrote `docs/phase1-data-summary.md`: a short, Kit-facing note
separate from the full write-up, covering what to sanity-check and what
questions are still open for Kit's review, per the PRD's "Domain
validation (Kit)" success criteria.

## Open items

- Phases 2-4 (distribution fitting, Monte Carlo, validation) haven't
  started yet.
- The residual 2020-2024 area-ratio divergence (~112% vs GWIS after the 30 ha filter) is still an open question.
- No published total economic loss for 2023/2024 found: decide what benchmark the PRD's "within ~20%" domain-validation test uses (Kit). Also look up published 2025 loss figures.
- Revisit the fire-day event definition (multi-day windows, hours-clause style) and its sensitivity, esp. the 2017-10-15 cluster.
- Decide whether to integrate the ICNF PRDF (Zenodo) dataset for Phase 2 - as a replacement for EFFIS, a from-1980 extension, or a cross-check (Dan).
- Verify the PRDF GeoPackage's attribute table is readable via sqlite3 without geopandas before committing to using it.
