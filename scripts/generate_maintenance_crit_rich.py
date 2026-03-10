#!/usr/bin/env python3
"""
Generate rich maintenance criticality data with extensive equipment hierarchy.
Creates realistic coal plant systems, subsystems, and components with maintenance data.

Run this script to enrich the demo with more equipment and maintenance events.
No additional dependencies required.
"""

import os
from pathlib import Path
import pandas as pd
import numpy as np

# Define extensive coal plant hierarchy
SYSTEM_HIERARCHY = {
    "Boiler & Combustion": {
        "Coal Mills": ["Mill A", "Mill B", "Mill C", "Mill D", "Mill E", "Mill F"],
        "Forced Draft System": ["FD Fan A", "FD Fan B", "FD Fan A Motor", "FD Fan B Motor", 
                                "FD Fan A Damper", "FD Fan B Damper"],
        "Induced Draft System": ["ID Fan A", "ID Fan B", "ID Fan A Motor", "ID Fan B Motor",
                                 "ID Fan A Damper", "ID Fan B Damper"],
        "Primary Air System": ["PA Fan A", "PA Fan B", "PA Fan A Motor", "PA Fan B Motor"],
        "Air Preheater": ["APH A", "APH B", "APH A Basket", "APH B Basket"],
        "Sootblowers": ["Sootblower Group 1", "Sootblower Group 2", "Sootblower Group 3"],
        "Burners": ["Burner Tier 1", "Burner Tier 2", "Burner Tier 3", "Burner Tier 4"],
    },
    "Turbine": {
        "HP Turbine": ["HP Inlet Valve", "HP Stop Valve", "HP Turbine Rotor", "HP Bearing 1", "HP Bearing 2"],
        "IP Turbine": ["IP Inlet Valve", "IP Stop Valve", "IP Turbine Rotor", "IP Bearing 1", "IP Bearing 2"],
        "LP Turbine": ["LP Turbine Rotor A", "LP Turbine Rotor B", "LP Bearing 1", "LP Bearing 2", "LP Bearing 3"],
        "Lube Oil System": ["Lube Oil Pump A", "Lube Oil Pump B", "Lube Oil Cooler A", "Lube Oil Cooler B"],
        "Gland Steam System": ["Gland Steam Regulator", "Gland Steam Condenser"],
    },
    "Generator": {
        "Generator Main": ["Generator Rotor", "Generator Stator", "Generator Exciter"],
        "Generator Cooling": ["H2 Cooling System", "Stator Water Cooling", "Cooling Water Pumps"],
        "Seal Oil System": ["Seal Oil Pump A", "Seal Oil Pump B"],
    },
    "Condensate & Feedwater": {
        "Boiler Feed Pumps": ["BFP A", "BFP B", "BFP A Motor", "BFP B Motor", "BFP A Turbine Drive"],
        "Condensate Extraction": ["CEP A", "CEP B", "CEP A Motor", "CEP B Motor"],
        "Deaerator": ["Deaerator Storage Tank", "Deaerator Level Control", "Deaerator Vent"],
        "Feedwater Heaters": ["HP Heater 1", "HP Heater 2", "LP Heater 1", "LP Heater 2", "LP Heater 3"],
    },
    "Cooling": {
        "Condenser": ["Condenser A Side", "Condenser B Side", "Condenser Vacuum Pump A", "Condenser Vacuum Pump B"],
        "Circulating Water System": ["CW Pump A", "CW Pump B", "CW Pump C", "CW Pump A Motor", "CW Pump B Motor"],
        "Cooling Tower": ["CT Fan Bank 1", "CT Fan Bank 2", "CT Fan Bank 3", "CT Fan Bank 4"],
    },
    "Electrical": {
        "Main Transformer": ["GSU Transformer", "Transformer Bushing A", "Transformer Bushing B"],
        "Station Service": ["Station Transformer A", "Station Transformer B", "4160V Switchgear"],
        "Switchyard": ["Switchyard Bay 1", "Switchyard Bay 2", "Generator Breaker", "Line Breaker A"],
    },
    "Controls & I&C": {
        "DCS Controllers": ["DCS Controller 1", "DCS Controller 2", "DCS I/O Rack 1", "DCS I/O Rack 2"],
        "Field Instruments": ["Transmitter Group A", "Transmitter Group B", "Analyzer Group"],
        "Safety Systems": ["Turbine Trip System", "Burner Management System", "Emergency Shutdown"],
    },
    "Coal Handling": {
        "Conveyor System": ["Conveyor Belt 1", "Conveyor Belt 2", "Conveyor Belt 3"],
        "Crushers": ["Primary Crusher", "Secondary Crusher"],
        "Reclaim System": ["Reclaimer A", "Reclaimer B"],
    },
    "Ash Handling": {
        "Bottom Ash System": ["Bottom Ash Hopper", "Bottom Ash Conveyor", "Bottom Ash Pump A", "Bottom Ash Pump B"],
        "Fly Ash System": ["Fly Ash Silo A", "Fly Ash Silo B", "Fly Ash Conveyor"],
    },
    "Water Treatment": {
        "DM Plant": ["DM Plant A Train", "DM Plant B Train", "Regeneration System"],
        "Water Distribution": ["Service Water Pump A", "Service Water Pump B"],
    },
    "Emissions & FGD": {
        "ESP": ["ESP Field 1", "ESP Field 2", "ESP Field 3", "ESP Rapper System"],
        "FGD System": ["FGD Absorber", "FGD Recirculation Pump A", "FGD Recirculation Pump B"],
    },
}

