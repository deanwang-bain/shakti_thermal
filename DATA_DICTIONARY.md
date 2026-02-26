# Data Dictionary (Synthetic Demo)

## Tab 1 — Data Mapping
- **asset_hierarchy.csv**: Canonical asset structure with aliases and criticality.
- **sensor_registry.csv**: Tag registry linked to assets with aliases + descriptions.
- **events_outages_derates.csv**: Forced/planned/partial derate events with MW unavailable and root cause.
- **work_orders.csv**: Messy CMMS work orders + ground-truth asset mapping.
- **shift_logs.csv**: Free-text operator logs + ground-truth asset mapping.
- **emails.csv**: Fictional emails referencing events + ground-truth event mapping.
- **media_metadata.csv**: Placeholder media items linked to events and assets.
- **alarms.csv**: Alarm messages linked to tags + ground-truth tag mapping.
- **ontology_nodes.csv / ontology_edges.csv**: Graph representation connecting all domains.

## Tab 2 — Generation View
- **dispatch_timeseries_5min.csv.gz**: 5-minute available vs target vs net generation + delta and deviation type.
- **scada_unit1_5min.csv.gz**: 5-minute evidence tags (draft, ID fan, damper, O2, mill current, turbine vib, condenser temp, aux, net MW).
- **heat_rate_hourly.csv**: Hourly NSHR vs reference curve + aux load, fuel heat input, ramp rate, restart flag.

## Tab 3 — Revenue View
- **energy_settlement_5min.csv.gz**: 5-minute price + energy revenue actual/potential + loss.
- **capacity_revenue_daily.csv**: Daily availability factor and capacity payment actual/potential + availability penalty.
- **penalties_daily.csv**: Daily DSM-like penalties derived from controllable 5-minute misses.
- **fuel_cost_daily.csv**: Daily coal cost actual vs reference + non-recovered overburn cost (partial pass-through).
- **daily_revenue_reconciliation.csv**: Daily reconciliation ensuring Actual/Max/Loss/RCR balance.
- **revenue_summary_monthly.csv**: Monthly roll-ups with Revenue Capture Ratio.
- **lost_revenue_attribution_daily.csv**: Daily loss attribution by category and equipment; sums to total loss.

## Tab 4 — Chatbot
- **docs/ops_manual.md**: Fictional but realistic operating guidance aligned to patterns.
- **docs/troubleshooting_cards.md**: If-then cards for key issue archetypes.
- **docs/glossary.md**: Definitions of dispatch target, delta, NSHR, RCR, etc.
