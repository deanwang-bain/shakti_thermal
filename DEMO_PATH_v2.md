# Shakti Thermal Station — Full Potential Demo Path v2

**Last Updated:** March 9, 2026

## Story: Revenue Realization – From Full Potential Gap to Root Cause Action

**Narrative Arc:**  
Every power plant has a contractual revenue ceiling defined by the PPA. The gap between actual revenue and this maximum represents unrealized potential. This demo takes a top-down approach: starting with total revenue loss, drilling into the main contributors (capacity vs energy vs efficiency), then diving deep into specific equipment failures with actionable root cause insights. The goal is to show executives the dollar impact, then show operators exactly where to intervene.

---

## Demo Flow (5 minutes - Streamlined Version)

**Available Tabs:**
1. **Data Mapping & Ontology** - Interactive asset graph with node inspector
2. **Generation View** - Dispatch compliance and energy loss analysis  
3. **Revenue View** - Revenue capture ratio and loss attribution
4. **Heat Rate** - Efficiency monitoring and anomaly detection
5. **Maintenance Criticality** - AI-driven maintenance prioritization
6. **GenAI Chatbot** - Conversational insights and recommendations

**Key Visualization Functions:**
- `revenue_absolute_chart()` - Actual vs potential revenue with gap visualization
- `lost_revenue_driver_chart()` - Revenue loss waterfall/attribution
- `loss_treemap()` - Hierarchical loss breakdown
- `generation_main_chart()` - Dispatch target vs actual generation
- `dispatch_gap_attribution_chart()` - Root cause attribution by system
- `historian_overlay_chart()` - Equipment sensor correlation
- `heat_rate_trend_chart()` - NSHR trend with benchmarks
- `maintenance_criticality_bubble_chart()` - Asset criticality matrix
- `rcr_over_time_chart()` - Revenue capture ratio trending

---

### **START: Tab 3 - Revenue View** (1.5 min)

---

#### **1. Revenue Gap Overview**

**Setup:**
- Unit: `STS-U1`
- Date range: Last 12-24 months (e.g., 2024-01-01 to 2025-12-31)
- View: Monthly resolution

**What to Show:**

**Function:** `revenue_absolute_chart(revenue_df, show_gap=True, show_annotations=True)`

Visual output:
- Stacked area or dual-line chart showing:
  - **Actual Revenue** (green/blue line or bottom segment)
  - **Revenue Gap** (red area or top segment)
  - **Maximum PPA Revenue** (dashed line representing 100% ceiling)

**What to Say:**

> "This is our revenue capture story. The gap between actual and potential represents money left on the table—averaging $2-3M annually for this 660 MW unit.
> 
> Notice Q2 2024 had a 15% gap from a major outage, but the persistent 8-10% shortfall in late 2024 is efficiency and dispatch losses, not just downtime."

---

**Function:** `lost_revenue_driver_chart(attribution_df)` or `loss_treemap(attribution_df)`

Visual output:
- Waterfall chart or treemap breaking down losses by category:
  1. **Capacity Payment Losses** - Availability shortfalls
  2. **Energy Payment Losses** - Dispatch misses  
  3. **Heat Rate Inefficiency** - NSHR deviations
  4. **Penalties** - PPA compliance issues

**What to Say:**

> "Energy payment losses dominate at $1.8M—that's electricity we were called to deliver but couldn't. Let's drill into why."

---

### **Tab 2: Generation View** (1.5 min)

---

#### **2. Dispatch Compliance Deep Dive**

**Setup:**
- Same unit and date range
- Resolution: Daily or Hourly for trend visibility

**What to Show:**

**Function:** `generation_main_chart(dispatch_df, show_gap_area=True, show_annotations=True)`

Visual output:
- Dual-line chart with shaded gap area:
  - **Blue line:** Dispatch target (sum of 5-min MW requests)
  - **Green line:** Actual net generation
  - **Red shading:** Dispatch miss (gap between target and actual)

**What to Say:**

> "92% dispatch compliance means we're missing 8% of requested generation—450 MWh monthly, translating to $135k in lost energy revenue.
> 
> The question is: which systems are causing these misses?"

---

**Function:** `dispatch_gap_attribution_chart(dispatch_df, resolution='daily')`

