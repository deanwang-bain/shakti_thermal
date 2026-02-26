# Shakti Thermal Station — Full Potential Demo Path v2

## Story: Revenue Realization – From Full Potential Gap to Root Cause Action

**Narrative Arc:**  
Every power plant has a contractual revenue ceiling defined by the PPA. The gap between actual revenue and this maximum represents unrealized potential. This demo takes a top-down approach: starting with total revenue loss, drilling into the main contributors (capacity vs energy vs efficiency), then diving deep into specific equipment failures with actionable root cause insights. The goal is to show executives the dollar impact, then show operators exactly where to intervene.

---

## Demo Flow (8-10 minutes total)

### **Tab 3: Revenue View** — Full Potential Revenue Analysis

---

#### **1. Revenue Generated vs Full Potential** (2.5 min)

**Setup:**
- Unit: `STS-U1`
- Date range: Last 3-5 years (e.g., 2020-01-01 to 2024-12-31) OR recent 12-24 months
- View: Monthly resolution for long-term trends

**What to Show:**

**1a. Actual Revenue vs Maximum PPA Value**

Point to a visualization showing:
- **Two line charts (month by month):**
  - Line 1: Actual revenue earned (from capacity + energy payments)
  - Line 2: Maximum possible revenue under PPA (100% performance scenario)
  - Gap between the two = unrealized revenue potential

OR

- **100% stacked bar chart (monthly):**
  - Bottom segment: Actual revenue earned
  - Top segment: Revenue gap (unrealized potential)
  - Each bar = 100% of maximum PPA revenue for that month

**What to Say:**

> "Our PPA defines a revenue ceiling—what we could earn at 100% availability and contractual efficiency. This chart shows where we've been leaving money on the table.
> 
> Over the past 3 years, we've averaged [X]% revenue capture. The gap represents lost capacity payments, energy payments we didn't earn, and efficiency penalties. That's roughly $[Y]M in unrealized value."

Point to specific months with large gaps:
> "Look at Q2 2023—this 15% gap represents a major outage event. And here in late 2024, we're seeing persistent 8-10% shortfalls driven by heat rate degradation, not just availability."

---

**1b. Main Contributors to Revenue Loss**

Scroll to the **"Revenue Loss Attribution"** breakdown (treemap or waterfall chart):

Categories:
1. **Capacity Payment Losses** — From availability shortfalls (outages, derates)
2. **Energy Payment Losses** — From dispatch gap (failed to deliver requested MWh)
3. **Heat Rate Inefficiency Losses** — Excess fuel cost due to NSHR deviation
4. **Penalties & Other Losses** — PPA penalties, ancillary service failures, etc.

**What to Say:**

> "We've decomposed the revenue gap into four buckets:
> - **Capacity losses** ($[X]M): When the plant is offline or derated, we forfeit fixed capacity payments.
> - **Energy losses** ($[Y]M): When we can't meet dispatch, we don't sell electricity.
> - **Heat rate inefficiency** ($[Z]M): Even when we're running, if our fuel burn is inefficient, margins compress. This is the 'hidden' cost—the plant is operating, but profitability per MWh drops.
> - **Penalties** ($[W]k): Direct contractual penalties for non-compliance.
> 
> The biggest opportunity is energy payment losses—let's drill into that."

---

### **Tab 2: Generation View** — Energy Payment Deep Dive

---

#### **2. Double Click on Energy Payment Losses** (2 min)

**Setup:**
- Unit: `STS-U1`
- Date range: Last 3-5 years (monthly view) OR focus on last 12 months
- Resolution: `Monthly` or `Daily` for trend analysis

**What to Show:**

**2a. Generated Electricity vs Dispatch Requirements (Line Chart)**

Two overlaid lines (month by month):
- **Blue line:** Total dispatch target MWh (sum of all 5-min dispatch requests for the month)
- **Green line:** Actual net generation MWh
- **Gap area (red shading):** Dispatch miss MWh (= lost energy revenue)

**What to Say:**

> "This chart shows our dispatch compliance at monthly granularity. Every gap between target and actual is electricity we didn't sell.
> 
> In 2023, we averaged 95% dispatch compliance. That 5% gap cost us $[X]M in energy payments. In 2024, compliance dropped to 92%—that incremental 3 points is $[Y]k/month we're now leaving on the table.
> 
> The question is: why are we missing dispatch?"

---

**2b. Main Contributors to Generation Losses (by System/Equipment)**

Scroll to the **"Dispatch Gap Attribution by Root Cause"** stacked bar chart:

Shows monthly breakdown of missed MWh by equipment/system category:
- **Boiler-side issues** (feedwater, burners, draft fans, etc.)
- **Turbine-side issues** (HP/LP turbine, bearings, seals)
- **Cooling system constraints** (condenser, cooling tower, CW pumps)
- **Fuel quality issues** (coal variability, slagging, fouling)
- **Planned maintenance** (scheduled outages)
- **Other/Unknown**

**What to Say:**

