# Heat Rate & Maintenance Criticality Enhancements

## Summary of Updates

This update adds comprehensive heat rate analysis with hourly granularity and enhanced maintenance criticality mapping with 2D ranking.

## Heat Rate Tab Features

### Granularity Options
- **Hourly** (NEW): Direct from `heat_rate_hourly.csv` with full detail
- **Daily**: Aggregated daily trends with anomaly detection  
- **Monthly**: Long-term performance tracking

### Gross Heat Rate Calculation
The tab now computes and displays:
- **Net Station Heat Rate**: Fuel efficiency based on net output
- **Gross Heat Rate**: Total heat rate including auxiliary consumption
- **Auxiliary Penalty**: Visual gap between gross and net (shaded area)

**Calculation Method** (Hourly):
```
fuel_btu = fuel_heat_input_mmbtu × 1,000,000
net_kwh = fuel_btu / net_station_heat_rate
net_mw = net_kwh / 1000  (1-hour bucket)
aux_ratio = aux_load_mw / net_mw
auxiliary_heat_rate = net_station_heat_rate × aux_ratio
gross_heat_rate = net_station_heat_rate + auxiliary_heat_rate
```

For Daily/Monthly: Simplified estimation using ~500 MW baseline.

### PPA Reference Line
- **Flat Reference**: User-adjustable (9000-9500 Btu/kWh, default 9300)
- Removes confusing varying reference line
- Shows contractual heat rate guarantee

### Features
- KPI metrics showing average net/gross heat rate and deviation
- Interactive chart with gross/net/PPA traces
- Hourly data table (first 100 rows displayed, full CSV download)
- Anomaly highlighting (daily view only)
- Download filtered datasets as CSV

## Maintenance Criticality Tab Features

### Enhanced Hierarchy Support
- **Level Filter**: All Levels, or filter to specific hierarchy level
- **System Filter**: Filter to specific plant system
- **Subsystem Filter**: Further drill-down (cascading from system)
- **Top N**: Show top 10-100 critical assets (default 25)

### 2D Criticality Ranking
New scoring algorithm considers BOTH dimensions:
```python
# Log transform for wide ranges
x = log1p(maintenance_cost_usd)
y = log1p(revenue_impact_usd)

# Normalize to 0-1
x_norm = (x - min) / (max - min)
y_norm = (y - min) / (max - min)

# Combined 2D score
criticality_score_2d = 100 × sqrt((x_norm² + y_norm²) / 2)

# Rank descending by score
criticality_rank = rank(criticality_score_2d, descending=True)
```

### Bubble Chart
- **X-axis**: Maintenance cost (resource burden)
- **Y-axis**: Revenue impact (failure consequence)  
- **Bubble Size**: Event frequency
- **Median Lines**: Quadrant reference lines
- **Ranking**: Top N by 2D score (not single dimension)

### AI Insights
Enhanced prompts referencing:
- Rank and score position
- Both cost AND impact dimensions
- Recommended actions by timeframe
- Expected savings if frequency reduced

## Rich Data Generator (Optional)

### Purpose
Generate realistic coal plant hierarchy with extensive equipment for demo purposes.

### Usage
```bash
cd scripts
python generate_maintenance_crit_rich.py
```

### Output
Creates/overwrites 4 files in `/data`:
- `asset_hierarchy.csv` (~200+ assets)
- `maintenance_criticality_asset_summary.csv`
- `maintenance_event_impacts.csv`
- `maintenance_criticality_ai_insights.csv`

### Equipment Coverage
11 major systems with realistic subsystems:
- **Boiler & Combustion**: Mills, fans, APH, burners, sootblowers
- **Turbine**: HP/IP/LP stages, bearings, lube oil
- **Generator**: Rotor, stator, cooling, seal oil
- **Condensate & Feedwater**: BFPs, CEPs, deaerator, heaters
- **Cooling**: Condenser, CW pumps, cooling tower fans
- **Electrical**: GSU, station transformers, switchyard
- **Controls & I&C**: DCS, field instruments, safety systems
- **Coal Handling**: Conveyors, crushers, reclaimers
- **Ash Handling**: Bottom ash, fly ash systems
- **Water Treatment**: DM plant, service water
- **Emissions & FGD**: ESP, FGD absorber, recirculation

Each system includes multiple equipment instances (A/B pumps, mill banks, etc.).

## Data Catalog Updates

Already configured in `utils/data.py`:
```python
"heat_rate": hourly data (required)
"heat_rate_daily": daily aggregation (optional)
"heat_rate_monthly": monthly aggregation (optional)
"maintenance_crit": asset summary (optional)
"maintenance_event_impacts": event details (optional)
"maintenance_crit_ai": pre-generated insights (optional)
```

App works with any combination of available files.

## Key Design Principles Maintained

✅ **No UI redesign** - Preserved Bain styling, colors, spacing  
✅ **Same chart aesthetics** - Consistent Plotly theme  
✅ **Existing filters respected** - Unit and date range still apply  
✅ **No new dependencies** - Pure pandas/numpy/plotly  
✅ **Graceful degradation** - Works with missing optional files  
✅ **Backward compatible** - Existing data files still work  

## Testing Recommendations

1. **Hourly heat rate view**: Verify gross calculation accuracy
2. **PPA reference adjustment**: Test slider (9000-9500 range)
3. **Maintenance hierarchy filters**: Test cascading system→subsystem
4. **2D ranking**: Verify assets ranked by combined cost+impact
5. **Rich data generator**: Run script and reload app
6. **Missing data handling**: Remove optional files, verify graceful warnings

## Files Modified

### Core Updates
- `app.py`: Enhanced `render_tab_heat_rate()` and `render_tab_maintenance_criticality()`
- `utils/viz.py`: Added `build_heat_rate_chart()`, enhanced `maintenance_criticality_bubble_chart()`
- `utils/data.py`: Already had optional file candidates (no changes needed)

### New Files
- `scripts/generate_maintenance_crit_rich.py`: Optional rich data generator
