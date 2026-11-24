# Data dictionary

All data synthetic. Blank numeric cells mean NULL, never zero. Dates are local calendar dates. No personal information.

## sites

| Column | Meaning |
|---|---|
| `site_id` | INTEGER primary key |
| `site_name` | Fictional solar facility label |
| `region` | Climate scenario label; not measured geography |
| `cleaning_interval_days` | INTEGER planned cleaning interval, days |

## assets

| Column | Meaning |
|---|---|
| `asset_id` | INTEGER inverter/array primary key |
| `site_id` | INTEGER FK to sites |
| `dc_capacity_kwp` | DC array nameplate capacity, kWp |
| `ac_capacity_kw` | Inverter AC nameplate capacity, kW |
| `commissioned_date` | ISO commissioning date before the study |
| `temperature_coefficient` | Fractional output change per degree C above 25; negative |
| `conversion_efficiency` | Assumed fixed DC-to-AC efficiency fraction |

## weather

| Column | Meaning |
|---|---|
| `weather_id` | INTEGER primary key; one site-day |
| `site_id` | INTEGER FK to sites |
| `date` | ISO local calendar date |
| `poa_irradiation_kwh_m2` | Daily plane-of-array solar irradiation, kWh/m2; blank sensor gaps retained NULL |
| `ambient_temp_c` | Daily daytime ambient temperature, degrees C |
| `rain_mm` | Daily rain, mm; zero is a dry day |

## readings

| Column | Meaning |
|---|---|
| `reading_id` | INTEGER daily record key; duplicated in 120 raw copies |
| `asset_id` | INTEGER FK to assets, 10 intentional unmatched raw IDs |
| `weather_id` | INTEGER FK to weather; must match asset site |
| `date` | Local calendar date; 150 raw dates DD/MM/YYYY, otherwise ISO |
| `energy_kwh` | Daily AC output kWh; blank telemetry gaps, 20 negatives and 10 extreme sensor errors |
| `module_temp_c` | Daytime module temperature, degrees C |
| `operating_hours` | Hours available in a fixed 12-hour daylight window, not irradiance-weighted availability |
| `days_since_cleaning` | Days since manual cleaning; rain does not reset this counter |
| `status` | Operating, Outage or Maintenance; 200 raw labels padded/lowercase |

## events

| Column | Meaning |
|---|---|
| `event_id` | INTEGER daily event-segment primary key |
| `asset_id` | INTEGER FK to assets |
| `date` | ISO event date |
| `event_type` | Cleaning, Inverter fault or Grid outage; at most one per asset-day |
| `downtime_hours` | Unavailable hours within fixed 12-hour daylight window |
| `cost_ngn` | Fictional daily maintenance cost NGN; not an energy tariff |

## Derived fields

`reference_kwh` = dc_capacity_kwp × poa_irradiation_kwh_m2 / 1 kW/m2 × (1 + temperature_coefficient × (module_temp_c − 25)) × conversion_efficiency × 0.97. This simplified clean-array reference assumes full availability and no age loss; 0.97 is a scenario balance-of-system factor. It is not PVWatts. `matched` = 1 when energy and reference are both present. `performance_index` = 100 × measured energy/reference on matched records. `available_reference_kwh` = reference × operating_hours/12. `residual_gap_kwh` = available_reference − measured energy, signed; includes age, soiling and noise, not exclusively soiling. `modelled_outage_gap_kwh` = reference × (1 − operating_hours/12), matched records only. Both gap terms sum to reference minus energy but depend on the assumed uniform energy production across daylight hours.

The daily_mart retains reading fields and adds asset site/capacity/efficiency, weather irradiation/rain/ambient temperature, reference_kwh and matched. Reports aggregate those fields using ratios of sums. Maintenance events are daily segments, not independent failure incidents; do not interpret event count as failure count. Costs use the full event ledger independently of missing telemetry.
