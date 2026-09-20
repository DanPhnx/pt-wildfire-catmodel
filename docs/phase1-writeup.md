# Data & EDA

**Phase 1 of 5** - Data sourcing & exploratory analysis - Portugal, 2010-2024 - Status: complete

A parametric catastrophe loss model for Portuguese wildfires. This note covers how the underlying data was actually sourced, a scope decision made along the way, and what stress-testing that data against an independent source turned up.

(A polished version of this note with interactive charts is at [`docs/phase1-writeup.html`](phase1-writeup.html).)

## Why this exists

The end goal is a full frequency-severity catastrophe model: a Poisson process for how often large wildfires occur, a Lognormal/Pareto fit for how big they get, and a Monte Carlo engine tying the two together into portfolio-level risk metrics (VaR, Expected Shortfall) in the style of reinsurance pricing work. None of that is credible without a real, defensible data foundation underneath it, which is what Phase 1 was for.

## Sourcing real data

EFFIS (the European Forest Fire Information System) is the obvious place to start, but its public Statistics Portal turned out to be a JavaScript single-page app with no accessible API behind it. A live, scriptable substitute was found instead: **Our World in Data** mirrors GWIS (the Global Wildfire Information System, run by the same JRC/Copernicus programme as EFFIS) as plain CSV, which gave real annual fire-count and burnt-area series with no authentication needed.

That covers annual totals, but not individual fires. For that, EFFIS's own **Data Request Form** was submitted (a one-time manual request, not an API), asking for the "Burnt area mapped using Sentinel-2/MODIS images" product for Portugal, 2010-2024. It came back with EFFIS's real Rapid Damage Assessment database: 6,608 individual fire records, **6,533 after cleaning**, each with a real date, a real region, and a real burned area in hectares. **3,291 of those are at or above 30 ha and form the model dataset**, for the reason in the next section.

## Scope decision

EFFIS's documentation says its Rapid Damage Assessment maps fires of roughly **30 hectares or larger**, which still accounts for an estimated 75-80% of total burnt area despite being a minority of fire count. That holds for 2010-2018 (MODIS, smallest mapped fire 12-24 ha), but **not for the whole export**: the mapping source switches to Sentinel-2 from 2019, the smallest mapped fire drops to 1 ha, and 62-82% of 2020-2024 records are under 30 ha (versus 1-9% in 2010-2018). Left unfiltered, mean annual counts jump from ~248 to ~811 for a sensor reason, not a hazard reason.

So a "fire event" here is defined explicitly: **a mapped fire of at least 30 ha, applied uniformly to every year.** That keeps 3,291 events and 98.2% of the mapped area.

> **Rationale.** For a catastrophe model built around tail risk (VaR, Expected Shortfall), the fires below that threshold don't move the numbers that matter. A consistent threshold matters more than counting every small fire: without it, the frequency series has a structural break in 2019-2020 that would corrupt distribution fitting and any backtest that holds out the last five years.

> **Correction.** An earlier version of this note treated the whole export as a 30 ha+ dataset, read the post-2020 count rise as "more, smaller large fires", and attributed a count discrepancy against OWID to MODIS-vs-VIIRS methodology. All three were consequences of the unfiltered Sentinel-2 records. The tables and findings below are recomputed on the filtered data.

## What the data shows

Fifteen years of real large-fire activity in Portugal is not a smooth series. 2017 is the outlier every Portuguese wildfire dataset has to reckon with; less obviously, **2023 was unusually quiet for Portugal specifically** even though it was a severe wildfire year across the EU as a whole, while 2024 (Madeira, and a large mainland fire in Centro) was comparatively severe again.

**Annual burnt area, fires of 30 ha or more (hectares):**

| Year | Burnt area (ha) | Fire count |
|------|-----------------:|------------------:|
| 2010 | 127,560 | 292 |
| 2011 | 64,442  | 303 |
| 2012 | 101,053 | 227 |
| 2013 | 153,408 | 326 |
| 2014 | 11,550  | 34 |
| 2015 | 47,286  | 169 |
| 2016 | 165,853 | 312 |
| 2017 | **563,530** | 408 |
| 2018 | 37,144  | 78 |
| 2019 | 33,451  | 172 |
| 2020 | 62,557  | 175 |
| 2021 | 25,855  | 187 |
| 2022 | 104,379 | 258 |
| 2023 | 36,855  | 168 |
| 2024 | 143,684 | 182 |

With a consistent threshold, counts show no upward trend (mean 232 per year in 2010-2019, 194 in 2020-2024). They are, however, **strongly overdispersed**: from 34 (2014) to 408 (2017) around a mean of ~219, a variance-to-mean ratio of ~44 where a Poisson process gives ~1. Phase 2 should expect a plain Poisson to fail goodness-of-fit and test a Negative Binomial.