Visual output:
- Stacked bar chart showing daily/monthly dispatch gaps by root cause:
  - Boiler issues (ID fans, draft, feedwater)
  - Turbine issues (seals, bearings, vibration)
  - Cooling constraints
  - Fuel quality
  - Planned maintenance

**What to Say:**

> "Boiler-side issues—specifically ID fan instability—account for 40% of dispatch gaps. That's our #1 target for intervention.
> 
> Let's look at one specific failure mode."

---

### **Tab 1: Data Mapping & Ontology** (1 min)

---

#### **3. Equipment Root Cause Analysis**

**Setup:**
- Interactive ontology graph showing plant hierarchy
- Node Inspector panel on right

**What to Show:**

**Function:** `build_pyvis_html(nodes_df, edges_df, events_df, wo_df)`

Visual output:
- Interactive network graph with color-coded nodes:
  - Red: Plant level  
  - Pink gradient: Unit → System → Subsystem → Component
  - Blue: Equipment/sensors
  - Yellow: Events with hover details

**Action:** Click on node `STS-U1-IDF-A` (ID Fan A)

**Function:** `get_node_inspector(selected_node, events_df, wo_df, sensor_df)`

Node Inspector displays:
- **Asset Details:** Name, system, criticality score
- **Linked Events Table:**
  - Event ID | Timestamp | Type | Duration | Impact (MW/MWh/$)
  - Example: `EVT-2025-0142` - "Draft instability, manual load reduction" - 65 MW - $19.5k
- **Work Orders:**
  - WO-2025-0087: "Inspect IDF-A damper & bearing" (Completed)
  - Status shows recurrence → incomplete root cause fix
- **Associated Sensors:**
  - `TAG::STS-U1-IDF-A-DRAFT-PRES`
  - `TAG::STS-U1-IDF-A-VIB`
  - `TAG::STS-U1-IDF-A-DAMPER-POS`

**What to Say:**

> "ID Fan A has triggered 15 forced derate events in 12 months, costing $135k in lost energy revenue.
> 
> The pattern is clear: draft pressure oscillations, damper control saturation, and bearing vibration spikes. Maintenance replaced the actuator linkage, but the problem recurred—we're treating symptoms, not root cause."

---

**Optional:** Toggle to historian overlay

**Function:** `historian_overlay_chart(merged_df, signals=['draft_pres', 'vibration', 'damper_pos'])`

Visual output:
- Multi-axis time series showing event correlation:
  - Generation drops from 345 MW → 280 MW
  - Draft pressure oscillates wildly
  - Damper position saturates at 100%
  - Vibration exceeds alarm threshold

**What to Say:**

> "Here's January 15th at 10:30 AM. Generation drops 65 MW in 5 minutes. Draft control is fighting instability—damper pegged at 100%, vibration in alarm.
> 
> True root causes: bearing wear + ash buildup in ductwork. The fix isn't just parts—it's bearing replacement, ductwork cleaning, and PID retuning. $85k investment, 8-month payback."

---

### **Tab 6: Maintenance Criticality** (30 sec)

---

#### **4. AI-Driven Prioritization**

**Setup:**
- Asset-level view with maintenance insights

**What to Show:**

**Function:** `maintenance_criticality_bubble_chart(df, color_mode='system')`

Visual output:
- Bubble chart with:
  - X-axis: Criticality score (0-1)
  - Y-axis: Maintenance impact ($)
  - Bubble size: Failure frequency
  - Color: System category

Top priority assets highlighted:
- **ID Fan A:** High criticality, high $/year impact
- **HP Turbine Seal:** Medium criticality, medium cost
- **Coal Quality Monitoring:** Low criticality, long-term gain

**What to Say:**

> "This is where AI ranks the maintenance backlog by financial ROI. ID Fan A is top priority: high criticality, high revenue impact, fast payback.
> 
> The system generates actionable work orders with cost-benefit analysis—not just 'fix everything,' but 'fix these 3 things first for maximum return.'"

---

### **Tab 4: GenAI Chatbot** (30 sec)

---

#### **5. Conversational Insights & Recommendations**

**Setup:**
- Chatbot interface with context from all tabs
- Mode: Mock (template-based) or Real LLM

**What to Show:**

Type or select pre-loaded query:
> "What are the top 3 revenue improvement actions? Prioritize by ROI."

**Function:** `build_mock_response()` or `call_openai_rag()` (depending on mode)

