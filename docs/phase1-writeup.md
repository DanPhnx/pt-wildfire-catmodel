# Data & EDA

**Phase 1 of 5** - Data sourcing & exploratory analysis - Portugal, 2010-2024 - Status: complete

A parametric catastrophe loss model for Portuguese wildfires. This note covers how the underlying data was actually sourced, a scope decision made along the way, and what stress-testing that data against an independent source turned up.

(A polished version of this note with interactive charts is at [`docs/phase1-writeup.html`](phase1-writeup.html).)

## Why this exists

The end goal is a full frequency-severity catastrophe model: a Poisson process for how often large wildfires occur, a Lognormal/Pareto fit for how big they get, and a Monte Carlo engine tying the two together into portfolio-level risk metrics (VaR, Expected Shortfall) in the style of reinsurance pricing work. None of that is credible without a real, defensible data foundation underneath it, which is what Phase 1 was for.

## Sourcing real data

EFFIS (the European Forest Fire Information System) is the obvious place to start, but its public Statistics Portal turned out to be a JavaScript single-page app with no accessible API behind it. A live, scriptable substitute was found instead: **Our World in Data** mirrors GWIS (the Global Wildfire Information System, run by the same JRC/Copernicus programme as EFFIS) as plain CSV, which gave real annual fire-count and burnt-area series with no authentication needed.

That covers annual totals, but not individual fires. For that, EFFIS's own **Data Request Form** was submitted (a one-time manual request, not an API), asking for the "Burnt area mapped using Sentinel-2/MODIS images" product for Portugal, 2010-2024. It came back with EFFIS's real Rapid Damage Assessment database: 6,608 individual fire records, **6,485 after cleaning** (48 Madeira and Azores records, 40 with non-physical area, and 35 duplicate copies removed), each with a real date, a real region, and a real burned area in hectares. **3,263 of those are mainland fires of at least 30 ha and form the model dataset**, for the reason in the next section.

## Scope decision

The model covers **mainland Portugal only**; Madeira and the Azores behave differently and are excluded.

EFFIS's documentation says its Rapid Damage Assessment maps fires of roughly **30 hectares or larger**, which still accounts for an estimated 75-80% of total burnt area despite being a minority of fire count. That holds for 2010-2018 (MODIS, smallest mapped fire 12-24 ha), but **not for the whole export**: the mapping source switches to Sentinel-2 from 2019, the smallest mapped fire drops to 1 ha, and 63-82% of 2020-2024 records are under 30 ha (versus 1.5-9% in 2010-2018). Left unfiltered, mean annual counts jump from ~246 to ~804 for a sensor reason, not a hazard reason.

So a "fire event" here is defined explicitly: **a mapped mainland fire of at least 30 ha, applied uniformly to every year.** That keeps 3,263 events and 98.2% of the mapped area.

> **Rationale.** For a catastrophe model built around tail risk (VaR, Expected Shortfall), the fires below that threshold don't move the numbers that matter. A consistent threshold matters more than counting every small fire: without it, the frequency series has a structural break in 2019-2020 that would corrupt distribution fitting and any backtest that holds out the last five years.

> **Correction.** An earlier version of this note treated the whole export as a 30 ha+ dataset, read the post-2020 count rise as "more, smaller large fires", and attributed a count discrepancy against OWID to MODIS-vs-VIIRS methodology; all three were consequences of the unfiltered Sentinel-2 records. It also included 28 Madeira records (1.9% of area), compared an all-Portugal total with AGIF's mainland figure, and described "69 duplicates" when 35 redundant copies were removed (69 rows sit in duplicate sets). Everything below is recomputed on the corrected data.

## What the data shows

Fifteen years of real large-fire activity in Portugal is not a smooth series. 2017 is the outlier every Portuguese wildfire dataset has to reckon with; less obviously, **2023 was unusually quiet for Portugal specifically** even though it was a severe wildfire year across the EU as a whole, while 2024 (Madeira, and a large mainland fire in Centro) was comparatively severe again.

**Annual burnt area, mainland fires of 30 ha or more (hectares):**

| Year | Burnt area (ha) | Fire count |
|------|-----------------:|------------------:|
| 2010 | 120,693 | 290 |
| 2011 | 64,442 | 303 |
| 2012 | 95,379 | 223 |
| 2013 | 153,408 | 326 |
| 2014 | 11,550 | 34 |
| 2015 | 47,286 | 169 |
| 2016 | 160,444 | 310 |
| 2017 | **562,348** | 405 |
| 2018 | 37,144 | 78 |
| 2019 | 33,181 | 168 |
| 2020 | 61,280 | 172 |
| 2021 | 25,855 | 187 |
| 2022 | 104,339 | 257 |
| 2023 | 31,053 | 162 |
| 2024 | 137,564 | 179 |

With a consistent threshold, counts show no upward trend (mean 231 per year in 2010-2019, 191 in 2020-2024). They are, however, **strongly overdispersed**: from 34 (2014) to 405 (2017) around a mean of ~218, a variance-to-mean ratio of ~44 where a Poisson process gives ~1. Phase 2 should expect a plain Poisson to fail goodness-of-fit and test a Negative Binomial.

Two further properties matter for the simulation, and both are visible in the data:

- **Bad years have both more and bigger fires.** Annual count vs median fire size has a Spearman rho of 0.58 (permutation p = 0.026, and it holds without 2017). A model drawing counts and sizes independently gives an annual-area SD of ~61k ha against ~134k ha observed, and essentially never produces a 2017-sized year.
- **Fires cluster in time.** On 15 October 2017, 33 polygons burned 196,476 ha; the largest single polygon that year is 67,521 ha. The top 10 fire-days hold 36% of all area. Grouping by start date gives 1,106 fire-day events: overdispersion falls to ~6 and the count-size correlation is no longer significant, but the annual-area SD is still ~1.85x the independent value, so a year-level severity factor is still needed.

