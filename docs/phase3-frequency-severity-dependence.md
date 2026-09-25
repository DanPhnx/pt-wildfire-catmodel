# Phase 3 PRD addendum: frequency-severity dependence and tail stability

**Status: proposal, not yet implemented.** This is a proposed update to the
PRD's Phase 3 Technical Decisions, written by Dan (with Claude Code) for Dan
and Kit to fold into the actual PRD if agreed — it is not an official Kit
revision. It narrowly targets one open item flagged at the end of Phase 2
(`docs/worklog.md`, "Open items"): how Phase 3's Monte Carlo engine should
handle the frequency-severity dependence Phase 1 and 2 found, given the PRD
says only:

> **Phase 3: Simulation and metrics (Weeks 3-4)**
> Monte Carlo engine: annual fire count, then burned area per fire, then euro
> loss, then annual total; 100,000 years, fixed seed
>
> Technical Decisions | Simulation | 100,000 years, fixed random seed |
> 10,000 runs is noisy at VaR(99)
>
> Success Criteria | Convergence: standard error on VaR(95%) is below 2% at
> the chosen number of runs. VaR(99%) is reported separately, as it is
> noisier.

Everything below is backed by an executed numerical prototype (not asserted
figures); the code is in this branch's worklog entry and will become
`monte_carlo.py` proper during implementation.

## Why we need to fix

Two distinct problems, found in that order while building the prototype.

**1. The independent model has an unstable, effectively infinite-variance
tail.** The fitted GPD tail (`models/pareto_tail.json`, shape ξ = 0.746) is
already flagged in Phase 2 as "heavy — expected for a catastrophe model." What
wasn't tested until now is what that does to a 100,000-year simulation: a GPD
has finite variance only for ξ < 0.5. Ours doesn't, so simulated annual
losses don't converge — they're dominated by rare, occasionally
non-physical single fire-day draws.

Running the *independent* engine (no dependence, no frailty — just fitted
Negative Binomial count × fitted Lognormal/GPD severity) 8 times with
different seeds:

| Seed | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| Annual-loss SD (ha) | 598,526 | 400,101 | 837,052 | 927,695 | 548,185 | 648,403 | 467,861 | 1,064,317 |

No convergence at all — this is exactly what the PRD's "SE(VaR95%) < 2%"
criterion is there to catch. The cause: 0.62% of raw GPD tail draws exceed
the worst fire-day ever recorded (196,476 ha, 2017-10-15), and the single
largest draw across the test run was **75.7 million ha** — over 8× the
entire land area of mainland Portugal. This has nothing to do with
frequency-severity dependence; it would exist even with a perfectly
independent model, and must be fixed before dependence can be assessed at
all.

**2. Once the tail is stabilized, the independent model does understate the
observed annual variance — but by less, and less dramatically, than the
`docs/worklog.md` open item's "~1.8x" figure suggested.** That figure
compared *observed* history to a *nonparametric bootstrap of observed
history* (drawing counts and areas from the actual historical arrays), which
can never exceed what's already been seen and so is guaranteed to
understate a model meant to extrapolate. The right comparison is observed
history vs. the *fitted parametric model* run independently — done here
for the first time. With the tail capped for stability (see below), the
independent model gives annual SD ≈ 137,000 ha against a true training-period
(2009–2020) observed SD of **147,411 ha** — a real but modest ~7% gap, not
a factor of 1.8–1.9. It's still evidence of genuine residual dependence
(Phase 1's rho = 0.57, p = 0.019 between annual count and median fire size,
and the same-day clustering finding), just smaller than first estimated.

## How we will fix

Two changes to the Monte Carlo engine, in this order:

**1. Cap simulated severity at two levels — a physical ceiling and a
practical simulation bound.**

- *Physical ceiling: 6.1 million ha.* Per ICNF's 6th National Forest
  Inventory (IFN6, 2015 survey data, published June 2019), mainland
  Portugal's forest, shrubland, and unproductive land — the land classes
  that can actually burn — total 6.1 million ha (69.4% of the 8.91 million
  ha mainland). A single fire-day cannot physically exceed this; it's
  hard-coded as an absolute backstop and is not expected to bind in
  practice.
