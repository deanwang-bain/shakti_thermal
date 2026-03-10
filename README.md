# Plant Co — Full Potential Demo (Streamlit Prototype)

This repository contains a complete, runnable Streamlit prototype for a thermal plant “full potential” story centered on **Revenue Capture Ratio (RCR)**.
The app is Bain-branded (accent `#CB2026`, Arial styling), resilient to missing optional files, and designed for executive demos.
It uses synthetic data under `./data` and docs under `./docs` with robust filename fallbacks.
The prototype includes four integrated tabs: ontology/mapping, generation diagnostics, revenue analytics, and a retrieval-based GenAI chatbot.
All heavy data loads and transformations are cached for fast re-runs.
Startup sanity checks run non-fatally and surface pass/warn/fail status in-app.

## Tabs at a glance

1. **Data Mapping & Ontology**
	- Interactive ontology graph (assets, tags, events, work-order references)
	- GenAI-like fuzzy matcher over canonical names and aliases
	- Mapping audit (sampled WOs, accuracy@1/accuracy@5 when truth exists, CSV export)

2. **Generation View**
	- Dispatch target vs available vs net generation with red delta shading
	- Outage overlays and 5-min miss markers
	- Heat-rate sync chart and historian correlation panel for draft-control diagnostics

3. **Revenue View**
	- KPI strip with RCR, actual revenue, max potential, total loss
	- RCR trend with intervention markers
	- Lost-revenue drivers with category/system/subsystem/component drilldowns and exports

4. **GenAI Chatbot**
	- Default mock mode (retrieval + deterministic response template)
	- Optional OpenAI RAG mode when `OPENAI_API_KEY` is set
	- Citations include source file + section, with context-aware KPI insertion

---

## Run instructions

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

---

## Data expectations

The app reads files from `./data` and attempts fallbacks in order, selecting the first available file.

### Core mapping / ontology
- `asset_hierarchy.csv`
- `sensor_registry.csv`
- `ontology_nodes.csv` (fallback generated from assets + sensors if missing)
- `ontology_edges.csv` (fallback generated with `PARENT_OF` + `MEASURES` if missing)
- outages/events: `outage_ledger.csv` OR `events_outages_derates.csv`
- media: `media_index.csv` OR `media_metadata.csv`
- `work_orders.csv`
- optional: `alarms.csv`, `shift_logs.csv`, `emails.csv`

### Generation view
- dispatch: `dispatch_timeseries_5min.parquet` OR `.csv` OR `.csv.gz`
- historian: `sensor_timeseries_5min.parquet` OR `.csv` OR `scada_unit1_5min.csv.gz` OR `.csv`
- heat rate: `heat_rate_timeseries.parquet` OR `.csv` OR `heat_rate_hourly.csv`

### Revenue view
- `revenue_summary_monthly.csv`
- energy settlement: `revenue_5min.csv` OR `energy_settlement_5min.csv.gz` OR `.csv`
- `capacity_revenue_daily.csv`
- attribution: `lost_revenue_attribution.csv` OR `lost_revenue_attribution_daily.csv`
- optional: `penalties_daily.csv`, `fuel_cost_daily.csv`, `daily_revenue_reconciliation.csv`

### Docs for chatbot and glossary
- `docs/ops_manual.md`
- `docs/troubleshooting_cards.md`
- `docs/glossary.md`

If files are missing, the app degrades gracefully and reports warnings in Sidebar Data Health + Sanity Status.

---

## Assets expectations

- Placeholder logo: `assets/bain_logo_placeholder.svg` (generic non-trademark placeholder)
- Blueprint placeholder: `assets/blueprint_placeholder.svg`
- Replace placeholders with approved client/demo imagery before presentation.

---

## Chatbot modes

### Default (always available): Mock mode
- Uses retrieval over docs + generated context snippets
- Responds with structure:
  - What happened
  - Likely drivers
  - Evidence
  - Recommended actions
  - Expected value impact

### Optional: LLM mode (RAG)
Enable by setting:

```bash
export OPENAI_API_KEY="your_key_here"
export OPENAI_MODEL="gpt-4o"   # optional override
```

Security note:
- API key is read from environment only.
- Key is never printed or logged by the app.

---

## Troubleshooting

- **Missing dataset**: app shows warning and disables only dependent visuals.
- **Schema mismatch**: app warns in Sanity Status and tries best-effort plotting/metrics.
- **Large time window + 5-min series**: plotting auto-downsamples to hourly beyond 30 days.
- **No OpenAI key**: chatbot remains fully functional in mock mode.
- **Correlation panel blank**: selected window may lack overlapping historian + dispatch timestamps.

---

## Demo checklist (presenter)

- [ ] Sidebar Data Health has no critical fails on required datasets
- [ ] Sanity Check Status visible and understandable
- [ ] Tab 1 graph renders; fuzzy matching + mapping audit export works
- [ ] Tab 2 delta shading/outage overlays visible; correlation table populates
- [ ] Tab 3 KPI strip and drilldowns render; exports download correctly
- [ ] Tab 4 mock chatbot cites docs; transcript export works
- [ ] (Optional) LLM mode appears only when key is set

---

## 90-second demo script

See full script in `EXEC_DEMO_SCRIPT_90SEC.md`.
