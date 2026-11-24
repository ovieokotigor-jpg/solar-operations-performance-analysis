# Solar Operations: Energy Yield, Downtime and Cleaning

**SQL · Python · Synthetic engineering data · Explanatory analytics**

## Business question
Which sites and inverter arrays deserve maintenance or cleaning investigation after accounting for differences in solar resource and installed capacity?

HelioWorks is a fictional operator of six sites with 24 inverter/array assets. This project supports an operations manager deciding where to investigate low yield, schedule field reviews and improve telemetry. It connects mechanical/energy engineering judgment with data analysis.

All data is synthetic, generated with seed 314159. Dates cover 1 January 2024–31 December 2025. Climate labels are scenario groups, not measured site locations. Parameters and costs are assumptions, not calibrated Nigerian solar benchmarks.

## Executive findings
- Observed AC generation: **15,559.4 MWh**. This is incomplete observed energy, not a full-fleet estimate.
- Energy telemetry coverage: **98.44%** of all **17,544 expected asset-days**.
- Matched performance index: **94.33%** of the clean-array, full-availability reference.
- Lowest asset index: **Asset 19 (91.91%)**; review its outage history and operating context.
- Lowest site index: **HelioWorks Site 4 (93.39%)**; capacity and irradiance are normalized, but age, cleaning and other operating differences remain.
- Modelled downtime-associated gap: **404.3 MWh** on matched records. This is a scenario-model estimate, not proven recoverable energy.

## Data and relationships
Five raw CSVs: sites (6 rows), assets (24), weather (4,386 site-days), readings (17,664 rows including duplicates) and events (1,232 daily event segments). One clean reading represents one asset-day. Assets belong to sites; readings reference assets and weather; events reference assets and dates. Weather is shared by the site's four assets. There is at most one event segment per asset-day. Multi-day faults span multiple segments, not multiple independent failures.

| Prepared table | Rows |
|---|---:|
| sites | 6 |
| assets | 24 |
| weather | 4,386 |
| readings | 17,504 |
| events | 1,232 |
| quarantine | 40 |
| daily_mart | 17,544 |

See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for every field and unit.

## How realism is introduced
Daily solar irradiation varies by climate scenario, season, rainfall, common daily weather and site-specific noise. Shared grid outages affect all arrays at a site. Asset faults can persist across days. Asset 19 deliberately has higher fault probability. Soiling accumulates faster in dry months, heavy rain partly washes it off, and manual cleaning resets it. Cleaning is deferred during faults and grid outages. Capacity, temperature, fixed conversion losses, age and availability influence output. Sites have different cleaning intervals. Correlated missingness is more likely during heavy rain.

The design is a simplified daily energy model, **not PVWatts or an engineering yield guarantee**. It uses a fixed 12-hour daylight window, no hourly clipping physics, no battery, no dispatch/curtailment model and no GPS or measured weather. Input distributions are not uniformly random. Natural extremes such as genuine zero-output days are preserved.

## SQL workflow and quality audit
`pipeline.py` imports all fields into text staging tables and rejects malformed numeric strings before casting. `sql/01_clean.sql` standardizes dates/status, casts numeric fields while retaining NULLs, removes identical duplicates, quarantines invalid values/references and builds an expected asset-day grid. Clean tables use unique indexes. The SQL remains visible and reviewable rather than hidden inside Python data cleaning.

**Reconciliation:** 17,664 raw rows − 120 duplicates − 40 quarantined records = 17,504 retained readings. Deliberate faults: 20 negative readings, 10 unknown assets, 10 above-capacity readings, 150 mixed dates and 200 inconsistent statuses. Some source faults overlap with missing sensor data. Null energy is not zero energy.

The expected grid contains 17,544 rows even when a reading is rejected. Coverage therefore includes those rejected or missing observations in the denominator. `sql/03_validation.sql` checks references, temporal logic, status labels, event-hours reconciliation, zero-hour energy, grid size and raw-row reconciliation. Raw and rejected records remain available for review.

## Definitions and methodology
- Observed energy sums available readings; never extrapolate silently to missing days.
- Reference kWh = DC kWp × daily POA irradiation / reference irradiance of 1 kW/m² × temperature factor × conversion efficiency × 0.97 assumed balance-of-system factor.
- Performance index = 100 × SUM(measured energy) / SUM(reference energy), using the same matched records for both sums. It is not a standard temperature-uncorrected performance ratio.
- Availability = mean operating hours / 12 on retained records; it is time-based, not energy-weighted. Missing/quarantined operating hours are excluded and should be interpreted with coverage.
- Modelled downtime gap = reference × unavailable daylight fraction. This assumes production is uniform across daylight hours, a simplifying approximation.
- Residual gap = available-hours reference − measured output. It includes soiling, degradation and noise. It cannot be called avoidable soiling loss.
- Both gap terms reconcile algebraically to reference minus measured energy on matched observations. That does not validate the reference model against a real plant.
- Event costs are reported separately from the full event ledger; joining events to incomplete energy data must not reduce the cost total. No tariffs, revenue or savings claims are made.

