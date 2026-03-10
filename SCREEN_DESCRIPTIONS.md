# Plant Co Demo - Screen Descriptions

## Main Application Tabs

### 1. Data Mapping & Ontology
Interactive asset hierarchy visualization showing how plant equipment, systems, and sensors are interconnected. Displays mapping accuracy for work orders and events linked to assets using fuzzy logic and timestamp-based matching.

### 2. Revenue View
Real-time revenue performance dashboard tracking Revenue Capture Ratio (RCR), actual vs. potential revenue, and revenue loss attribution across three categories: Capacity, Energy, and Penalties. Includes AI-generated optimization recommendations.

### 3. Generation View
5-minute resolution dispatch tracking showing target vs. actual generation, highlighting dispatch misses and outages. Analyzes dispatch gap root causes and correlates SCADA signals with generation performance.

### 4. Heat Rate Analysis
Multi-granularity (hourly/daily/monthly) heat rate performance monitoring comparing Net Station Heat Rate (NSHR) and Gross Heat Rate against PPA benchmarks. Identifies efficiency anomalies and trends over time.

### 5. Maintenance Criticality
Bubble chart visualization prioritizing assets by maintenance cost and revenue impact, with criticality banding (A-E). Provides AI-powered root cause analysis and evidence drilldown with work orders, events, and multimedia attachments.

### 6. GenAI Chatbot
RAG-enabled operations co-pilot that answers questions about plant performance using real-time data context. Retrieves relevant KPIs, events, and documentation to provide data-grounded insights.

---

## Key Visualizations

### Revenue Absolute Chart
Stacked area chart showing monthly/daily revenue breakdown by category (Capacity, Energy, Penalty) with annotations for major events and outages.

### Revenue Capture Ratio Over Time
Line chart tracking RCR percentage over time, showing how much potential revenue was captured vs. lost, with event annotations.

### Lost Revenue Driver Chart
Treemap visualization showing proportion of revenue losses by category and root cause, sized by dollar impact.

### Generation Main Chart
Time series chart with dispatch target overlay, actual generation, and color-coded dispatch misses. Shows 5-minute granularity performance with outage markers.

### Dispatch Gap Attribution Chart
Stacked bar chart breaking down generation gaps by root cause (e.g., Equipment Failure, Fuel Issues, Grid Curtailment) over the selected time window.

### Heat Rate Trend Chart
Line chart comparing actual NSHR/Gross HR against PPA reference benchmark, with anomaly highlighting for periods exceeding thresholds.

### Maintenance Criticality Bubble Chart
Scatter plot with bubble size representing event count, X-axis for maintenance cost, Y-axis for revenue impact. Color-coded by criticality band (A=highest to E=lowest) or asset system.

### Interactive Ontology Graph
Network graph showing hierarchical relationships from plant → unit → system → subsystem → component → tag, with color-coded node types and edge mapping methods (ID, fuzzy logic, timestamp).

### Historian Correlation Panel
Correlation table and overlay chart showing how SCADA signals (e.g., ID Fan Speed, Furnace Draft Pressure) relate to net generation performance.