> "We've attributed each dispatch miss to a root cause system. This is where asset-level data—events, work orders, operating historian—gets linked to financial impact.
> 
> The dominant driver is **boiler-side issues**: ID fan trips, draft control instability, soot blower failures. Those account for 40% of our dispatch gap. Second is **turbine-side** at 25%, mostly bearing vibrations and seal leaks causing controlled shutdowns.
> 
> Let's pick the worst offender and drill into it."

---

### **Tab 2: Generation View** — Root Cause Deep Dive (Example: Unstable Draft)

---

#### **3. For Select Examples: Double Click on Specific Equipment Failure** (2.5 min)

**Setup:**
- Focus on **ID Fan A (STS-U1-IDF-A)** — a high-impact asset
- Date range: Last 6-12 months (to show recurring pattern)
- Resolution: `5-min` or `Hourly` to see event details

**What to Show:**

**3a. Total Contribution from the Subsystem/Equipment**

Scroll to **"Historian Correlation Panel"** or open **Node Inspector** in Tab 1 (Data Mapping & Ontology):

Select node: `ASSET::STS-U1-IDF-A` (ID Fan A)

Show:
- **Downtime/Derate Events Table:**
  - List of outage events linked to this fan
  - Columns: Event ID, Start Time, Duration, Root Cause Category, MW Impact, $ Impact
  - Sum total: e.g., "ID Fan A: 15 events, 450 MWh dispatch miss, $135k revenue loss"

**What to Say:**

> "Let's look at ID Fan A—our #1 dispatch gap driver. Over the last 12 months, this fan has triggered 15 forced derate events, costing us 450 MWh and $135k in lost energy revenue.
> 
> These aren't planned outages. These are unplanned trips or performance issues forcing the plant to reduce output mid-dispatch."

---

**3b. Root Cause Analysis: Drivers, Events, and Potential Interventions**

Switch to the **main generation chart** with historian overlay:

Toggle **"Show historian correlation"** ON to overlay relevant sensor tags:
- `TAG::STS-U1-IDF-A-DRAFT-PRES` (Draft pressure)
- `TAG::STS-U1-IDF-A-VIB` (Vibration)
- `TAG::STS-U1-IDF-A-DAMPER-POS` (Inlet damper position)

Point to a specific event (e.g., Jan 15, 2025):

**Visual:**
- Green line (net generation) drops sharply from 345 MW to 280 MW
- Blue line (dispatch target) remains at 345 MW → **red gap appears**
- Draft pressure spikes erratically
- Damper position saturates at 100% (control loop fighting instability)
- Vibration alarm threshold exceeded

**What to Say:**

> "Here's what happened on January 15th at 10:30 AM. Dispatch called for 345 MW, but we had to derate to 280 MW within 5 minutes.
> 
> Look at the draft pressure trace—it's oscillating wildly. The damper is pegged at 100%, meaning the control system is maxed out trying to stabilize furnace draft. Meanwhile, vibration on the fan bearing is spiking into alarm range.
> 
> This is **unstable draft syndrome**—a common coal plant failure mode. Root causes can include:
> - **Damper linkage wear** (mechanical slop causes control instability)
> - **Fan bearing degradation** (vibration reduces fan efficiency, requiring higher damper openings to maintain draft)
> - **Ash buildup in ductwork** (increases resistance, reducing controllable range)
> - **Coal moisture variability** (wet coal generates more flue gas, overwhelming fan capacity with existing damper settings)"

---

Scroll down to **Linked Work Orders and Events** in Node Inspector:

Show:
- Event: `EVT-2025-0142` — "IDF-A Draft Control Instability, Manual Load Reduction"
- Root Cause Category: "Boiler-side / Draft Fan"
- Linked Work Order: `WO-2025-0087` — "Inspect IDF-A damper actuator and bearing, replace if needed"
- Status: Completed (but event recurred 2 weeks later → indicates incomplete fix)

**What to Say:**

> "Operations filed a work order to inspect the damper and bearing. Maintenance replaced the actuator linkage, but the problem came back two weeks later. This tells us we're treating symptoms, not root cause.
> 
> The real issue is likely bearing wear combined with ash accumulation. The fix isn't just replacing parts—it's:
> 1. **Bearing replacement** (not just inspection)
> 2. **Ductwork cleaning** (remove ash buildup to restore airflow margin)
> 3. **Damper PID tuning** (re-tune control loop with new mechanical tolerances)
> 4. **Predictive monitoring** (install continuous bearing vibration monitoring to catch degradation early)
> 
> Cost of intervention: ~$85k (bearing + cleaning + controls).  
> ROI: We're losing $135k/year to this one issue. Payback is 8 months."

---

### **Tab 4: GenAI Chatbot** — AI Synthesis & Prioritized Recommendations (1.5 min)

**Setup:**
- Mode: Mock or Real LLM
- Context: Full dataset (all filters applied from previous tabs)

**What to Show:**

Type into chatbot:
> "What are the top 3 actions we should take to improve revenue capture ratio? Prioritize by expected financial impact."

**Mock Response (Example):**

