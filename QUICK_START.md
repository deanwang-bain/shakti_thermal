# Quick Start Guide - Enhanced Features

## Heat Rate Analysis

### Using Hourly Data
The Heat Rate tab now defaults to **hourly granularity** using data from `heat_rate_hourly.csv`.

**New Controls:**
1. **Granularity** toggle: Hourly / Daily / Monthly
2. **PPA Reference** input: Adjust flat reference line (9000-9500 Btu/kWh)
3. **Highlight Anomalies** toggle (Daily view only)

**What You'll See:**
- 📊 **Chart** with 4 traces:
  - Gray dotted line: Flat PPA guarantee
  - Red solid line: Net station heat rate
  - Orange dashed line: Gross heat rate (Net + Auxiliary)
  - Orange shaded area: Auxiliary penalty
  - Purple line (right axis): Auxiliary heat rate penalty in Btu/kWh
  
- 📈 **KPIs**: Avg Net HR, Avg Gross HR, Avg Deviation, Total Fuel Impact

- 📋 **Data Table** (Hourly view): First 100 rows with scroll
  
- 💾 **Download**: Full filtered dataset as CSV

### Gross Heat Rate Calculation

**Hourly data** (most accurate):
```
Uses: aux_load_mw, fuel_heat_input_mmbtu, net_station_heat_rate
Computes: net_mw → aux_ratio → auxiliary_heat_rate → gross_heat_rate
```

**Daily/Monthly** (estimated):
```
Uses: aux_load_mw, net_station_heat_rate  
Assumes: ~500 MW typical net capacity
```

**If data missing**: Warning shown, only Net HR + PPA displayed.

---

## Maintenance Criticality

### New Filtering Capabilities

**Step 1: Select Hierarchy Level**
- Choose "All Levels" or filter to System/Subsystem/Component
- Default: Shows all levels

**Step 2: Filter by System (Optional)**
- Select specific system (e.g., "Boiler & Combustion")
- Or "All Systems" to see everything

**Step 3: Filter by Subsystem (Optional)**  
- Cascades from selected system
- Further drill-down to specific subsystem

**Step 4: Adjust Display**
- **Top N**: How many assets to show (10-100)
- **Min Events**: Filter out low-activity assets
- **Color By**: system / criticality_quadrant / level

### Understanding 2D Criticality Ranking

**The Problem with 1D ranking:**
- Sorting only by "revenue impact" ignores maintenance burden
- Sorting only by "cost" ignores business consequence

**The 2D Solution:**
- Combines BOTH dimensions using Euclidean distance
- Log-transforms wide ranges
- Normalizes to 0-100 scale
- Rank = position by combined score

**Result:**
- Asset in top-right quadrant (high cost, high impact) ranks #1
- Asset with only high cost OR only high impact ranks lower
- Ranking reflects true criticality considering both factors

### Bubble Chart Interpretation

**Quadrants:**
```
High Impact │     ●          ●●●
            │                 (Critical!)
            │  
            │  ●     ●
Low Impact  │________________________
          Low Cost        High Cost
```

- **Top-Right**: Most critical (high burden + high consequence)
- **Top-Left**: High consequence, manageable burden
- **Bottom-Right**: High burden, lower consequence  
- **Bottom-Left**: Lowest criticality

**Median lines** divide the chart into quadrants based on dataset medians.

### AI Insights

**Click "Generate Detailed Analysis"** to get:
1. **Why Critical**: Rank, score, position context
2. **Drivers**: Breakdown of cost, impact, and frequency
3. **Actions**: Immediate / Next shift / Next outage recommendations
4. **Watch List**: Signals and patterns to monitor
5. **Expected Impact**: Savings estimate if frequency reduced

**Modes:**
- **Mock** (no OpenAI key): Deterministic response using asset data
- **Real** (with OpenAI key): GPT-generated detailed analysis

---

## Generate Rich Demo Data (Optional)

### When to Use
- Current demo has limited equipment (10-20 assets)
- Want to demonstrate full hierarchy with 200+ assets
- Need realistic coal plant system structure

### How to Run
```bash
cd scripts
python generate_maintenance_crit_rich.py
```

**Runtime**: ~2-5 seconds  
**No dependencies**: Uses only pandas/numpy (already installed)

