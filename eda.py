"""EDA and explanatory charts. Run from anywhere: python analysis/eda.py."""
from pathlib import Path
import sqlite3,json,base64,html
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parents[1]
BLUE='#174f68';GOLD='#d69d2c';RED='#bf5b50';BG='#fcfbf7'
plt.rcParams.update({'figure.facecolor':BG,'axes.facecolor':BG,'savefig.facecolor':BG,'font.family':'DejaVu Sans','font.size':10,'text.color':'#23394a','axes.labelcolor':'#23394a','axes.spines.top':False,'axes.spines.right':False})
charts=[]
def save(fig,file,title,note):
 fig.suptitle(title,x=.07,ha='left',fontsize=16,fontweight='bold');fig.text(.07,.025,note,fontsize=9,color='#617382');fig.tight_layout(rect=[.02,.07,.98,.91]);fig.savefig(P/'charts'/file,dpi=150);plt.close(fig);charts.append((file,title,note))
def read(n):return pd.read_csv(P/'reports'/f'{n}.csv')
c=sqlite3.connect(P/'solar.sqlite');d=pd.read_sql('SELECT * FROM daily_mart',c);c.close()
m=read('monthly');s=read('sites');a=read('assets');sm=read('site_month');ev=read('event_summary');cw=read('coverage_weather');age=read('cleaning_age');b=read('gap_bridge').iloc[0]
# Avoid dual-axis confusion: use aligned small multiples.
fig,ax=plt.subplots(2,1,figsize=(12,6),sharex=True);x=np.arange(24)
ax[0].plot(x,m.reference_mwh,color=GOLD,lw=2,label='Full-availability clean-array reference');ax[0].plot(x,m.matched_mwh,color=BLUE,lw=2,label='Measured, same records');ax[0].set_ylabel('MWh');ax[0].legend(frameon=False,fontsize=9)
ax[1].plot(x,m.performance_index,color=BLUE,lw=2);ax[1].set_ylabel('Performance index (%)');ax[1].set_xticks(x[::2],m.month[::2],rotation=30,ha='right')
save(fig,'01_seasonal_output.png','Separate weather exposure from operating performance','Both energy curves use matched records. The reference is a simplified scenario model, not a production forecast.')
# Calendar-like site-month heatmap with support shown.
v=sm.pivot(index='site_id',columns='month',values='performance_index');n=sm.pivot(index='site_id',columns='month',values='matched_days')
fig,ax=plt.subplots(figsize=(14,5));im=ax.imshow(v,cmap='YlGnBu',vmin=70,vmax=100,aspect='auto')
for i in range(6):
 for j in range(24):ax.text(j,i,f'{v.iloc[i,j]:.0f}\n{int(n.iloc[i,j])}',fontsize=7,ha='center',va='center',color='white' if v.iloc[i,j]>89 else '#23394a')
ax.set_yticks(range(6),[f'Site {i}' for i in v.index]);ax.set_xticks(range(24),v.columns,rotation=65,ha='right');fig.colorbar(im,ax=ax,label='Performance index (%)')
save(fig,'02_site_month_heatmap.png','Locate recurring performance pressure','Each cell: performance index, then matched asset-days. Four arrays per site; missing records excluded from index.')
# Signed gap decomposition, no claim that residual equals preventable soiling.
values=[b.reference_mwh,-b.modelled_outage_gap_mwh,-b.residual_gap_mwh];labels=['Reference','Modelled downtime gap','Residual gap','Measured'];total=0
fig,ax=plt.subplots(figsize=(11,5))
for i,val in enumerate(values):
 ax.bar(i,val,bottom=total,color=GOLD if i==0 else RED,width=.6);total+=val;ax.text(i,(total if val>0 else total-val)+220,f'{val:+,.1f}',ha='center')
ax.bar(3,b.measured_mwh,color=BLUE,width=.6);ax.text(3,b.measured_mwh+15,f'{b.measured_mwh:,.1f}',ha='center');ax.set_xticks(range(4),labels);ax.set_ylabel('MWh')
assert abs(total-b.measured_mwh)<1e-5
save(fig,'03_energy_gap_waterfall.png','Explain the reference-to-output gap','Matched records only. Residual includes soiling, age and noise; downtime estimate assumes uniform daylight production.')
# Decision matrix: gap versus availability, bubble area installed DC capacity.
cap=d.groupby('asset_id').dc_capacity_kwp.first();fig,ax=plt.subplots(figsize=(11,5));colors=[GOLD if i==19 else BLUE for i in a.asset_id]
ax.scatter(a.observed_availability,a.performance_index,s=[cap.loc[i]*1.2 for i in a.asset_id],c=colors,alpha=.75,edgecolor='white')
for _,r in a.nsmallest(4,'performance_index').iterrows():ax.annotate(f'Asset {int(r.asset_id)}',(r.observed_availability,r.performance_index),xytext=(7,-13),textcoords='offset points',fontsize=9)
ax.set_xlabel('Availability on retained daily readings (%)');ax.set_ylabel('Matched performance index (%)');ax.margins(.15)
save(fig,'04_asset_priority_matrix.png','Prioritise equipment reviews using two measures','Bubble area represents DC capacity. Availability uses retained hours, including rows with missing energy.')
# Reference normalization vs time since cleaning, weather/confounding explicit.
fig,ax=plt.subplots(figsize=(11,5))
for color,(region,g) in zip([BLUE,GOLD,RED],age.groupby('region')):
 g=g[g.matched_full_availability_days>=30];ax.plot(g.age_band+5,g.performance_index,'o-',color=color,label=region)
