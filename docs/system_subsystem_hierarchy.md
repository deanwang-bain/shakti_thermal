# Thermal Power Plant Systems & Subsystems Hierarchy (Reference)

This hierarchy is a **practical taxonomy** for a large coal-fired (Rankine-cycle) thermal power plant.
Use it to drive *System → Subsystem* drill-downs in the Full Potential / Revenue Capture Ratio (RCR) prototype.

## Level 0: Plant / Units
- **Plant**
  - **Unit 1**
  - **Unit 2** (if applicable)

## Level 1–2: Major Systems and Typical Subsystems

### 1) Fuel Receiving, Handling & Preparation
- Coal receiving & unloading (rail/road/jetty)
- Coal yard / stockpile management
- Crushers & sizing
- Conveyors / transfer towers
- Bunkers & feeders
- **Pulverizers / coal mills** (PF system)
- (Optional) Sorbent/limestone handling for FGD

### 2) Boiler / Steam Generator & Combustion System
- Furnace / combustion chamber
- Burners & igniters
- **Air & flue-gas path**
  - Forced Draft (FD) fans
  - Primary Air (PA) fans
  - Induced Draft (ID) fans
  - Dampers / guide vanes
  - Air preheater (APH)
- **Heat transfer surfaces**
  - Economizer
  - Superheater (SH)
  - Reheater (RH)
- Sootblowers
- Boiler water/steam circuit (drums in subcritical designs, once-through in supercritical)

### 3) Steam Turbine-Generator Train
- High / Intermediate / Low Pressure turbine sections (HP/IP/LP)
- Steam admission & control valves (stop valves, control valves)
- Bearings & vibration monitoring
- Lube oil system and oil coolers
- Generator
  - Rotor / stator
  - Cooling (e.g., hydrogen cooling where applicable)
  - Excitation system

### 4) Condensate & Feedwater (Water/Steam Cycle)
- Main condenser & hotwell
- Condensate extraction pumps (CEP)
- Low-pressure feedwater heaters (LP FWH)
- Condensate polishing / demineralizers (if present)
- Deaerator
- Boiler feed pumps (BFP)
- High-pressure feedwater heaters (HP FWH)
- Feedwater regulating / isolation valves

### 5) Cooling Water & Heat Rejection
- Circulating water (CW) pumps
- Cooling tower (natural draft or mechanical draft)
- Cooling tower makeup / blowdown
- Condenser waterboxes / tube bundles
- Vacuum / air removal equipment (steam ejectors / vacuum pumps)
- Cooling water chemistry / treatment

### 6) Flue-Gas Cleanup / Environmental Protection
- NOx control (e.g., SCR)
- Particulate control (ESP or baghouse)
- SO₂ control (FGD scrubber: wet or dry)
- Ductwork
- Stack
- (Optional) Mercury control / sorbent injection

### 7) Waste & Byproduct Handling
- Bottom ash handling
- Fly ash handling (ESP hoppers, pneumatic transfer)
- Gypsum handling (for wet FGD)
- Wastewater / effluent treatment

### 8) Electrical / Accessory Electric Plant
- Generator step-up (GSU) transformer
- Station service / auxiliary transformers
- Switchgear / breakers
- Protection relays
- DC systems / UPS
- Switchyard / substation interface to grid

### 9) Controls & Instrumentation (I&C)
- DCS / plant control systems
- Field instrumentation (pressure/temperature/flow/level)
- Analyzers (O₂, CO, NOx, etc.)
- Actuators (dampers, valves, VFDs)
- Historian / alarm management

### 10) Balance of Plant / Utilities
- Instrument air
- Fire protection
- HVAC / ventilation
- Lighting, cranes, buildings (as needed for completeness)

## Suggested drill-down mapping for the prototype

Below is a compact mapping that matches the updated synthetic attribution data:

- **Boiler**
  - Air & Flue Gas Path → ID Fans, Dampers, APH
  - Fuel Prep & Milling → Coal Mills / Feeders
  - Heat Transfer Surfaces → Superheater / Economizer
  - Combustion Control → O₂ trim / Draft loops
- **Cooling**
  - Condenser & Vacuum → Surface Condenser
  - Circulating Water System → CW Pumps / Strainers
  - Cooling Tower → CT Fans / Fill
- **Turbine**
  - Bearings & Vibration → Turbine Bearing #2
  - Steam Path & Valves → HP Control Valves
  - Lube Oil System → Lube oil pumps / coolers
- **Controls**
  - DCS & Control Logic → Unit DCS
  - Instrumentation & Sensors → Draft DP / O₂ analyzers
  - Actuators → Damper / valve actuators
- **Electrical**
  - Transformers → GSU transformer
  - Switchyard → Breakers / protection
  - Station Service → Aux transformer / MCC
- **Plant**
  - Planned Maintenance → Outage window
  - Operations → Operating constraints

---
If you want, I can also provide the above hierarchy as a **JSON tree** for direct use in the UI (tree table / breadcrumb drill-down).