### What It Creates

**11 Major Systems:**
1. Boiler & Combustion (40+ components)
2. Turbine (15+ components)
3. Generator (9+ components)
4. Condensate & Feedwater (15+ components)
5. Cooling (10+ components)
6. Electrical (8+ components)
7. Controls & I&C (8+ components)
8. Coal Handling (5+ components)
9. Ash Handling (5+ components)
10. Water Treatment (3+ components)
11. Emissions & FGD (4+ components)

**Files Overwritten:**
- `data/asset_hierarchy.csv` (~200 assets)
- `data/maintenance_criticality_asset_summary.csv` (~150 rows)
- `data/maintenance_event_impacts.csv` (~300 events)
- `data/maintenance_criticality_ai_insights.csv` (~20 insights)

**After Running**: Refresh your browser to see new data.

---

## Troubleshooting

### "Heat rate hourly data unavailable"
**Cause**: `heat_rate_hourly.csv` missing from `/data`  
**Fix**: Ensure file exists or regenerate data with `generate_demo_data.py`

### "Cannot compute Gross Heat Rate"
**Cause**: Missing `aux_load_mw` or `fuel_heat_input_mmbtu` columns  
**Fix**: Check hourly data schema, regenerate if needed

### "No assets match the current filters"
**Cause**: Filters too restrictive (e.g., Min Events = 20 but no asset has 20+ events)  
**Fix**: Reduce Min Events slider or broaden System filter

### Maintenance tab shows limited equipment
**Cause**: Using minimal demo dataset  
**Fix**: Run `scripts/generate_maintenance_crit_rich.py` for full hierarchy

### Ranking looks wrong
**Cause**: May be sorted by old single-dimension index  
**Fix**: New code computes `criticality_rank` from 2D score automatically

---

## Data File Requirements

### Minimum Required (App Still Works)
- `heat_rate_hourly.csv` OR `heat_rate_daily.csv` OR `heat_rate_monthly.csv` (at least one)
- `asset_hierarchy.csv` (for maintenance tab)

### Optional (Enhanced Features)
- All three heat rate granularities (hourly + daily + monthly)
- `maintenance_criticality_asset_summary.csv`
- `maintenance_event_impacts.csv`
- `maintenance_criticality_ai_insights.csv`

### Schema Requirements

**heat_rate_hourly.csv** (for gross heat rate):
```
Required: timestamp, unit_id, net_station_heat_rate
For Gross: aux_load_mw, fuel_heat_input_mmbtu
Optional: heat_rate_deviation_percent, fuel_cost_impact_usd
```

**maintenance_criticality_asset_summary.csv** (for 2D ranking):
```
Required: asset_id, asset_path, maintenance_cost_usd, revenue_impact_usd
Optional: level, system, subsystem, event_count, top_root_cause_category
```

---

## Testing Checklist

- [ ] Heat rate tab loads without errors
- [ ] Hourly granularity shows data table
- [ ] PPA reference slider works (9000-9500)
- [ ] Gross heat rate line appears (if data available)
- [ ] Auxiliary shaded area visible
- [ ] Daily view shows anomaly markers
- [ ] Download CSV button works
- [ ] Maintenance tab loads without errors
- [ ] Hierarchy filters cascade correctly
- [ ] Bubble chart shows 2D positioning
- [ ] Table shows `criticality_rank` column
- [ ] AI insights generate (mock or real)
- [ ] Rich data generator runs successfully (optional)
- [ ] All existing tabs still work (no regressions)

---

## Performance Notes

- **Hourly data**: Shows first 100 rows in table, full CSV download available
- **2D ranking**: Computed in-memory (no pre-computation needed)
- **Bubble chart**: Limited to Top N assets to avoid overplotting
- **Filters**: Applied client-side (fast even with 200+ assets)

---

## Next Steps

1. **Try It**: Switch Heat Rate tab to "Hourly" and adjust PPA reference
2. **Explore**: Use Maintenance filters to drill into specific systems
3. **Enrich** (optional): Run rich data generator for full equipment set
4. **Customize**: Adjust slider defaults in code if needed (e.g., Top N = 50)

Questions? Check `ENHANCEMENTS_SUMMARY.md` for technical details.