## Analytical SQL
`sql/02_analysis.sql` includes eight queries: monthly output, site performance, asset performance, site-month patterns, event hours/costs, weather-linked telemetry coverage, cleaning-age profiles and the reference-to-output gap bridge. Results are exported to reports/.

## Explanatory visuals

### Separate weather exposure from operating performance
![Separate weather exposure from operating performance](charts/01_seasonal_output.png)
Both energy curves use matched records. The reference is a simplified scenario model, not a production forecast.

### Locate recurring performance pressure
![Locate recurring performance pressure](charts/02_site_month_heatmap.png)
Each cell: performance index, then matched asset-days. Four arrays per site; missing records excluded from index.

### Explain the reference-to-output gap
![Explain the reference-to-output gap](charts/03_energy_gap_waterfall.png)
Matched records only. Residual includes soiling, age and noise; downtime estimate assumes uniform daylight production.

### Prioritise equipment reviews using two measures
![Prioritise equipment reviews using two measures](charts/04_asset_priority_matrix.png)
Bubble area represents DC capacity. Availability uses retained hours, including rows with missing energy.

### Cleaning-age patterns vary with climate scenario
![Cleaning-age patterns vary with climate scenario](charts/05_cleaning_age_profile.png)
Full-availability days, bins with at least 30 records. Rain, season and asset age confound this association.

### Inspect the output distribution, not just averages
![Inspect the output distribution, not just averages](charts/06_irradiation_yield_hexbin.png)
Near-zero yield can be a genuine outage. Colour indicates density; all matched days are included.

### Weather changes which records are visible
![Weather changes which records are visible](charts/07_telemetry_coverage.png)
Missing readings remain missing. Reference coverage also needs irradiation and module temperature.

## Recommended actions
1. Review the weak asset's fault history, spare-parts needs and repeated outage segments; do not rank solely by raw MWh.
2. Compare dry-period cleaning options using matched peer arrays, labour/water costs and service constraints. The cleaning-age chart is observational, not a causal treatment estimate.
3. Investigate rainy-day telemetry outages. Improve coverage before extrapolating fleet performance.
4. Reconcile site grid outages separately from equipment faults so maintenance teams are not blamed for network interruptions.
5. On real data, validate the reference using calibrated weather, actual module specifications, hourly availability and uncertainty appropriate to shared site-day conditions.

## Reproduction
Python 3.10+ is required. SQLite is included with Python.

```bash
python -m pip install -r requirements.txt
python pipeline.py
```

Run commands from the extracted folder containing requirements.txt. On Windows you can double-click RUN_WINDOWS.bat, or replace python with py. Existing raw data is reused. To regenerate it explicitly: `python generate_data.py`. For EDA only: `python analysis/eda.py` after pipeline preparation. Generated README, charts and dashboard are overwritten on rerun; preserve personal edits separately.

## Files
| Path | Contents |
|---|---|
| data/raw/ | Five full synthetic source CSVs |
| data/clean/ | Clean data, quarantine and complete expected grid |
| sql/ | Staging, cleaning, analysis and validation SQL |
| analysis/eda.py | Full Python EDA and explanatory chart code |
| analysis/findings.md | Executive findings |
| charts/ | Seven PNG charts |
| dashboard/index.html | Self-contained offline dashboard, no server needed |
| reports/ | Query outputs, validation audit and environment versions |
| solar.sqlite | Ready-to-query database |
| DATA_DICTIONARY.md | Columns, units and definitions |

## GitHub publishing
Suggested repository: `solar-operations-performance-analysis`. Description: Synthetic solar operations analysis using SQL and Python to investigate energy yield, downtime, cleaning and telemetry quality. Initial commit: `Add complete solar operations analytics portfolio`.

Upload the extracted project's contents with README.md at the repository root. Include data, sql, analysis, charts, dashboard, reports and supporting scripts. Do not upload the ZIP, .venv or __pycache__. The README already includes calculated results and chart links.

## Limitations
Synthetic records demonstrate analytical practice; they do not prove real causal effects or expected savings. Fixed efficiency, daylight, daily weather, full-site grid interruptions and simple degradation are approximations. Rain and season influence cleaning age and output simultaneously. Shared site/day effects mean rows are not statistically independent; no significance claims are made. No inverter replacement, plant expansion, batteries, tariff contracts or maintenance optimisation is modeled. Missing data is deliberately not random, so complete-record performance can be biased.

## Technical context
The PVWatts documentation distinguishes temperature effects, system-loss categories and inverter conversion. This project uses those concepts for context only; its equations and parameter choices are an independent teaching simulation, not a PVWatts implementation.
- https://pvwatts.nlr.gov/docs/help_system_sysloss.php
- https://sam.nlr.gov/photovoltaic

## Skills demonstrated
Relational data modeling, engineering-aware simulation, SQL cleaning, audit reconciliation, coverage denominators, safe joins, exposure-normalized metrics, missing-data diagnostics, explanatory charts and clear operational recommendations.