# Root causes for each system
SYSTEM_ROOT_CAUSES = {
    "Boiler & Combustion": ["Fouling", "Erosion", "Bearing failure", "Vibration", "Motor overheating"],
    "Turbine": ["Vibration", "Bearing wear", "Blade erosion", "Oil contamination", "Seal leak"],
    "Generator": ["Insulation breakdown", "Cooling water leak", "Seal oil leak", "Rotor imbalance"],
    "Condensate & Feedwater": ["Pump seal leak", "Tube leak", "Motor bearing", "Control valve sticking"],
    "Cooling": ["Tube fouling", "Pump bearing", "Fan blade damage", "Motor failure"],
    "Electrical": ["Oil leak", "Bushing failure", "Breaker failure", "Insulation breakdown"],
    "Controls & I&C": ["Card failure", "Sensor drift", "Communication loss", "Power supply"],
    "Coal Handling": ["Belt damage", "Bearing seizure", "Crusher jam"],
    "Ash Handling": ["Hopper plugging", "Conveyor jam", "Pump wear"],
    "Water Treatment": ["Resin exhaustion", "Pump failure", "Valve leak"],
    "Emissions & FGD": ["Rapper failure", "Pump seal leak", "Nozzle plugging"],
}


def generate_asset_hierarchy_rich(rng):
    """Generate rich asset hierarchy CSV."""
    assets = []
    asset_id_counter = 1
    
    # Unit level
    unit_id = "STS-U1"
    assets.append({
        "asset_id": unit_id,
        "asset_name": "Plant Co Unit 1",
        "level": "Unit",
        "system": "Powerhouse",
        "subsystem": None,
        "component": None,
        "asset_path": "STS > Unit 1",
        "criticality": "Critical",
    })
    
    # Generate hierarchy
    for system_name, subsystems in SYSTEM_HIERARCHY.items():
        # System level
        system_id = f"SYS-{asset_id_counter:03d}"
        asset_id_counter += 1
        assets.append({
            "asset_id": system_id,
            "asset_name": system_name,
            "level": "System",
            "system": system_name,
            "subsystem": None,
            "component": None,
            "asset_path": f"STS > Unit 1 > {system_name}",
            "criticality": "High",
        })
        
        for subsystem_name, components in subsystems.items():
            # Subsystem level
            subsystem_id = f"SUB-{asset_id_counter:03d}"
            asset_id_counter += 1
            assets.append({
                "asset_id": subsystem_id,
                "asset_name": subsystem_name,
                "level": "Subsystem",
                "system": system_name,
                "subsystem": subsystem_name,
                "component": None,
                "asset_path": f"STS > Unit 1 > {system_name} > {subsystem_name}",
                "criticality": "Medium",
            })
            
            for component_name in components:
                # Component level
                comp_id = f"COMP-{asset_id_counter:03d}"
                asset_id_counter += 1
                criticality = rng.choice(["Critical", "High", "Medium", "Low"], p=[0.1, 0.3, 0.4, 0.2])
                assets.append({
                    "asset_id": comp_id,
                    "asset_name": component_name,
                    "level": "Component",
                    "system": system_name,
                    "subsystem": subsystem_name,
                    "component": component_name,
                    "asset_path": f"STS > Unit 1 > {system_name} > {subsystem_name} > {component_name}",
                    "criticality": criticality,
                })
    
    return pd.DataFrame(assets)