## Stress-testing the data

The live OWID/GWIS series wasn't dropped once the real per-fire data arrived; it was kept specifically as an independent check. That check surfaced two discrepancies, and chasing them is what exposed the sensor break above.

- **Count: resolved.** Unfiltered, EFFIS counts exceeded OWID's all-fire counts in some years (e.g. 2022: 1,210 vs 465). With the 30 ha filter the EFFIS count is below OWID's in **every** year with OWID data (0 of 13 exceed it).
- **Area: narrowed, not closed.** Summed EFFIS area first appeared to exceed GWIS's total in every year, averaging 116.6%. That figure was itself misleading: an unweighted mean of yearly ratios over-counts small years.

| Statistic | Value |
|---|---:|
| Unweighted mean of yearly ratios (misleading) | ~~116.6%~~ |
| Total &divide; total, all 15 years, unfiltered | 106.1% |
| Total &divide; total, all 15 years, 30 ha filter | **104.2%** |
| 2010-2019, 30 ha filter | 102.2% |
| 2020-2024, 30 ha filter (unfiltered: 120.0%) | 112.0% |

The filter leaves 2010-2019 essentially unchanged but only brings 2020-2024 from ~120% down to ~112%: sub-30 ha fires explain part of the recent-years excess, not all of it. The remainder is unexplained. The 69 duplicate rows (tiny fires, ~104 ha, concentrated in 2021-2024) were a confirmed export artifact and are deduplicated, but are far too small to be the cause. Candidate causes not yet checked are GWIS's most recent years being less finalized, and Sentinel-2's 10 m burn-scar perimeters differing from 250 m MODIS. A ~12% overshoot in the last five years is small enough not to change the model's conclusions, so it is left as a documented open question.

## Loss calibration

No public source publishes verified EUR loss for an individual fire; only annual or period aggregates from ICNF, OECD, and press reporting. A single documented calibration constant converts burnt area to euros:

| Basis | EUR / ha | Source |
|---|---:|---|
| Long-run average, 1975-2021 | 1,923 | ICNF cumulative burnt area & losses |
| 2017 season (for comparison) | 2,865 | Implied by reported 2017 losses vs. burnt area |

That gap between the two rows is itself the headline limitation: real losses aren't linear in area. A wildland-urban-interface fire like 2017 costs far more per hectare than a remote forest fire, because fatalities and structures dominate, not hectares. The 1,923 EUR/ha figure is applied uniformly for now, with that caveat stated plainly rather than hidden.

Two things follow from that, and neither is hidden:

- **Modeled loss is burnt area times a constant.** The loss distribution has exactly the shape of the area distribution, and VaR/ES in euros are the area VaR/ES rescaled. That is acceptable for this scope, but it is best read as a burnt-area model with a euro scale.
- **External checks are weaker than they look.** 2024 burnt area agrees well with AGIF's national figure (143,684 ha vs 137,667 ha, +4%). For loss, the only published euro figures found are *components*: forest-sector loss of EUR 67m (forest only, excluding homes and infrastructure) and provisional insured claims above EUR 17m for the September fires, together ~EUR 84m against a modeled 2024 total of ~EUR 276m. That is a bracket, not a validation: no published *total* economic loss for 2023 or 2024 was found. The 2017 comparison (modeled EUR 1.08bn vs ~EUR 1.5bn reported) is not independent, since it just restates the calibration gap in the table above.

The benchmarks and their sources are in `data/raw/published_loss_benchmarks.csv`. The PRD's "within ~20% of published reports" criterion needs a defined benchmark before Phase 4.

## Limitations

- Frequency and severity cover fires of at least 30 ha only, applied uniformly to all years, a deliberate scope choice, not a hidden gap.
- Loss is derived from a single EUR/ha constant, not observed per-fire, so the euro loss distribution is the burnt-area distribution rescaled.
- No published total economic loss was found for 2023 or 2024, so the loss level is bracketed by component figures rather than validated.
- A ~12% area overshoot versus GWIS in 2020-2024 remains unexplained (102% in 2010-2019).
- Annual counts are strongly overdispersed (variance/mean ~44), so a plain Poisson is unlikely to fit.
- Location is NUTS2-level only; no sub-regional or spatial modeling, by design.

## Next

Phase 2 fits the actual distributions (Poisson and Negative Binomial frequency, Lognormal/Pareto severity, with Kolmogorov-Smirnov and Anderson-Darling goodness-of-fit) against this real dataset.

---

github.com/DanPhnx/pt-wildfire-catmodel &middot; Dan &middot; September 2026