> **Top Revenue Improvement Actions (Prioritized by ROI):**
> 
> **1. Address ID Fan A Draft Instability** ($135k/year opportunity)  
> *Action:* Replace IDF-A bearing, clean ductwork, retune damper PID loop.  
> *Cost:* $85k | *Payback:* 8 months  
> *Impact:* Eliminate 15 forced derate events/year, recover 450 MWh dispatch compliance.
> 
> **2. Optimize HP Turbine Seal Leak** ($98k/year opportunity)  
> *Action:* Replace worn gland seals during next planned outage.  
> *Cost:* $45k | *Payback:* 5 months  
> *Impact:* Reduce steam leakage, improve heat rate by 1.2%, avoid efficiency penalties.
> 
> **3. Implement Coal Quality Monitoring** ($72k/year opportunity)  
> *Action:* Install real-time coal moisture sensors + AI-based soot blower optimization.  
> *Cost:* $120k | *Payback:* 20 months  
> *Impact:* Reduce heat rate variability, improve boiler efficiency, extend tube life.
> 
> **Total Potential:** $305k/year | **Investment:** $250k | **Portfolio Payback:** 10 months

**What to Say:**

> "This is where the AI co-pilot synthesizes everything we've seen—events, historian data, work orders, financial impact—and ranks interventions by ROI.
> 
> It's not just saying 'fix the fan.' It's saying: fix the fan first because it's costing you $135k/year and only takes $85k to solve. Then tackle the turbine seals. Then invest in coal quality monitoring for long-term heat rate gains.
> 
> This shifts the conversation from 'we have reliability issues' to 'here's a $305k revenue recovery plan with 10-month payback.'"

---

## Summary: The Full Potential Story in 3 Layers

| **Layer**               | **Stakeholder**       | **Question Answered**                                      | **Tab/Tool**          |
|-------------------------|-----------------------|------------------------------------------------------------|-----------------------|
| **1. Revenue Gap**      | CFO / Plant Manager   | "How much money are we leaving on the table?"              | Tab 3: Revenue View   |
| **2. Energy Loss Drivers** | Operations Manager | "Which systems are causing dispatch misses?"               | Tab 2: Generation View (Root Cause Chart) |
| **3. Equipment Root Cause** | Maintenance / Reliability | "What's broken, why, and how do we fix it?"           | Tab 2: Historian + Tab 1: Node Inspector |
| **4. AI Prioritization** | Executive Team       | "What should we do first, and what's the ROI?"             | Tab 4: GenAI Chatbot  |

---

## Key Talking Points (Memorize These)

1. **"Revenue capture ratio is the #1 KPI."** It's not about uptime—it's about dollars per MW-hour contracted vs delivered.

2. **"Energy payment losses dominate the gap."** Availability gets attention (outages are visible), but dispatch misses are the silent killer. 5% dispatch gap = $2M+/year for a 350 MW plant.

3. **"Boiler-side issues are 40% of the problem."** Draft fans, feedwater pumps, burner management—these are the unsexy systems that kill margin.

4. **"Unstable draft is a perfect case study."** It's recurring, it has historian signatures, it has work order history, and it's expensive. Fixing it shows ROI in under a year.

5. **"AI doesn't replace engineers—it ranks their backlog."** Maintenance has 200 open work orders. The chatbot says "do these 3 first" based on revenue impact, not just mean time to failure.

6. **"This isn't monitoring—it's decision support."** We're not just alerting on alarms. We're connecting alarms → events → dispatch gaps → revenue loss → work orders → interventions → ROI.

---

## Handling Questions

**Q: "Is this data real?"**  
A: "This is synthetic demo data calibrated to real coal plant operating profiles. The patterns—draft instability, heat rate variance, dispatch gaps—are taken from actual case studies. For your facility, we'd ingest your historian, work orders, and PPA contract to build a live twin."

**Q: "How long does implementation take?"**  
A: "Data mapping takes 4-8 weeks depending on historian accessibility and asset registry maturity. The AI models train in days once data is structured. Typical production deployment is 8-12 weeks from kickoff."

**Q: "What if we don't have boiler chemistry sensors or detailed tag-level data?"**  
A: "The demo shows an idealized ontology. In practice, 70% of insights come from 20% of tags: MW output, heat rate, major equipment status (on/off), and event timestamps. We start there and expand coverage as value is proven."

**Q: "Can this integrate with our existing maintenance system (SAP/Maximo)?"**  
A: "Yes. Work order linkage is critical. We pull WO history to validate root cause hypotheses and push prioritized recommendations back as maintenance tasks. API integrations are standard."

**Q: "What's the accuracy of the AI root cause predictions?"**  
A: "For well-instrumented equipment (like ID fans with vibration + position sensors), we see 85-90% correct attribution. For under-sensored systems, we rely on event clustering and work order text mining—accuracy drops to 70-75%, but still actionable for prioritization."

---

## Demo Killer Lines (End Strong)

> "Every coal plant has the same failure modes. The difference between 92% and 97% revenue capture is knowing *which* modes are bleeding the most margin at *your* facility—and fixing them in order of ROI. That's what this system does."

> "You've got the data. It's sitting in your historian, your CMMS, your dispatch logs. We structure it, link it, and turn it into a decision engine. The question isn't 'can we do this?'—it's 'how much longer can we afford not to?'"

---

**End of DEMO_PATH_v2.md**