def generate_maintenance_criticality_summary(rng, asset_df):
    """Generate maintenance criticality asset summary with 2D metrics."""
    # Focus on System, Subsystem, and Component levels
    focus_df = asset_df[asset_df["level"].isin(["System", "Subsystem", "Component"])].copy()
    
    summaries = []
    
    for _, row in focus_df.iterrows():
        asset_id = row["asset_id"]
        level = row["level"]
        system = row["system"]
        
        # Event count varies by level
        if level == "System":
            event_count = rng.randint(15, 50)
        elif level == "Subsystem":
            event_count = rng.randint(5, 25)
        else:  # Component
            event_count = rng.randint(0, 15)
        
        # Skip if no events
        if event_count == 0:
            continue
        
        # Maintenance cost and revenue impact
        # Higher criticality = higher values
        criticality_multiplier = {"Critical": 3.0, "High": 2.0, "Medium": 1.0, "Low": 0.5}.get(row["criticality"], 1.0)
        
        base_maint_cost = rng.uniform(5000, 50000) * criticality_multiplier
        base_revenue_impact = rng.uniform(10000, 100000) * criticality_multiplier
        
        maint_cost = base_maint_cost * event_count
        revenue_impact = base_revenue_impact * event_count * rng.uniform(0.7, 1.3)
        
        # Root cause
        root_causes = SYSTEM_ROOT_CAUSES.get(system, ["Unknown issue"])
        top_root_cause = rng.choice(root_causes)
        
        # Criticality quadrant
        median_cost = 100000
        median_impact = 200000
        if maint_cost >= median_cost and revenue_impact >= median_impact:
            quadrant = "High Cost / High Impact"
        elif maint_cost >= median_cost:
            quadrant = "High Cost / Low Impact"
        elif revenue_impact >= median_impact:
            quadrant = "Low Cost / High Impact"
        else:
            quadrant = "Low Cost / Low Impact"
        
        summaries.append({
            "asset_id": asset_id,
            "asset_path": row["asset_path"],
            "level": level,
            "system": system,
            "subsystem": row["subsystem"],
            "component": row["component"],
            "event_count": event_count,
            "maintenance_cost_usd": round(maint_cost, 2),
            "revenue_impact_usd": round(revenue_impact, 2),
            "work_order_count": int(event_count * rng.uniform(0.8, 1.5)),
            "top_root_cause_category": top_root_cause,
            "criticality_quadrant": quadrant,
            "maintenance_criticality_index": round(rng.uniform(50, 95), 2),
        })
    
    return pd.DataFrame(summaries)


def generate_maintenance_event_impacts(rng, summary_df):
    """Generate detailed event impacts for top critical assets."""
    # Take top 30 assets by combined cost + impact
    top_assets = summary_df.nlargest(30, ["maintenance_cost_usd", "revenue_impact_usd"])
    
    events = []
    event_id = 1
    
    # Generate 2023-2024 events
    start_date = pd.Timestamp("2023-01-01")
    end_date = pd.Timestamp("2024-12-31")
    date_range = (end_date - start_date).days
    
    for _, asset_row in top_assets.iterrows():
        num_events = min(asset_row["event_count"], 10)  # Max 10 events per asset
        
        for i in range(num_events):
            event_date = start_date + pd.Timedelta(days=rng.randint(0, date_range))
            
            # Cost and impact per event
            avg_cost = asset_row["maintenance_cost_usd"] / asset_row["event_count"]
            avg_impact = asset_row["revenue_impact_usd"] / asset_row["event_count"]
            
            event_cost = avg_cost * rng.uniform(0.5, 1.5)
            event_impact = avg_impact * rng.uniform(0.5, 1.5)
            
            # Root cause from system
            root_causes = SYSTEM_ROOT_CAUSES.get(asset_row["system"], ["Unknown"])
            root_cause = rng.choice(root_causes)
            
            # Description
            descriptions = [
                f"{root_cause} detected during routine inspection",
                f"Unplanned outage due to {root_cause}",
                f"{root_cause} caused performance degradation",
                f"Emergency repair required for {root_cause}",
                f"Preventive maintenance addressing {root_cause}",
            ]
            
            events.append({
                "event_id": f"MAINT-{event_id:05d}",
                "asset_id": asset_row["asset_id"],
                "asset_path": asset_row["asset_path"],
                "event_date": event_date.strftime("%Y-%m-%d"),
                "description": rng.choice(descriptions),
                "root_cause_category": root_cause,
                "maintenance_cost_usd": round(event_cost, 2),
                "revenue_impact_usd": round(event_impact, 2),
                "downtime_hours": round(rng.uniform(0.5, 48), 1),
                "event_type": rng.choice(["Forced Outage", "Planned Maintenance", "Derate"]),
            })
            event_id += 1
    
    return pd.DataFrame(events)