**Mock Response Example:**

> **Top Revenue Improvement Actions:**
> 
> **1. ID Fan A Draft Stability Fix** - $135k/year opportunity  
> *Action:* Replace bearing, clean ductwork, retune PID  
> *Investment:* $85k | *Payback:* 8 months
> 
> **2. HP Turbine Seal Replacement** - $98k/year opportunity  
> *Action:* Replace gland seals during next outage  
> *Investment:* $45k | *Payback:* 5 months
> 
> **3. Coal Quality Monitoring** - $72k/year opportunity  
> *Action:* Install moisture sensors + AI soot blower optimization  
> *Investment:* $120k | *Payback:* 20 months
> 
> **Total Potential:** $305k/year | **Portfolio Payback:** 10 months

**What to Say:**

> "The AI co-pilot synthesizes events, historian data, work orders, and financial impact—then ranks interventions by ROI.
> 
> It's not saying 'you have reliability issues.' It's saying: 'Here's a $305k revenue recovery plan with 10-month payback. Start with the fan.'"

---

## 5-Minute Demo Summary

| **Time** | **Tab** | **Focus** | **Key Message** |
|----------|---------|-----------|-----------------|
| **0:00-1:30** | Revenue View | Revenue gap & loss attribution | "$2-3M left on table annually; energy losses dominate at $1.8M" |
| **1:30-3:00** | Generation View | Dispatch compliance & system attribution | "92% compliance = $135k/month loss; boiler issues drive 40% of gaps" |
| **3:00-4:00** | Data Mapping | Equipment root cause (ID Fan A) | "15 events, $135k impact; bearing + ductwork, $85k fix, 8-mo payback" |
| **4:00-4:30** | Maintenance Criticality | AI-driven prioritization matrix | "Rank 200+ work orders by ROI; top 3 assets deliver $305k/year recovery" |
| **4:30-5:00** | GenAI Chatbot | Executive recommendations | "AI synthesizes data → actionable $305k recovery plan with 10-mo payback" |

---

## Complete Function Reference

### Revenue & Financial Metrics

**Module:** `utils.metrics`
- `compute_revenue_kpis(rev_df, dispatch_df, heat_df)` → dict of KPIs (revenue capture ratio, availability proxy, etc.)
- `top_loss_components(attribution_df, top_n=10)` → Top N revenue loss drivers ranked by impact

**Module:** `utils.viz`
- `revenue_absolute_chart(revenue_df, show_gap=True, show_annotations=True)` → Actual vs potential revenue over time
- `rcr_over_time_chart(monthly_df, show_annotations=True)` → Revenue capture ratio trend
- `lost_revenue_driver_chart(attribution_df)` → Waterfall chart of loss categories
- `loss_treemap(attribution_df)` → Hierarchical treemap of revenue losses

### Generation & Dispatch

**Module:** `utils.metrics`
- `standardize_dispatch_columns(dispatch_df)` → Normalize column names across data sources
- `detect_5min_miss_points(dispatch_df, threshold_mw=5.0)` → Flag dispatch compliance failures

**Module:** `utils.viz`
- `generation_main_chart(dispatch_df, show_gap_area=True, show_annotations=True)` → Dispatch target vs actual with gap shading
- `dispatch_gap_attribution_chart(dispatch_df, resolution='daily')` → Stacked bar of missed MWh by root cause system

### Heat Rate & Efficiency

**Module:** `utils.viz`
- `heat_rate_trend_chart(heat_df, show_benchmark=True)` → NSHR over time with contractual benchmarks
- `heat_rate_sync_chart(heat_df)` → Compare heat rate across multiple timeframes
- `build_heat_rate_chart(heat_df, chart_type='trend')` → Unified heat rate visualization interface
- `heat_rate_anomaly_table(heat_rate_daily_df, top_n=10)` → Top N worst heat rate days with context

### Asset Ontology & Root Cause

**Module:** `utils.ontology`
- `build_pyvis_html(nodes_df, edges_df, events_df, wo_df)` → Interactive network graph
- `get_node_inspector(selected_node, events_df, wo_df, sensor_df)` → Asset detail panel with linked events/WOs
- `node_options(nodes_df)` → Get selectable node list for dropdown

