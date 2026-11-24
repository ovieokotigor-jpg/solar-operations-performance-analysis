"""Reproducible fictional daily solar operations. Standard library only."""
from pathlib import Path
from datetime import date,timedelta
import random,math,csv,copy
P=Path(__file__).resolve().parent
SCHEMA={
'sites':{'site_id':'INTEGER primary key','site_name':'Fictional solar facility label','region':'Climate scenario label; not measured geography','cleaning_interval_days':'INTEGER planned cleaning interval, days'},
'assets':{'asset_id':'INTEGER inverter/array primary key','site_id':'INTEGER FK to sites','dc_capacity_kwp':'DC array nameplate capacity, kWp','ac_capacity_kw':'Inverter AC nameplate capacity, kW','commissioned_date':'ISO commissioning date before the study','temperature_coefficient':'Fractional output change per degree C above 25; negative','conversion_efficiency':'Assumed fixed DC-to-AC efficiency fraction'},
'weather':{'weather_id':'INTEGER primary key; one site-day','site_id':'INTEGER FK to sites','date':'ISO local calendar date','poa_irradiation_kwh_m2':'Daily plane-of-array solar irradiation, kWh/m2; blank sensor gaps retained NULL','ambient_temp_c':'Daily daytime ambient temperature, degrees C','rain_mm':'Daily rain, mm; zero is a dry day'},
'readings':{'reading_id':'INTEGER daily record key; duplicated in 120 raw copies','asset_id':'INTEGER FK to assets, 10 intentional unmatched raw IDs','weather_id':'INTEGER FK to weather; must match asset site','date':'Local calendar date; 150 raw dates DD/MM/YYYY, otherwise ISO','energy_kwh':'Daily AC output kWh; blank telemetry gaps, 20 negatives and 10 extreme sensor errors','module_temp_c':'Daytime module temperature, degrees C','operating_hours':'Hours available in a fixed 12-hour daylight window, not irradiance-weighted availability','days_since_cleaning':'Days since manual cleaning; rain does not reset this counter','status':'Operating, Outage or Maintenance; 200 raw labels padded/lowercase'},
'events':{'event_id':'INTEGER daily event-segment primary key','asset_id':'INTEGER FK to assets','date':'ISO event date','event_type':'Cleaning, Inverter fault or Grid outage; at most one per asset-day','downtime_hours':'Unavailable hours within fixed 12-hour daylight window','cost_ngn':'Fictional daily maintenance cost NGN; not an energy tariff'}
}
def generate():
 r=random.Random(314159);out=P/'data/raw';out.mkdir(parents=True,exist_ok=True)
 sites=[dict(site_id=i+1,site_name=f'HelioWorks Site {i+1}',region=['Coastal','Savanna','Dry inland'][i//2],cleaning_interval_days=[30,45,30,60,30,60][i]) for i in range(6)]
 assets=[dict(asset_id=i+1,site_id=i//4+1,dc_capacity_kwp=r.choice([180,220,250]),ac_capacity_kw=220,commissioned_date=f'{r.choice([2019,2020,2021,2022])}-01-01',temperature_coefficient=-.0038,conversion_efficiency=.96) for i in range(24)]
 weather=[];readings=[];events=[];soil={a['asset_id']:r.uniform(0,.02) for a in assets};last={a['asset_id']:-r.randrange(20) for a in assets};remaining={a['asset_id']:0 for a in assets}
 for day in range(731):
  d=date(2024,1,1)+timedelta(days=day);common=r.gauss(0,.35)
  for site in sites:
   sid=site['site_id'];region=site['region'];wet=d.month in [5,6,7,8,9];dust=d.month in [11,12,1,2]
   rain=round(r.gammavariate(1.4,9) if r.random()<(.62 if wet and region=='Coastal' else .42 if wet else .08) else 0,2)
   irrad=round(max(.5,min(7.2,5.6+(.4 if region=='Dry inland' else -.2)-(.9 if wet else 0)-min(rain/30,1.5)+common+r.gauss(0,.6))),3)
   temp=round(29+(3 if region=='Dry inland' else 0)+3*math.sin(day/365*2*math.pi)-rain*.05+r.gauss(0,1.5),2)
   wid=len(weather)+1;weather.append(dict(weather_id=wid,site_id=sid,date=d.isoformat(),poa_irradiation_kwh_m2=irrad,ambient_temp_c=temp,rain_mm=rain))
   grid=r.uniform(2,8) if r.random()<(.045 if wet else .025) else 0
   for a in [a for a in assets if a['site_id']==sid]:
    aid=a['asset_id'];soil[aid]=min(.2,soil[aid]+(.0022 if dust and region!='Coastal' else .00065))
    if rain>8:soil[aid]*=.45
    hours=0;kind=None;cost=0
    if remaining[aid]>0:hours=12;kind='Inverter fault';remaining[aid]-=1;cost=25000
    elif r.random()<(.008 if aid!=19 else .035):remaining[aid]=r.choice([0,0,1,2]);hours=r.uniform(3,12);kind='Inverter fault';cost=r.uniform(50000,180000)
    elif grid:hours=grid;kind='Grid outage'
    elif day-last[aid]>=site['cleaning_interval_days']:soil[aid]=.002;last[aid]=day;hours=.5;kind='Cleaning';cost=a['dc_capacity_kwp']*80
    if kind:events.append(dict(event_id=len(events)+1,asset_id=aid,date=d.isoformat(),event_type=kind,downtime_hours=round(hours,3),cost_ngn=round(cost,2)))
    hours=round(hours,3);module=round(temp+irrad*3+r.gauss(0,1),2)
    reference=a['dc_capacity_kwp']*irrad*(1+a['temperature_coefficient']*(module-25))*a['conversion_efficiency']*.97
    age=(d-date.fromisoformat(a['commissioned_date'])).days/365.25
    energy=round(min(a['ac_capacity_kw']*12,reference*(1-soil[aid])*(1-hours/12)*(1-.004*age)*r.uniform(.987,1.013)),3)
    readings.append(dict(reading_id=len(readings)+1,asset_id=aid,weather_id=wid,date=d.isoformat(),energy_kwh=energy,module_temp_c=module,operating_hours=round(12-hours,3),days_since_cleaning=day-last[aid],status='Maintenance' if kind=='Cleaning' else 'Outage' if hours else 'Operating'))
 # Correlated data loss: weather station missing affects all four associated arrays.
 for w in weather:
  if r.random()<(.035 if w['rain_mm']>15 else .008):w['poa_irradiation_kwh_m2']=''
 for t in readings:
  w=weather[t['weather_id']-1]
  if r.random()<(.05 if w['rain_mm']>15 else .012):t['energy_kwh']=''
 for t in r.sample(readings,200):t['status']=' '+t['status'].lower()+' '
 for t in r.sample(readings,150):t['date']=date.fromisoformat(t['date']).strftime('%d/%m/%Y')
 bad=r.sample([t for t in readings if t['energy_kwh']!='' and t['energy_kwh']>0],40)
 for t in bad[:20]:t['energy_kwh']=-t['energy_kwh']
 for t in bad[20:30]:t['asset_id']=90000+t['reading_id']
 for t in bad[30:]:t['energy_kwh']=99999
 readings += [copy.deepcopy(t) for t in r.sample(readings,120)]
 for name,rows in [('sites',sites),('assets',assets),('weather',weather),('readings',readings),('events',events)]:
  with (out/(name+'.csv')).open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 doc='# Data dictionary\n\nAll data synthetic. Blank numeric cells mean NULL, never zero. Dates are local calendar dates. No personal information.\n'
 for table,cols in SCHEMA.items():
  doc+='\n## '+table+'\n\n| Column | Meaning |\n|---|---|\n'+''.join(f'| `{k}` | {v} |\n' for k,v in cols.items())
 doc+='''\n## Derived fields\n\n`reference_kwh` = dc_capacity_kwp × poa_irradiation_kwh_m2 / 1 kW/m2 × (1 + temperature_coefficient × (module_temp_c − 25)) × conversion_efficiency × 0.97. This simplified clean-array reference assumes full availability and no age loss; 0.97 is a scenario balance-of-system factor. It is not PVWatts. `matched` = 1 when energy and reference are both present. `performance_index` = 100 × measured energy/reference on matched records. `available_reference_kwh` = reference × operating_hours/12. `residual_gap_kwh` = available_reference − measured energy, signed; includes age, soiling and noise, not exclusively soiling. `modelled_outage_gap_kwh` = reference × (1 − operating_hours/12), matched records only. Both gap terms sum to reference minus energy but depend on the assumed uniform energy production across daylight hours.\n\nThe daily_mart retains reading fields and adds asset site/capacity/efficiency, weather irradiation/rain/ambient temperature, reference_kwh and matched. Reports aggregate those fields using ratios of sums. Maintenance events are daily segments, not independent failure incidents; do not interpret event count as failure count. Costs use the full event ledger independently of missing telemetry.\n'''
 (P/'DATA_DICTIONARY.md').write_text(doc)
 print('Generated',len(readings),'raw readings;',len(events),'event segments')
if __name__=='__main__':generate()