- *Practical simulation bound: 5× the historical maximum fire-day
  (982,380 ha, vs. the observed record of 196,476 ha).* The physical
  ceiling alone doesn't stabilize the simulation (cross-seed SD still
  ranges 221,000–266,000 ha at that cap — a legitimate hard limit, but too
  loose to converge). 5× the historical record does: cross-seed SD lands
  at 135,000 ± 3,500 ha (a ~2.6% range, in line with the PRD's convergence
  target), while still letting the model generate fire-days well beyond
  anything on record, which is the actual point of fitting an EVT tail.

**2. A year-level frailty factor (Option A, as agreed).** A lognormal
multiplicative factor *Z* per simulated year (mean 1, calibrated spread
σ_z), applied to every fire-day severity draw that year, linked to that
year's simulated count via a Gaussian copula (correlation ρ). High ρ makes
high-count years also tend to be high-severity years, reproducing Phase 1's
count/median-size correlation; σ_z alone reproduces the annual-variance
gap even at ρ = 0.

## Results of fixing (prototype, verified — not yet the production run)

With the cap in place, sweeping σ_z at ρ = 0:

| σ_z | 0.00 | 0.10 | 0.15 | 0.20 | 0.25 | 0.30 |
|---|---|---|---|---|---|---|
| Mean simulated annual SD (ha) | 137,463 | 139,054 | 141,131 | 144,050 | **147,801** | 152,372 |
| Ratio to observed target (147,411 ha) | 0.933x | 0.943x | 0.957x | 0.977x | **1.003x** | 1.034x |

**σ_z ≈ 0.25 at ρ = 0 reproduces the observed annual variance almost
exactly** — a modest, well-behaved calibration (nowhere near as large as a
frailty factor calibrated against the flawed 1.8x figure would have needed
to be), and stable across seeds (±~8,000 ha at this setting).

That calibration alone reproduces none of the count/severity rank
correlation (simulated Spearman ≈ 0 at ρ = 0, vs. the observed 0.57). Adding
ρ > 0 does add it back, but a first grid search over σ_z ∈ [0.05, 0.30] and
ρ ∈ [0.0, 0.7] shows the two targets pull against each other: the
combination that best balances both in the searched range (σ_z = 0.30,
ρ = 0.70) reaches Spearman ≈ 0.50 but overshoots the variance target
(SD ≈ 177,000–181,000 ha, ~1.2–1.3x). This needs a proper joint
calibration — a finer grid or a direct optimizer over both parameters
together, checked against the 2021–2025 hold-out — which is implementation
work, not planning work, and is deferred to when `monte_carlo.py` is
actually built.

**What this proposal does and doesn't establish:**

- Confirms the tail-stability problem is real, quantified, and fixable with
  a documented, sourced cap (not an arbitrary number).
- Confirms the frailty mechanism (Option A) works and gives a validated
  starting point (σ_z ≈ 0.25–0.30, ρ ≈ 0–0.7, final values to be fixed by a
  formal joint calibration during implementation).
- Does **not** yet include: integration into `monte_carlo.py`/
  `03_monte_carlo.ipynb`, the euro-loss conversion step, the actual
  100,000-year/fixed-seed production run, the PRD's convergence check
  (repeated-run SE on VaR(95%) and VaR(99%)), or hold-out validation. Those
  are Phase 3 implementation, tracked separately.

**Proposed PRD Technical Decisions addendum**, alongside the existing
"Simulation" row:

| Decision | Choice | Why |
|---|---|---|
| Severity tail cap | 5× historical max fire-day (982,380 ha) as the working simulation bound; ICNF's 6.1M ha mainland burnable-land figure as an absolute physical backstop | The fitted GPD tail (ξ = 0.746) has infinite theoretical variance; uncapped, the simulation doesn't converge and can generate non-physical single-day losses |
| Frequency-severity dependence | Year-level lognormal frailty factor (mean 1, σ_z calibrated), linked to the annual count draw via a Gaussian copula (ρ calibrated) | Reproduces the observed annual-variance gap and the count/median-severity correlation (ρ_Spearman = 0.57, p = 0.019) that an independent model misses |