def generate_ai_insights(rng, summary_df):
    """Generate mock AI insights for top assets."""
    top_assets = summary_df.nlargest(20, ["maintenance_cost_usd", "revenue_impact_usd"])
    
    insights = []
    
    for _, row in top_assets.iterrows():
        # Mock insight text
        insight_text = f"""
**Why {row['asset_path']} is Critical:**

This equipment ranks in the top tier for maintenance criticality due to both high consequence (revenue impact: ${row['revenue_impact_usd']:,.0f}) and high burden (maintenance cost: ${row['maintenance_cost_usd']:,.0f}).

**Drivers:**
- **Consequence**: {row['event_count']} events caused significant revenue losses through derates and outages
- **Burden**: Frequent maintenance interventions strain O&M resources  
- **Frequency**: Recurring {row['top_root_cause_category']} issues indicate systematic problem

**Recommended Actions:**
- **Immediate**: Inspect for early signs of {row['top_root_cause_category']}
- **Next Shift**: Monitor related parameters for anomalies
- **Next Outage**: Consider predictive replacement strategy

**What to Watch:**
- Trending degradation in performance metrics
- Repeating failure patterns every 60-90 days
- Correlation with load cycling events

**Expected Impact:**
If event frequency reduced by 30%, estimated annual savings: ${row['revenue_impact_usd'] * 0.3:,.0f}
"""
        
        insights.append({
            "asset_id": row["asset_id"],
            "asset_path": row["asset_path"],
            "insight_text": insight_text.strip(),
        })
    
    return pd.DataFrame(insights)


def main():
    """Generate rich maintenance criticality data."""
    rng = np.random.RandomState(42)
    
    # Output directory
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"
    data_dir.mkdir(exist_ok=True)
    
    print("Generating rich asset hierarchy...")
    asset_df = generate_asset_hierarchy_rich(rng)
    print(f"✓ Created {len(asset_df)} assets across 4 levels")
    
    print("\nGenerating maintenance criticality summary...")
    summary_df = generate_maintenance_criticality_summary(rng, asset_df)
    print(f"✓ Created {len(summary_df)} asset summaries with event data")
    
    print("\nGenerating detailed event impacts...")
    events_df = generate_maintenance_event_impacts(rng, summary_df)
    print(f"✓ Created {len(events_df)} maintenance event records")
    
    print("\nGenerating AI insights...")
    insights_df = generate_ai_insights(rng, summary_df)
    print(f"✓ Created {len(insights_df)} AI insight records")
    
    # Save to CSV
    asset_df.to_csv(data_dir / "asset_hierarchy.csv", index=False)
    summary_df.to_csv(data_dir / "maintenance_criticality_asset_summary.csv", index=False)
    events_df.to_csv(data_dir / "maintenance_event_impacts.csv", index=False)
    insights_df.to_csv(data_dir / "maintenance_criticality_ai_insights.csv", index=False)
    
    print("\n" + "="*60)
    print("✅ Rich maintenance criticality data generated successfully!")
    print("="*60)
    print(f"\nFiles created in {data_dir}:")
    print("  - asset_hierarchy.csv")
    print("  - maintenance_criticality_asset_summary.csv")
    print("  - maintenance_event_impacts.csv")
    print("  - maintenance_criticality_ai_insights.csv")
    print("\nSystem breakdown:")
    for system in asset_df["system"].unique():
        if pd.notna(system):
            count = len(asset_df[asset_df["system"] == system])
            print(f"  • {system}: {count} assets")


if __name__ == "__main__":
    main()