**Module:** `utils.viz`
- `historian_overlay_chart(merged_df, signals=['tag1', 'tag2'])` → Multi-axis correlation plot for equipment sensors

### Maintenance Criticality & AI

**Module:** `utils.viz`
- `maintenance_criticality_bubble_chart(df, color_mode='system')` → Asset prioritization matrix

**Module:** `utils.chat`
- `build_retrieval_index(docs_dir, extra_snippets)` → Index documents for RAG
- `build_data_context_snippets(catalog, unit, start_dt, end_dt)` → Generate data context for LLM
- `build_mock_response(question, context, kpis)` → Template-based chatbot (no API needed)
- `call_openai_rag(question, context, kpis, model, api_key)` → Real LLM with retrieval augmentation
- `generate_llm_insight(metric_name, value, trend, context)` → AI commentary on specific metrics
- `generate_maintenance_criticality_insight(asset_data, events, kpis)` → Maintenance ROI recommendations
- `generate_evidence_summary(events_df, wo_df, asset_id)` → Structured evidence report for asset

### Data Utilities

**Module:** `utils.data`
- `load_data_catalog(data_dir)` → Load all CSV datasets into DataCatalog object
- `filter_by_unit_and_time(df, unit, start_dt, end_dt)` → Apply unit + date filters
- `available_units(catalog)` → Get list of units in dataset
- `get_available_date_range(catalog)` → Get min/max timestamps across all data
- `best_default_date_range(catalog)` → Smart default date range (last 12-24 months)
- `downsample_for_plotting(df, max_points=5000)` → Reduce timeseries density for performance

**Module:** `utils.matching`
- `build_entity_catalog(asset_df, sensor_df, ontology_df)` → Create searchable entity index
- `fuzzy_match(query, entity_catalog, threshold=0.8)` → Match user text to asset/tag names
- `map_work_orders(wo_df, entity_catalog)` → Link work orders to assets via NLP
- `compute_mapping_accuracy(mapped_wo_df, events_df)` → Validate WO-to-asset linkage quality

### Correlation & Analysis

**Module:** `utils.metrics`
- `cached_correlations(dispatch_df, signals, method='pearson')` → Compute sensor-to-generation correlations
- `correlation_explanation(corr_df)` → Generate natural language explanation of correlation results

---

## Key Talking Points (5-Min Version)

1. **"Revenue capture ratio is the #1 KPI"** — Not uptime, but dollars per MW contracted vs delivered.

2. **"Energy losses are the silent killer"** — 5% dispatch gap = $1.8M/year for a 660 MW plant in this demo.

3. **"Boiler-side issues drive 40% of losses"** — Draft fans, not turbines, are the top revenue detractor.

4. **"Unstable draft = perfect case study"** — Recurring failures, clear historian signatures, incomplete fixes, measurable ROI.

5. **"AI ranks the backlog, not just monitoring"** — 200 open work orders → "Do these 3 first" based on $/year impact.

6. **"This is decision support, not dashboarding"** — Alarms → Events → Dispatch gaps → Revenue loss → Work orders → ROI → Action.

---

## Handling Questions (Quick Answers)

**Q: "Is this data real?"**  
A: "Synthetic demo data calibrated to real coal plant patterns. For production, we ingest your historian, WO system, and PPA contract to build a live twin. Deployment: 8-12 weeks."

**Q: "What if we lack sensor coverage?"**  
A: "70% of insights come from 20% of tags: MW output, heat rate, major equipment status, event timestamps. We start lean and expand as value is proven."

**Q: "Integration with SAP/Maximo?"**  
A: "Yes. API integrations pull WO history for root cause validation and push prioritized recommendations as maintenance tasks."

**Q: "AI accuracy?"**  
A: "85-90% for well-instrumented equipment (like ID fans). 70-75% for under-sensored systems using event clustering + WO text mining. Still actionable for prioritization."

---

## Demo Killer Lines (End Strong)

> "Every coal plant has the same failure modes. The difference between 92% and 97% revenue capture is knowing *which* modes are bleeding the most margin at *your* facility—and fixing them in order of ROI. That's what this system does."

> "You've got the data. It's sitting in your historian, your CMMS, your dispatch logs. We structure it, link it, and turn it into a decision engine. The question isn't 'can we do this?'—it's 'how much longer can we afford not to?'"

---

**End of DEMO_PATH_v2.md**