ax.set_xlabel('Days since manual cleaning (10-day bin midpoint)');ax.set_ylabel('Matched performance index (%)');ax.legend(frameon=False)
save(fig,'05_cleaning_age_profile.png','Cleaning-age patterns vary with climate scenario','Full-availability days, bins with at least 30 records. Rain, season and asset age confound this association.')
# Exposure shape beyond means; output normalized for capacity.
g=d[d.matched==1];fig,ax=plt.subplots(figsize=(10,5));im=ax.hexbin(g.poa_irradiation_kwh_m2,g.energy_kwh/g.dc_capacity_kwp,gridsize=38,mincnt=1,cmap='YlGnBu',bins='log');ax.set_xlabel('Daily plane-of-array irradiation (kWh/m²)');ax.set_ylabel('Specific AC yield (kWh/kWp)');fig.colorbar(im,ax=ax,label='Observation count (log colour scale)')
save(fig,'06_irradiation_yield_hexbin.png','Inspect the output distribution, not just averages','Near-zero yield can be a genuine outage. Colour indicates density; all matched days are included.')
# Coverage dumbbell.
fig,ax=plt.subplots(figsize=(10,4));y=np.arange(len(cw));ax.hlines(y,cw.matched_coverage,cw.energy_coverage,color='#b9c7ca',lw=5);ax.scatter(cw.energy_coverage,y,color=BLUE,s=95,label='Energy available');ax.scatter(cw.matched_coverage,y,color=GOLD,s=95,label='Energy + reference available')
for i,r in cw.iterrows():ax.text(r.energy_coverage+.2,i,f'{r.energy_coverage:.1f}%',va='center');ax.text(r.matched_coverage-.2,i,f'{r.matched_coverage:.1f}%',ha='right',va='center')
ax.set_yticks(y,cw.weather_band);ax.set_xlim(cw.matched_coverage.min()-4,101);ax.set_xlabel('Coverage of all expected asset-days (%)');ax.legend(frameon=False,loc='lower right')
save(fig,'07_telemetry_coverage.png','Weather changes which records are visible','Missing readings remain missing. Reference coverage also needs irradiation and module temperature.')
# Findings sourced from computed results, not hardcoded targets.
audit=json.loads((P/'reports/validation.json').read_text());coverage=100*d.energy_kwh.notna().mean();index=100*g.energy_kwh.sum()/g.reference_kwh.sum();weak=a.loc[a.performance_index.idxmin()];worst=s.loc[s.performance_index.idxmin()]
findings=f'''- Observed AC generation: **{d.energy_kwh.sum()/1000:,.1f} MWh**. This is incomplete observed energy, not a full-fleet estimate.
- Energy telemetry coverage: **{coverage:.2f}%** of all **{len(d):,} expected asset-days**.
- Matched performance index: **{index:.2f}%** of the clean-array, full-availability reference.
- Lowest asset index: **Asset {int(weak.asset_id)} ({weak.performance_index:.2f}%)**; review its outage history and operating context.
- Lowest site index: **{worst.site_name} ({worst.performance_index:.2f}%)**; capacity and irradiance are normalized, but age, cleaning and other operating differences remain.
- Modelled downtime-associated gap: **{b.modelled_outage_gap_mwh:,.1f} MWh** on matched records. This is a scenario-model estimate, not proven recoverable energy.
'''
counts='\n'.join(f'| {k} | {v:,} |' for k,v in audit['clean_counts'].items())
md=f'''# Solar Operations: Energy Yield, Downtime and Cleaning

**SQL · Python · Synthetic engineering data · Explanatory analytics**

## Business question
Which sites and inverter arrays deserve maintenance or cleaning investigation after accounting for differences in solar resource and installed capacity?

HelioWorks is a fictional operator of six sites with 24 inverter/array assets. This project supports an operations manager deciding where to investigate low yield, schedule field reviews and improve telemetry. It connects mechanical/energy engineering judgment with data analysis.

All data is synthetic, generated with seed 314159. Dates cover 1 January 2024–31 December 2025. Climate labels are scenario groups, not measured site locations. Parameters and costs are assumptions, not calibrated Nigerian solar benchmarks.

## Executive findings
{findings}
## Data and relationships
Five raw CSVs: sites (6 rows), assets (24), weather (4,386 site-days), readings ({audit['raw_readings']:,} rows including duplicates) and events ({audit['clean_counts']['events']:,} daily event segments). One clean reading represents one asset-day. Assets belong to sites; readings reference assets and weather; events reference assets and dates. Weather is shared by the site's four assets. There is at most one event segment per asset-day. Multi-day faults span multiple segments, not multiple independent failures.

| Prepared table | Rows |
|---|---:|
{counts}

See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for every field and unit.

## How realism is introduced
Daily solar irradiation varies by climate scenario, season, rainfall, common daily weather and site-specific noise. Shared grid outages affect all arrays at a site. Asset faults can persist across days. Asset 19 deliberately has higher fault probability. Soiling accumulates faster in dry months, heavy rain partly washes it off, and manual cleaning resets it. Cleaning is deferred during faults and grid outages. Capacity, temperature, fixed conversion losses, age and availability influence output. Sites have different cleaning intervals. Correlated missingness is more likely during heavy rain.

The design is a simplified daily energy model, **not PVWatts or an engineering yield guarantee**. It uses a fixed 12-hour daylight window, no hourly clipping physics, no battery, no dispatch/curtailment model and no GPS or measured weather. Input distributions are not uniformly random. Natural extremes such as genuine zero-output days are preserved.

## SQL workflow and quality audit
`pipeline.py` imports all fields into text staging tables and rejects malformed numeric strings before casting. `sql/01_clean.sql` standardizes dates/status, casts numeric fields while retaining NULLs, removes identical duplicates, quarantines invalid values/references and builds an expected asset-day grid. Clean tables use unique indexes. The SQL remains visible and reviewable rather than hidden inside Python data cleaning.

**Reconciliation:** {audit['raw_readings']:,} raw rows − 120 duplicates − {audit['clean_counts']['quarantine']} quarantined records = {audit['clean_counts']['readings']:,} retained readings. Deliberate faults: 20 negative readings, 10 unknown assets, 10 above-capacity readings, 150 mixed dates and 200 inconsistent statuses. Some source faults overlap with missing sensor data. Null energy is not zero energy.

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
'''
for file,title,note in charts:md+=f'\n### {title}\n![{title}](charts/{file})\n{note}\n'
md+='''
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
'''
(P/'README.md').write_text(md);(P/'analysis/findings.md').write_text('# Executive findings\n\n'+findings)
(P/'reports/environment.json').write_text(json.dumps({'python':__import__('sys').version,'pandas':pd.__version__,'numpy':np.__version__,'matplotlib':matplotlib.__version__},indent=2))
# Standalone dashboard with all chart bytes embedded; no missing-image paths.
cards=[('Observed output',f'{d.energy_kwh.sum()/1000:,.0f} MWh'),('Performance index',f'{index:.1f}%'),('Energy coverage',f'{coverage:.1f}%'),('Assets',str(d.asset_id.nunique()))]
body=''.join(f'<article><small>{k}</small><strong>{v}</strong></article>' for k,v in cards)
plots=''.join('<figure><img alt="'+html.escape(title)+'" src="data:image/png;base64,'+base64.b64encode((P/'charts'/file).read_bytes()).decode()+'"></figure>' for file,title,_ in [charts[0],charts[2],charts[3],charts[6]])
(P/'dashboard/index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Solar operations dashboard</title><style>body{margin:0;background:#edf2f2;color:#174f68;font:15px system-ui}main{max-width:1500px;padding:24px;margin:auto}h1{margin:0;font-size:32px}p,footer{color:#617382}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:20px 0}article{background:#fcfbf7;padding:16px;border-top:4px solid #d69d2c;border-radius:10px}small,strong{display:block}strong{font-size:28px;margin-top:7px}.plots{display:grid;grid-template-columns:1fr 1fr;gap:14px}figure{margin:0;overflow:hidden;border-radius:10px}img{width:100%;display:block}footer{font-size:12px;margin-top:15px}@media(max-width:750px){.cards{grid-template-columns:1fr 1fr}.plots{grid-template-columns:1fr}}@media print{@page{size:A3 landscape;margin:8mm}main{padding:0}}</style><main><h1>Solar operations | From sunlight to delivered energy</h1><p>Six fictional sites • January 2024–December 2025 • Synthetic data</p><section class="cards">'''+body+'</section><section class="plots">'+plots+'</section><footer>Observed output is incomplete where telemetry is missing. Performance and gap estimates use a simplified reference model and matched records. Static executive summary.</footer></main></html>')
print(findings);print('Seven charts, EDA findings, README and standalone dashboard generated.')
