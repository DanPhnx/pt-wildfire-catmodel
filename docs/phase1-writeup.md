# Data & EDA

**Phase 1 of 5** - Data sourcing & exploratory analysis - Portugal, 2010-2024 - Status: complete

A parametric catastrophe loss model for Portuguese wildfires. This note covers how the underlying data was actually sourced, a scope decision made along the way, and what stress-testing that data against an independent source turned up.

(A polished version of this note with interactive charts is at [`docs/phase1-writeup.html`](phase1-writeup.html).)

## Why this exists

The end goal is a full frequency-severity catastrophe model: a Poisson process for how often large wildfires occur, a Lognormal/Pareto fit for how big they get, and a Monte Carlo engine tying the two together into portfolio-level risk metrics (VaR, Expected Shortfall) in the style of reinsurance pricing work. None of that is credible without a real, defensible data foundation underneath it, which is what Phase 1 was for.

## Sourcing real data

EFFIS (the European Forest Fire Information System) is the obvious place to start, but its public Statistics Portal turned out to be a JavaScript single-page app with no accessible API behind it. A live, scriptable substitute was found instead: **Our World in Data** mirrors GWIS (the Global Wildfire Information System, run by the same JRC/Copernicus programme as EFFIS) as plain CSV, which gave real annual fire-count and burnt-area series with no authentication needed.

That covers annual totals, but not individual fires. For that, EFFIS's own **Data Request Form** was submitted (a one-time manual request, not an API), asking for the "Burnt area mapped using Sentinel-2/MODIS images" product for Portugal, 2010-2024. It came back with EFFIS's real Rapid Damage Assessment database: **6,533 usable individual fire records** after cleaning, each with a real date, a real region, and a real burned area in hectares.

## Scope decision

EFFIS's Rapid Damage Assessment only maps fires of roughly **30 hectares or larger**; by its own documentation, that subset still accounts for an estimated 75-80% of total burnt area despite being a minority of total fire count. Rather than patch that gap with a separate all-fires source, the model's frequency measure was defined to match: a "fire event" here means a mapped ~30ha+ fire, not every ignition in Portugal.

> **Rationale.** For a catastrophe model built around tail risk (VaR, Expected Shortfall), the fires below that threshold don't move the numbers that matter. Keeping frequency and severity drawn from the same real dataset was worth more than counting every small fire.

## What the data shows

Fifteen years of real large-fire activity in Portugal is not a smooth series. 2017 is the outlier every Portuguese wildfire dataset has to reckon with; less obviously, **2023 was unusually quiet for Portugal specifically** even though it was a severe wildfire year across the EU as a whole, while 2024 (Madeira, and a large mainland fire in Centro) was comparatively severe again.

**Annual burnt area, large fires only (hectares):**

| Year | Burnt area (ha) | Large-fire count |
|------|-----------------:|------------------:|
| 2010 | 127,932 | 307 |
| 2011 | 64,849  | 319 |
| 2012 | 101,342 | 239 |
| 2013 | 154,203 | 359 |
| 2014 | 11,574  | 35 |
| 2015 | 47,465  | 177 |
| 2016 | 166,096 | 322 |
| 2017 | **563,682** | 414 |
| 2018 | 37,356  | 86 |
| 2019 | 34,665  | 222 |
| 2020 | 65,786  | 465 |
| 2021 | 31,576  | 748 |
| 2022 | 111,993 | 1,210 |
| 2023 | 43,018  | 913 |
| 2024 | 147,588 | 717 |

Note counts climb sharply from 2021 even where area doesn't, i.e. more, smaller "large" fires in recent years.

## Stress-testing the data

The live OWID/GWIS series wasn't dropped once the real per-fire data arrived; it was kept specifically as an independent check. That check surfaced two real discrepancies, which were investigated rather than waved away.

- **Count:** real large-fire counts sometimes exceed OWID's all-fire counts in the same year (e.g. 2022). Explained: EFFIS maps burnt-area polygons from MODIS; OWID/GWIS counts VIIRS thermal-anomaly detections, a different sensor with a different definition of "one fire."
- **Area, and a statistics correction along the way:** summed large-fire area first appeared to exceed GWIS's total in every single year, averaging 116.6%, alarming if true. That figure was itself the problem: an unweighted mean of yearly ratios over-counts small years.

| Statistic | Value |
|---|---:|
| Unweighted mean of yearly ratios (misleading) | ~~116.6%~~ |
| Total &divide; total, all 15 years (correct) | **106.1%** |

The correct comparison sums real large-fire area and GWIS's total separately across all fifteen years, then takes one ratio. 106% is a modest overshoot, well inside the normal disagreement range between independent satellite burnt-area products.

Two things came out of digging further. First, a real and separate defect: **69 rows** in the raw export were exact duplicates, same parish, area, and timestamp under a different id, all tiny fires, concentrated in 2021-2024. Confirmed and deduplicated (~104 ha of the 1.71M ha total, immaterial to the model, but worth fixing since it was a genuine artifact rather than a methodology gap). Second, a pattern that remains genuinely open: a three-year rolling view shows ~92-108% agreement through 2012-2019, rising to ~114-134% for 2020-2024. The duplicate rows were ruled out as the cause. Left as an open question rather than forced to a tidy answer.

## Loss calibration

No public source publishes verified EUR loss for an individual fire; only annual or period aggregates from ICNF, OECD, and press reporting. A single documented calibration constant converts burnt area to euros:

| Basis | EUR / ha | Source |
|---|---:|---|
| Long-run average, 1975-2021 | 1,923 | ICNF cumulative burnt area & losses |
| 2017 season (for comparison) | 2,865 | Implied by reported 2017 losses vs. burnt area |

That gap between the two rows is itself the headline limitation: real losses aren't linear in area. A wildland-urban-interface fire like 2017 costs far more per hectare than a remote forest fire, because fatalities and structures dominate, not hectares. The 1,923 EUR/ha figure is applied uniformly for now, with that caveat stated plainly rather than hidden.

Sense-checked anyway: the model's 2017 total comes out around **&euro;1.08bn** against published estimates of roughly **&euro;1.5bn** for that season: same order of magnitude, in the direction the calibration gap above would predict.

## Limitations

- Frequency and severity cover fires &ge;~30ha only, a deliberate scope choice, not a hidden gap.
- Loss is derived from a single EUR/ha constant, not observed per-fire.
- The 2020-2024 area cross-validation pattern is unexplained.
- Location is NUTS2-level only; no sub-regional or spatial modeling, by design.

## Next

Phase 2 fits the actual distributions (Poisson frequency, Lognormal/Pareto severity, with Kolmogorov-Smirnov and Anderson-Darling goodness-of-fit) against this real dataset.

---

github.com/DanPhnx/pt-wildfire-catmodel &middot; Dan &middot; September 2026