Plan for Phases 2-3: model fire-day events, add a year-level severity factor, and cross-check against a whole-year bootstrap. The fire-day definition is a simple first choice and is flagged to revisit (multi-day windows, in the style of a treaty hours clause).

## Stress-testing the data

The live OWID/GWIS series wasn't dropped once the real per-fire data arrived; it was kept specifically as an independent check. That check surfaced two discrepancies, and chasing them is what exposed the sensor break above.

- **Count: resolved.** Unfiltered, EFFIS counts exceeded OWID's all-fire counts in some years (e.g. 2022: 1,204 vs 465). With the 30 ha filter the EFFIS count (257 in 2022) is below OWID's in **every** year with OWID data (0 of 13 exceed it).
- **Area: narrowed, not closed.** Summed EFFIS area first appeared to exceed GWIS's total in every year, averaging 116.6% in the first pass. That figure was itself misleading: an unweighted mean of yearly ratios over-counts small years.

| Statistic | Value |
|---|---:|
| Unweighted mean of yearly ratios, first pass (misleading) | ~~116.6%~~ |
| Total &divide; total, all 15 years, unfiltered | 104.1% |
| Total &divide; total, all 15 years, 30 ha filter | **102.2%** |
| 2010-2019, 30 ha filter | 100.7% |
| 2020-2024, 30 ha filter (unfiltered: 116.0%) | 108.1% |

The filter leaves 2010-2019 essentially unchanged and brings 2020-2024 from 116.0% to 108.1%: sub-30 ha fires explain about half of the recent-years excess, and an ~8% overshoot remains. It is not caused by the duplicate records (~104 ha in total). Candidate causes not yet checked: GWIS's most recent years being less finalized, Sentinel-2's 10 m burn-scar perimeters differing from 250 m MODIS, and whether GWIS's "Portugal" includes the islands (which would make the mainland ratio slightly understated). An overshoot of that size does not change the model's conclusions, so it is left as a documented open question.

## Loss calibration

No public source publishes verified EUR loss for an individual fire, and published totals for the same event differ widely with what they include (Pedrogao Grande 2017: a EUR 497m government estimate against ~EUR 200m of direct losses). So EUR/ha is carried as a **three-point range, not a calibrated constant**:

| Scenario | EUR / ha | Basis |
|---|---:|---|
| Low | 487 | 2024 forest-sector loss (EUR 67m, AGIF) / 137,667 ha. A component of loss, so a floor |
| Central | 1,923 | ICNF-derived 1975-2021 average (~EUR 10bn over ~5.2M ha), via OECD/press; 2017 is ~15% of its numerator |
| High | 2,593 | 2017 EU Solidarity Fund total direct damage (EUR 1,458m) / 562,348 ha mainland burnt area in this dataset |

Only **one official mainland total** sits inside the data window (2017), so the range is an assumption bracketed by evidence, not a calibration. Candidate anchors not used, and why, are in `data/raw/loss_anchors.csv`: Madeira 2016 (EUR 157m over 5,409 ha is ~EUR 29,000/ha, about 11x the mainland 2017 figure, unverified, and out of scope), and 2003 (>EUR 800m over ~425,000 ha, ~EUR 1,900/ha; a possible second anchor but both figures need verifying). The 2017 total is derived by arithmetic (0.832% of GNI against a EUR 1,051.6m threshold at 0.6%) from figures seen in search results; the primary document was not opened. Ordinary years have no anchor and are likely below the catastrophic-year values.

Three things follow, and none is hidden:

- **Modeled loss is burnt area times a constant** per scenario. The loss distribution has exactly the shape of the area distribution, and VaR/ES in euros are the area VaR/ES rescaled. It is best read as a burnt-area model with a euro scale.
- **The 2017 check is only partly independent.** The central scenario gives EUR 1,081m, 74% of the official EUR 1,458m. The central figure isn't calibrated to 2017, but 2017 is part of its numerator; the high scenario matches by construction.
- **2024 can be bracketed, not validated.** Mainland burnt area agrees with AGIF (137,564 ha vs 137,667 ha, 99.9%). For loss, the only published euro figures are components: forest-sector loss of EUR 67m and provisional insured claims above EUR 17m, together ~EUR 84m, against a central-scenario total of ~EUR 265m. No published total economic loss for 2023 or 2024 was found.

The benchmarks and their sources are in `data/raw/published_loss_benchmarks.csv`. The PRD's "within published range" criterion needs a defined benchmark before Phase 4.

## Limitations

- Mainland Portugal only; frequency and severity cover fires of at least 30 ha, applied uniformly to all years, a deliberate scope choice, not a hidden gap.
- Loss is derived from a EUR/ha range with a single official mainland anchor (2017), not observed per-fire, so the euro loss distribution is the burnt-area distribution rescaled.
- No published total economic loss was found for 2023 or 2024, so the loss level is bracketed by component figures rather than validated.
- An ~8% area overshoot versus GWIS in 2020-2024 remains unexplained (100.7% in 2010-2019).
- Annual counts are strongly overdispersed (variance/mean ~44), and count, fire size and same-day clustering are dependent, so a plain independent Poisson-lognormal model is unlikely to fit or to reproduce a 2017-sized year.
- Location is NUTS2-level only; no sub-regional or spatial modeling, by design.

## Next

Phase 2 fits the actual distributions (Poisson and Negative Binomial frequency, Lognormal/Pareto severity, with Kolmogorov-Smirnov and Anderson-Darling goodness-of-fit) against this real dataset.

---

github.com/DanPhnx/pt-wildfire-catmodel &middot; Dan &middot; September 2026
