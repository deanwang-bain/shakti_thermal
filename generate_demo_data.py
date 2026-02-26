#!/usr/bin/env python3
# Synthetic dataset generator for: Shakti Thermal Station (STS) — Full Potential AI Demo (4 tabs)
# Fictional plant, fictional artifacts. No real-world rows copied.

from __future__ import annotations
import argparse, json, os
from typing import List, Dict, Tuple
import numpy as np
import pandas as pd

RATED_MW = 660.0
HOT_MONTHS = {4,5,6}
MONSOON_MONTHS = {7,8,9}
J = lambda x: json.dumps(x, ensure_ascii=False, separators=(",",":"))

def mkdirs(out_root:str)->Tuple[str,str,str]:
    data_dir=os.path.join(out_root,"data"); docs_dir=os.path.join(out_root,"docs"); schemas_dir=os.path.join(out_root,"schemas")
    for d in (data_dir,docs_dir,schemas_dir): os.makedirs(d, exist_ok=True)
    return data_dir, docs_dir, schemas_dir

def dt_5m(start_utc:str, end_excl_utc:str)->pd.DatetimeIndex:
    return pd.date_range(pd.Timestamp(start_utc,tz="UTC"), pd.Timestamp(end_excl_utc,tz="UTC"), freq="5min", inclusive="left")

def build_asset_hierarchy()->pd.DataFrame:
    rows=[]
    def add(aid,parent,level,system,name,crit,aliases):
        rows.append(dict(asset_id=aid,parent_asset_id=parent or "",level=level,system=system,canonical_name=name,
                         aliases_json=J(aliases),criticality_score=round(float(crit),3)))
    add("STS-PLANT","", "Plant","Plant","Shakti Thermal Station",0.95,["STS","Shakti Station","Shakti Thermal"])
    add("STS-U1","STS-PLANT","Unit","Unit","Unit 1 (660 MW)",0.92,["U1","Unit-1","STS Unit One","Block-1"])
    add("STS-U2","STS-PLANT","Unit","Unit","Unit 2 (660 MW)",0.74,["U2","Unit-2","STS Unit Two","Block-2"])

    systems=[("BOILER","Boiler",0.93,["Boiler","Steam Generator"]),
             ("TURBINE","Turbine",0.91,["ST","Steam Turbine","Turbine Train"]),
             ("GENERATOR","Generator",0.89,["GEN","Main Generator"]),
             ("COOLING","Cooling",0.88,["Condenser/Cooling","C&W"]),
             ("ELECTRICAL","Electrical",0.80,["Switchyard","GSU","Electrical Systems"]),
             ("CONTROLS","Controls",0.78,["DCS","Controls & I&C","Instrumentation"])]
    for sid,nm,crit,al in systems:
        add(f"STS-U1-{sid}","STS-U1","System",nm,f"{nm} System",crit,al)

    boiler_subs=[("FURNACE","Furnace",0.91,["Furnace","Combustion Chamber"]),
                 ("IDFANS","ID Fans",0.90,["ID Fans","Induced Draft Fan","IDF"]),
                 ("FDPAFANS","FD/PA Fans",0.86,["FD Fan","PA Fan","Forced Draft","Primary Air"]),
                 ("DAMPERS","Dampers",0.88,["Dampers","Gas Damper","Air Damper"]),
                 ("MILLS","Mills",0.92,["Coal Mills","Pulverizers","PF Mills"]),
                 ("APH","Air Preheater",0.84,["APH","Air Preheater","AirPreheater"]),
                 ("SH","Superheater",0.89,["SH","Super Heater"]),
                 ("ECO","Economizer",0.85,["ECO","Economiser","Econ"])]
    for code,nm,crit,al in boiler_subs:
        add(f"STS-U1-BOI-{code}","STS-U1-BOILER","Subsystem","Boiler",nm,crit,al)

    tur_subs=[("HP","HP Section",0.88,["HP Turbine","High Pressure"]),
              ("IP","IP Section",0.84,["IP Turbine","Intermediate Pressure"]),
              ("LP","LP Section",0.82,["LP Turbine","Low Pressure"]),
              ("BRG","Bearings",0.90,["Bearings","Journal Bearings"]),
              ("CV","Control Valves",0.87,["Control Valves","Steam Valves","CV"])]
    for code,nm,crit,al in tur_subs:
        add(f"STS-U1-TUR-{code}","STS-U1-TURBINE","Subsystem","Turbine",nm,crit,al)

    gen_subs=[("ROTOR","Rotor",0.85,["Rotor","Field"]),
              ("STATOR","Stator",0.83,["Stator","Armature"]),
              ("H2","Hydrogen System",0.80,["H2 System","Hydrogen Cooling"])]
    for code,nm,crit,al in gen_subs:
        add(f"STS-U1-GEN-{code}","STS-U1-GENERATOR","Subsystem","Generator",nm,crit,al)

    cool_subs=[("CT","Cooling Tower",0.86,["Cooling Tower","CT"]),
               ("CND","Condenser",0.90,["Condenser","Vacuum System"]),
               ("CWP","CW Pumps",0.88,["CW Pumps","Circulating Water Pumps","Condenser pump"])]
    for code,nm,crit,al in cool_subs:
        add(f"STS-U1-COL-{code}","STS-U1-COOLING","Subsystem","Cooling",nm,crit,al)

    add("STS-U1-ELC-XFMR","STS-U1-ELECTRICAL","Subsystem","Electrical","Transformer",0.84,["Transformer","GSU","Main XFMR"])
    add("STS-U1-ELC-SWYD","STS-U1-ELECTRICAL","Subsystem","Electrical","Switchyard",0.78,["Switchyard","Switch Yard","Yard"])
    add("STS-U1-CTL-DCS","STS-U1-CONTROLS","Subsystem","Controls","Unit DCS",0.80,["DCS","Unit Controls"])
    add("STS-U1-CTL-INST","STS-U1-CONTROLS","Subsystem","Controls","Instrumentation",0.78,["Instrumentation","I&C","Sensors"])

    # Components (support narratives)
    add("STS-U1-IDF-A","STS-U1-BOI-IDFANS","Component","Boiler","ID Fan A",0.90,["ID Fan A","Induced Draft Fan","IDF-A","Draft fan #1","ID fan (A)"])
    add("STS-U1-IDF-B","STS-U1-BOI-IDFANS","Component","Boiler","ID Fan B",0.86,["ID Fan B","IDF-B","Draft fan #2"])
    add("STS-U1-DAMPER-FG","STS-U1-BOI-DAMPERS","Component","Boiler","Flue Gas Damper",0.87,["FG Damper","Flue gas damper","Gas damper"])
    add("STS-U1-APH-1","STS-U1-BOI-APH","Component","Boiler","Air Preheater Rotor",0.80,["APH","Air Preheater","AIR preheater"])
    add("STS-U1-SH-OUT","STS-U1-BOI-SH","Component","Boiler","Superheater Outlet",0.82,["SH Outlet","Superheater outlet"])
    add("STS-U1-ECO-IN","STS-U1-BOI-ECO","Component","Boiler","Economizer Inlet",0.76,["ECO inlet","Economizer inlet"])
    for i in range(1,7):
        add(f"STS-U1-MILL-{i}","STS-U1-BOI-MILLS","Component","Boiler",f"Coal Mill {i}",0.90 if i in (3,4) else 0.82,
            [f"Mill {i}",f"Pulverizer {i}",f"M{i}",f"PF mill {i}"])
    add("STS-U1-TB-BRG2","STS-U1-TUR-BRG","Component","Turbine","Turbine Bearing #2",0.90,["TB brg2","Bearing 2","BRG2","Turb vib hi"])
    add("STS-U1-TB-CV-HP","STS-U1-TUR-CV","Component","Turbine","HP Control Valves",0.88,["HP CV","HP control valve","HPCV"])
    add("STS-U1-CND","STS-U1-COL-CND","Component","Cooling","Surface Condenser",0.90,["Condenser","CND","Condenser shell"])
    add("STS-U1-CTF-BANK1","STS-U1-COL-CT","Component","Cooling","Cooling Tower Fans Bank 1",0.86,["CT Fans","Cooling tower fans","CTF bank 1"])
    add("STS-U1-CWP-1","STS-U1-COL-CWP","Component","Cooling","CW Pump 1",0.86,["CW Pump","Condenser pump","CWP-1","CWpump A"])
    add("STS-U1-CWP-2","STS-U1-COL-CWP","Component","Cooling","CW Pump 2",0.84,["CW Pump","Condenser pump","CWP-2","CWpump B"])
    add("STS-U1-XFMR-GSU","STS-U1-ELC-XFMR","Component","Electrical","GSU Transformer",0.82,["GSU Transformer","Main transformer"])
    add("STS-U1-SWYD-1","STS-U1-ELC-SWYD","Component","Electrical","Switchyard Bay 1",0.76,["Switchyard bay 1","Bay-1"])
    add("STS-U1-DCS","STS-U1-CTL-DCS","Component","Controls","Unit DCS Controller",0.78,["DCS","Unit control","Controller"])
    return pd.DataFrame(rows)

def build_sensor_registry()->pd.DataFrame:
    rows=[]
    def add(tid,aid,tag,units,freq,aliases,desc):
        rows.append(dict(tag_id=tid,asset_id=aid,tag_name=tag,units=units,sampling_frequency=freq,aliases_json=J(aliases),description=desc))
    add("TAG-U1-FurnaceDraftPressure_Pa","STS-U1-BOI-FURNACE","FurnaceDraftPressure_Pa","Pa","5min",
        ["Furnace Draft","FDraft_Pa","Furn Draft Press"],"Furnace draft pressure (negative pull).")
    add("TAG-U1-IDFanSpeed_pct","STS-U1-IDF-A","IDFanSpeed_pct","%","5min",
        ["ID Fan A Speed","Induced Draft Fan","IDF-A"],"ID fan A speed (%).")
    add("TAG-U1-DamperPosition_pct","STS-U1-DAMPER-FG","DamperPosition_pct","%","5min",
        ["FG Damper Position","Damper Pos","Damper%"],"Flue gas damper position.")
    add("TAG-U1-O2_pct","STS-U1-BOI-FURNACE","O2_pct","%","5min",
        ["O2","Stack O2","Excess O2"],"Flue gas O₂ for combustion trim.")
    add("TAG-U1-MillCurrent_A","STS-U1-MILL-1","MillCurrent_A","A","5min",
        ["Mill amps","Mill 1 amps","Pulverizer current"],"Representative mill motor current.")
    add("TAG-U1-TurbineVibration_mm_s","STS-U1-TB-BRG2","TurbineVibration_mm_s","mm/s","5min",
        ["TB Vib","BRG2 VIB","Turb vib hi"],"Turbine bearing #2 vibration.")
    add("TAG-U1-CondenserTemp_C","STS-U1-CND","CondenserTemp_C","C","5min",
        ["Condenser Temp","Hotwell Temp"],"Condenser temperature proxy.")
    add("TAG-U1-AuxLoad_MW","STS-U1","AuxLoad_MW","MW","5min",
        ["Aux MW","Station Service MW","House Load"],"Auxiliary load estimate.")
    add("TAG-U1-NetGeneration_MW","STS-U1","NetGeneration_MW","MW","5min",
        ["Net MW","Net export","Unit Load"],"Net generation (export).")
    add("TAG-U1-CondenserVacuum_kPa","STS-U1-CND","CondenserVacuum_kPa","kPa(abs)","5min",
        ["Condenser Vacuum","CondVac"],"Condenser pressure proxy.")
    return pd.DataFrame(rows)

def generate_events(rng:np.random.Generator)->pd.DataFrame:
    ev=[]
    def add(eid,st,et,typ,mw,cat,detail,asset):
        ev.append(dict(event_id=eid,unit_id="STS-U1",start_time=st,end_time=et,type=typ,mw_unavailable=float(mw),
                       root_cause_category=cat,root_cause_detail=detail,linked_asset_id=asset))
    add("EVT-2023-09-PM1","2023-09-05T00:00:00Z","2023-09-12T00:00:00Z","Planned",660,"Planned Maintenance",
        "Annual shutdown: SH inspection, APH wash, ID fan alignment.","STS-U1-SH-OUT")
    add("EVT-2024-09-PM2","2024-09-05T00:00:00Z","2024-09-06T12:00:00Z","Planned",220,"Planned Maintenance",
        "Cooling tower fan refurbishment + condenser recovery activities.","STS-U1-CTF-BANK1")
    add("EVT-2023-02-TB-VIB","2023-02-14T02:00:00Z","2023-02-14T08:30:00Z","Forced",660,"Turbine-side",
        "Turbine vibration alarm; BRG2 high overall.","STS-U1-TB-BRG2")
    add("EVT-2023-03-MILLTRIP","2023-03-09T18:20:00Z","2023-03-09T22:15:00Z","Forced",660,"Boiler-side",
        "Mill trip (Mill 3); flame instability.","STS-U1-MILL-3")
    add("EVT-2023-05-TUBELEAK","2023-05-12T03:15:00Z","2023-05-12T19:00:00Z","Forced",660,"Boiler-side",
        "Boiler tube leak; draft swing; protective trip.","STS-U1-SH-OUT")
    add("EVT-2024-02-TB-VIB","2024-02-23T08:10:00Z","2024-02-23T12:20:00Z","Forced",660,"Turbine-side",
        "Turbine vibration alarm; BRG2 high overall.","STS-U1-TB-BRG2")
    add("EVT-2024-03-CW-CONSTR","2024-03-17T10:00:00Z","2024-03-17T18:30:00Z","Forced",660,"Cooling constraints",
        "Condenser backpressure high; CW pump cavitation; trip.","STS-U1-CWP-2")
    add("EVT-2023-07-WETCOAL","2023-07-15T00:00:00Z","2023-09-15T00:00:00Z","Partial Derate",45,"Fuel quality",
        "Monsoon wet-coal reduced stable firing margin; sustained cap.","STS-U1-MILL-3")
    add("EVT-2024-07-WETCOAL","2024-07-15T00:00:00Z","2024-09-15T00:00:00Z","Partial Derate",35,"Fuel quality",
        "Monsoon wet coal + draft sensitivity; conservative cap.","STS-U1-MILL-3")
    add("EVT-2024-06-AUXDRIFT","2024-06-01T00:00:00Z","2024-09-05T00:00:00Z","Partial Derate",60,"Cooling constraints",
        "CT fan degradation; sustained cap + aux drift.","STS-U1-CTF-BANK1")

    base=pd.date_range("2023-01-01","2025-01-01",freq="12H",inclusive="left",tz="UTC")
    pick=pd.to_datetime(rng.choice(base[base.hour==0],size=26,replace=False)).sort_values()
    for k,st in enumerate(pick[:26],start=1):
        st=st+pd.Timedelta(minutes=int(rng.integers(240,1100))); et=st+pd.Timedelta(minutes=int(rng.integers(60,240)))
        add(f"EVT-DRAFT-{st.strftime('%Y%m%d')}-{k:02d}",st.strftime("%Y-%m-%dT%H:%M:%SZ"),et.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Partial Derate",float(rng.integers(60,140)),"Boiler-side","Unstable furnace draft; ID fan hunting; damper saturation; temporary cap.","STS-U1-IDF-A")
    return pd.DataFrame(ev).sort_values("start_time").reset_index(drop=True)

def generate_dispatch_scada(rng, ts, events_df)->Tuple[pd.DataFrame,pd.DataFrame]:
    n=len(ts); hour=(ts.hour+ts.minute/60.0).to_numpy(); dow=ts.dayofweek.to_numpy(); mon=ts.month.to_numpy()
    hot=np.isin(mon,list(HOT_MONTHS)); monsoon=np.isin(mon,list(MONSOON_MONTHS))
    intraday=65*np.sin(2*np.pi*(hour-15)/24)+25*np.sin(4*np.pi*(hour-16)/24)
    target=np.clip(470+intraday+np.where(dow<5,15,-25)+np.where(hot,85,0)+np.where(monsoon,-20,0)+rng.normal(0,np.where(monsoon,20,14),size=n),280,660)

    ev=events_df.copy(); ev["start_time"]=pd.to_datetime(ev["start_time"],utc=True); ev["end_time"]=pd.to_datetime(ev["end_time"],utc=True)
    mw_un=np.zeros(n); active_eid=np.array([""]*n,dtype=object); active_cat=np.array([""]*n,dtype=object)
    for _,e in ev.iterrows():
        m=(ts>=e["start_time"])&(ts<e["end_time"]); new=float(e["mw_unavailable"])
        ow=m&(new>=mw_un); mw_un[ow]=new; active_eid[ow]=e["event_id"]; active_cat[ow]=e["root_cause_category"]
    available=np.clip(RATED_MW-mw_un,0,RATED_MW)

    draft_int=np.zeros(n)
    cand=ts[(ts.hour>=4)&(ts.hour<=21)]
    fp=pd.to_datetime(rng.choice(cand,size=42,replace=False)).sort_values()
    for st in fp:
        et=st+pd.Timedelta(minutes=int(rng.integers(30,150))); m=(ts>=st)&(ts<et); draft_int[m]=np.maximum(draft_int[m],0.80)
    for _,e in ev.iterrows():
        if str(e["event_id"]).startswith("EVT-DRAFT") and e["root_cause_category"]=="Boiler-side":
            pre=e["start_time"]-pd.Timedelta(minutes=60); mpre=(ts>=pre)&(ts<e["start_time"]); mevt=(ts>=e["start_time"])&(ts<e["end_time"])
            idx=np.where(mpre)[0]; 
            if len(idx): draft_int[idx]=np.maximum(draft_int[idx],np.linspace(0.4,1.0,len(idx)))
            draft_int[mevt]=np.maximum(draft_int[mevt],1.0)

    ramp=np.abs(np.diff(target,prepend=target[0]))/5.0
    p_miss=np.clip(0.020+0.10*draft_int+0.015*np.clip(ramp/8.0,0,1),0,0.35)
    intervention=ts>=pd.Timestamp("2024-09-06T12:00:00Z"); p_miss=np.where(intervention,p_miss*0.55,p_miss)
    miss=(rng.random(n)<p_miss)&(available>=target-3)
    miss_mw=np.zeros(n)
    miss_mw[miss]=np.clip(rng.lognormal(mean=3.0,sigma=0.50,size=miss.sum()),8,90)
    miss_mw*=1+0.8*draft_int
    miss_mw=np.clip(miss_mw,0,120)

    headroom=6+6*hot.astype(float)+8*monsoon.astype(float)+12*draft_int+4*np.clip(ramp/6.0,0,1)
    capability=np.maximum(available-headroom,0.0)
    bias=4+4*hot.astype(float)+5*monsoon.astype(float)+10*draft_int+6*np.clip(ramp/6.0,0,1)
    net=np.minimum(target,capability)-bias+rng.normal(0.0,2.0,size=n)-miss_mw
    net[available<1e-6]=0
    net=np.clip(net,0,RATED_MW)
    delta_mw=target-net; delta_mwh=delta_mw*(5/60)

    dev_type=np.array([""]*n,dtype=object); root=np.array([""]*n,dtype=object)
    tech=delta_mw>2; der=tech&(available<target-2); mis=tech&(~der)&(available>=target-2)
    dev_type[der]="Technical Derate"; dev_type[mis]="5-min Miss"
    root[tech]=np.where(active_cat[tech]!="",active_cat[tech],root[tech])
    mask=mis&(root=="")
    hi=mask&(draft_int>0.45)
    lo=mask&(~hi)
    root[hi]="Boiler-side"
    if lo.sum():
        root[lo]=rng.choice(np.array(["Boiler-side","Cooling constraints","Turbine-side","Fuel quality","Other"]),
                          size=int(lo.sum()), p=np.array([0.45,0.25,0.20,0.05,0.05]))
    rem=tech&(root==""); cats=np.array(["Boiler-side","Turbine-side","Cooling constraints","Fuel quality","Other"]); w=np.array([0.35,0.18,0.20,0.12,0.15])
    root[rem]=rng.choice(cats,size=int(rem.sum()),p=w)

    dispatch=pd.DataFrame(dict(timestamp=ts,unit_id="STS-U1",available_mw=np.round(available,3),dispatch_target_mw=np.round(target,3),
                              net_generation_mw=np.round(net,3),delta_mw=np.round(delta_mw,3),delta_mwh=np.round(delta_mwh,6),
                              deviation_type=dev_type,root_cause_category=root,active_event_id=active_eid))

    k=np.arange(n); osc=(np.sin(2*np.pi*k/3.0)+0.6*np.sin(2*np.pi*k/9.0+0.5)); osc/=np.max(np.abs(osc))
    furnace_draft=np.clip((-55+rng.normal(0,2.5,size=n))+(6+28*draft_int)*osc+rng.normal(0,1.8,size=n)-8*draft_int,-200,-20)
    idfan=np.clip(55+0.045*target+24*draft_int+rng.normal(0,2.2,size=n),25,100)
    damper=np.clip(42+0.06*target+40*draft_int+rng.normal(0,3.0,size=n),0,100)
    o2=np.clip(3.6+0.002*(target-420)+1.0*draft_int+rng.normal(0,0.18,size=n),2.5,8.5)
    fuel_active=(active_cat=="Fuel quality").astype(float)
    mill_cur=np.clip(310+0.35*target+45*monsoon.astype(float)+55*fuel_active+rng.normal(0,12,size=n),180,650)
    vib=1.2+0.001*(target-420)+rng.normal(0,0.08,size=n); vib_sp=np.zeros(n)
    for _,e in ev.iterrows():
        if e["root_cause_category"]=="Turbine-side":
            st=e["start_time"]-pd.Timedelta(minutes=90); et=e["end_time"]; m=(ts>=st)&(ts<et); 
            if m.sum(): vib_sp[m]=np.maximum(vib_sp[m],2.5+2.0/(1+np.exp(-np.linspace(-3,3,m.sum()))))
    vib=np.clip(vib+vib_sp,0.6,8.5)
    cool_active=(active_cat=="Cooling constraints").astype(float)
    cond_temp=np.clip(32+0.015*target+4.5*hot.astype(float)-2.0*monsoon.astype(float)+2.5*cool_active+rng.normal(0,0.8,size=n),20,50)
    vac=np.clip(8.8+0.12*(cond_temp-32)+rng.normal(0,0.15,size=n),6.8,14.5)
    drift=((ts>=pd.Timestamp("2024-06-01T00:00:00Z"))&(ts<pd.Timestamp("2024-09-06T12:00:00Z"))).astype(float)*7.5
    drift=np.where(intervention,drift*0.4,drift)
    aux=np.clip(34+0.03*target+0.35*(cond_temp-32)+1.5*draft_int+drift+rng.normal(0,1.2,size=n),22,85)
    scada=pd.DataFrame(dict(timestamp=ts,unit_id="STS-U1",FurnaceDraftPressure_Pa=np.round(furnace_draft,3),IDFanSpeed_pct=np.round(idfan,3),
                           DamperPosition_pct=np.round(damper,3),O2_pct=np.round(o2,3),MillCurrent_A=np.round(mill_cur,3),
                           TurbineVibration_mm_s=np.round(vib,3),CondenserTemp_C=np.round(cond_temp,3),CondenserVacuum_kPa=np.round(vac,3),
                           AuxLoad_MW=np.round(aux,3),NetGeneration_MW=np.round(net,3),draft_intensity_proxy=np.round(draft_int,3)))
    return dispatch, scada

def heat_rate_hourly(rng, dispatch_5m, scada_5m, events_df)->pd.DataFrame:
    d=dispatch_5m.copy(); d["hour"]=pd.to_datetime(d["timestamp"],utc=True).dt.floor("h"); d["net_mwh_5m"]=d["net_generation_mw"]*(5/60)
    h=d.groupby("hour").agg(net_mwh=("net_mwh_5m","sum"),avg_net_mw=("net_generation_mw","mean"),
                            avg_target_mw=("dispatch_target_mw","mean"),avg_available_mw=("available_mw","mean")).reset_index().rename(columns={"hour":"timestamp"})
    s=scada_5m.copy(); s["hour"]=pd.to_datetime(s["timestamp"],utc=True).dt.floor("h")
    sh=s.groupby("hour").agg(aux_load_mw=("AuxLoad_MW","mean"),condenser_temp=("CondenserTemp_C","mean"),draft_intensity=("draft_intensity_proxy","mean")).reset_index().rename(columns={"hour":"timestamp"})
    h=h.merge(sh,on="timestamp",how="left")
    net_mw=h["avg_net_mw"].to_numpy(); ramp=np.abs(np.diff(net_mw,prepend=net_mw[0]))/60; load=np.clip(net_mw/RATED_MW,0,1)
    ref=np.clip(9000+2600*(1-load)**2,8900,11850)

    ev=events_df.copy(); ev["start_time"]=pd.to_datetime(ev["start_time"],utc=True); ev["end_time"]=pd.to_datetime(ev["end_time"],utc=True)
    forced=ev[ev["type"]=="Forced"]
    restart=np.zeros(len(h),dtype=int); ts_h=pd.to_datetime(h["timestamp"],utc=True)
    for _,e in forced.iterrows():
        end=e["end_time"]; m=(ts_h>=end)&(ts_h<end+pd.Timedelta(hours=48)); restart[m.to_numpy()]=1

    aux=h["aux_load_mw"].to_numpy(); aux_dev=np.clip((aux-np.nanmedian(aux))/10,0,0.8)
    pen=1100*restart+350*np.clip(ramp/0.18,0,1)+220*h["draft_intensity"].to_numpy()+140*np.clip((h["condenser_temp"].to_numpy()-34)/8,0,1)+180*aux_dev
    nshr=np.clip(ref+pen+rng.normal(0,60,size=len(h)),8500,17500)
    gross=h["net_mwh"].to_numpy()+np.clip(aux,0,200)
    online=(h["avg_net_mw"].to_numpy()>30)&(h["avg_available_mw"].to_numpy()>50)
    nshr=np.where(online,nshr,np.nan)
    dev=np.where(online,(nshr-ref)/ref*100,np.nan)
    fuel_in=np.where(online,gross*nshr/1000,0.0)

    fuel_price=np.clip(2.85+0.25*np.sin(np.linspace(0,6*np.pi,len(h))),2.3,3.3)
    inc=np.where(online,np.maximum(gross*(np.nan_to_num(nshr)-ref)/1000,0),0.0)
    fuel_impact=inc*fuel_price

    return pd.DataFrame(dict(timestamp=pd.to_datetime(h["timestamp"],utc=True),unit_id="STS-U1",net_station_heat_rate=np.round(nshr,3),
                             ppa_reference_heat_rate=np.round(ref,3),aux_load_mw=np.round(aux,3),fuel_heat_input_mmbtu=np.round(fuel_in,4),
                             ramp_rate_mw_per_min=np.round(ramp,4),restart_flag=restart.astype(int),heat_rate_deviation_percent=np.round(dev,3),
                             fuel_cost_impact_usd=np.round(fuel_impact,2)))

def energy_settlement_5m(rng, dispatch_5m)->pd.DataFrame:
    ts=pd.to_datetime(dispatch_5m["timestamp"],utc=True); n=len(ts)
    hour=(ts.dt.hour+ts.dt.minute/60).to_numpy(); mon=ts.dt.month.to_numpy(); dow=ts.dt.dayofweek.to_numpy()
    hot=np.isin(mon,list(HOT_MONTHS)); monsoon=np.isin(mon,list(MONSOON_MONTHS))
    peak=18*np.maximum(0,np.sin(2*np.pi*(hour-14)/24)); season=np.where(hot,14,0)+np.where(monsoon,6,0); weekend=np.where(dow>=5,-3,0)
    price=42+peak+season+weekend+rng.normal(0,4.8,size=n)
    delta=dispatch_5m["delta_mw"].to_numpy()
    spike=(delta>180)&hot&(hour>=16)&(hour<=20)&(rng.random(n)<0.06); price[spike]+=rng.uniform(30,110,size=spike.sum())
    price=np.clip(price,10,240)
    a=dispatch_5m["net_generation_mw"].to_numpy()*(5/60); p=np.minimum(dispatch_5m["dispatch_target_mw"].to_numpy(),RATED_MW)*(5/60)
    rev_a=a*price; rev_p=p*price; loss=np.maximum(rev_p-rev_a,0)
    return pd.DataFrame(dict(timestamp=ts,unit_id="STS-U1",price_usd_mwh=np.round(price,3),energy_revenue_actual=np.round(rev_a,3),
                             energy_revenue_potential=np.round(rev_p,3),energy_revenue_loss=np.round(loss,3)))

def daily_finance(rng, dispatch_5m, energy_5m, heat_hr):
    e=energy_5m.copy(); e["date"]=pd.to_datetime(e["timestamp"],utc=True).dt.date
    e_daily=e.groupby("date").agg(energy_rev_actual=("energy_revenue_actual","sum"),energy_rev_potential=("energy_revenue_potential","sum"),
                                  energy_rev_loss=("energy_revenue_loss","sum")).reset_index()
    d=dispatch_5m.copy(); d["date"]=pd.to_datetime(d["timestamp"],utc=True).dt.date
    av=d.groupby("date")["available_mw"].mean().reset_index(name="avg_available"); av["availability_factor"]=np.clip(av["avg_available"]/RATED_MW,0,1)
    cap_pot=320000.0; cap_act=cap_pot*av["availability_factor"].to_numpy(); thr=0.90
    af=av["availability_factor"].to_numpy()
    raw_pen=np.where(af<thr,(thr-af)*cap_pot*0.75,0.0)
    avail_pen=np.minimum(raw_pen,cap_act)

    cap=pd.DataFrame(dict(date=av["date"],unit_id="STS-U1",availability_factor=np.round(av["availability_factor"],4),
                          capacity_payment_actual=np.round(cap_act,2),capacity_payment_potential=np.round(np.full(len(av),cap_pot),2),
                          availability_penalty=np.round(avail_pen,2)))

    jn=d.merge(e[["timestamp","price_usd_mwh"]],on="timestamp",how="left"); jn["delta_mwh_pos"]=np.maximum(jn["delta_mwh"].to_numpy(),0)
    miss=jn["deviation_type"].to_numpy()=="5-min Miss"; pen_rate=0.08*jn["price_usd_mwh"].to_numpy()
    jn["dsm_pen_5m"]=np.where(miss,jn["delta_mwh_pos"].to_numpy()*pen_rate,0.0)
    p=jn.groupby("date")["dsm_pen_5m"].sum().reset_index(name="dsm_penalties_usd")
    miss_mwh=jn.loc[miss].groupby("date")["delta_mwh_pos"].sum().reset_index(name="miss_mwh")
    pen=p.merge(miss_mwh,on="date",how="left").fillna({"miss_mwh":0.0}); pen["unit_id"]="STS-U1"
    pen["dsm_penalties_usd"]=pen["dsm_penalties_usd"].round(2); pen["miss_mwh"]=pen["miss_mwh"].round(3)
    pen=pen[["date","unit_id","miss_mwh","dsm_penalties_usd"]]

    h=heat_hr.copy(); h["date"]=pd.to_datetime(h["timestamp"],utc=True).dt.date
    fuel_price=np.clip(2.6+0.25*np.sin(np.linspace(0,4*np.pi,len(h)))+rng.normal(0,0.08,size=len(h)),2.2,3.3)

    d_hr=dispatch_5m.copy(); d_hr["hour"]=pd.to_datetime(d_hr["timestamp"],utc=True).dt.floor("h")
    avg_net=d_hr.groupby("hour")["net_generation_mw"].mean().reset_index().rename(columns={"hour":"timestamp"})
    hh=h.merge(avg_net,on="timestamp",how="left")
    online=(hh["net_generation_mw"].to_numpy()>30)
    gross=np.where(online,hh["net_generation_mw"].to_numpy()+hh["aux_load_mw"].to_numpy(),0.0)

    actual=hh["fuel_heat_input_mmbtu"].to_numpy(); ref=gross*hh["ppa_reference_heat_rate"].to_numpy()/1000.0
    denied=0.40; coal_act=actual*fuel_price; coal_ref=ref*fuel_price; over=np.maximum(actual-ref,0)*fuel_price*denied
    fuel=pd.DataFrame(dict(date=hh["date"],coal_cost_actual=coal_act,coal_cost_reference=coal_ref,fuel_overburn_cost=over)).groupby("date").sum().reset_index()
    fuel["unit_id"]="STS-U1"; fuel[["coal_cost_actual","coal_cost_reference","fuel_overburn_cost"]]=fuel[["coal_cost_actual","coal_cost_reference","fuel_overburn_cost"]].round(2)
    fuel=fuel[["date","unit_id","coal_cost_actual","coal_cost_reference","fuel_overburn_cost"]]

    m=e_daily.merge(cap,on="date").merge(pen,on=["date","unit_id"]).merge(fuel,on=["date","unit_id"])
    m["penalties_total_usd"]=m["dsm_penalties_usd"]+m["availability_penalty"]
    m["actual_revenue_usd"]=m["energy_rev_actual"]+m["capacity_payment_actual"]-m["penalties_total_usd"]-m["fuel_overburn_cost"]
    m["max_potential_revenue_usd"]=m["energy_rev_potential"]+m["capacity_payment_potential"]
    m["revenue_loss_usd"]=m["max_potential_revenue_usd"]-m["actual_revenue_usd"]
    m["revenue_capture_ratio"]=np.minimum(m["actual_revenue_usd"]/m["max_potential_revenue_usd"],1.0)

    recon=m[["date","unit_id","actual_revenue_usd","max_potential_revenue_usd","revenue_loss_usd","revenue_capture_ratio",
             "energy_rev_actual","energy_rev_potential","capacity_payment_actual","capacity_payment_potential","penalties_total_usd","fuel_overburn_cost"]].copy()
    m["month"]=pd.to_datetime(m["date"]).dt.to_period("M").astype(str)
    monthly=m.groupby(["month","unit_id"]).agg(actual_total_revenue=("actual_revenue_usd","sum"),
                                               max_potential_revenue=("max_potential_revenue_usd","sum"),
                                               total_revenue_loss=("revenue_loss_usd","sum")).reset_index()
    monthly["revenue_capture_ratio"]=np.minimum(monthly["actual_total_revenue"]/monthly["max_potential_revenue"],1.0)
    monthly[["actual_total_revenue","max_potential_revenue","total_revenue_loss"]]=monthly[["actual_total_revenue","max_potential_revenue","total_revenue_loss"]].round(2)
    monthly["revenue_capture_ratio"]=monthly["revenue_capture_ratio"].round(4)
    monthly=monthly[["month","unit_id","actual_total_revenue","max_potential_revenue","revenue_capture_ratio","total_revenue_loss"]]
    return cap, pen, fuel, recon, monthly

def lost_revenue_attribution(dispatch_5m, recon, events_df)->pd.DataFrame:
    # Daily loss attribution that sums EXACTLY to recon.revenue_loss_usd
    # Target: top 3 systems ≈ 60–70% of total losses (spread remaining across Plant/Controls/Electrical).
    sys_meta={
        "Boiler":("Furnace Draft","ID Fan / Dampers"),
        "Cooling":("Condenser","Cooling Tower Fans"),
        "Turbine":("Bearings","Turbine Bearing #2"),
        "Controls":("DCS","Unit Control Logic"),
        "Electrical":("Transformer","GSU Transformer"),
        "Plant":("Maintenance","Planned Window"),
    }
    # Base mapping from root-cause category → primary system
    primary_sys={
        "Boiler-side":"Boiler",
        "Fuel quality":"Boiler",
        "Turbine-side":"Turbine",
        "Cooling constraints":"Cooling",
        "Other":"Controls",
        "Planned Maintenance":"Plant",
    }
    # Split rules to prevent one system dominating the entire loss story
    energy_split={
        "Boiler-side":[("Boiler",0.58),("Controls",0.17),("Electrical",0.13),("Turbine",0.12)],
        "Fuel quality":[("Boiler",0.58),("Controls",0.22),("Electrical",0.08),("Turbine",0.12)],
        "Cooling constraints":[("Cooling",0.58),("Electrical",0.18),("Controls",0.12),("Turbine",0.12)],
        "Turbine-side":[("Turbine",0.80),("Controls",0.10),("Electrical",0.05),("Boiler",0.05)],
        "Other":[("Controls",0.60),("Electrical",0.40)],
        "Planned Maintenance":[("Plant",0.20),("Boiler",0.25),("Cooling",0.25),("Turbine",0.15),("Electrical",0.15)],
    }
    cap_split={
        "Boiler":[("Boiler",0.70),("Plant",0.15),("Electrical",0.10),("Controls",0.05)],
        "Cooling":[("Cooling",0.70),("Plant",0.15),("Electrical",0.10),("Controls",0.05)],
        "Turbine":[("Turbine",0.70),("Plant",0.15),("Electrical",0.10),("Controls",0.05)],
        "Controls":[("Controls",0.60),("Electrical",0.25),("Plant",0.15)],
        "Plant":[("Plant",0.70),("Boiler",0.15),("Cooling",0.15)],
        "Electrical":[("Electrical",0.70),("Plant",0.15),("Controls",0.15)],
    }

    d=dispatch_5m.copy()
    d["date"]=pd.to_datetime(d["timestamp"],utc=True).dt.date
    d["loss_mwh_pos"]=np.maximum(d["delta_mwh"].to_numpy(),0)
    by=d.groupby(["date","root_cause_category"])["loss_mwh_pos"].sum().reset_index()
    tot=by.groupby("date")["loss_mwh_pos"].sum().reset_index(name="tot")
    by=by.merge(tot,on="date",how="left")
    by["share"]=np.where(by["tot"]>0,by["loss_mwh_pos"]/by["tot"],0.0)
    share={(r["date"],r["root_cause_category"]):float(r["share"]) for _,r in by.iterrows()}
    cats_order=["Boiler-side","Cooling constraints","Turbine-side","Fuel quality","Planned Maintenance","Other"]
    top_cat={dte: max(cats_order, key=lambda c: share.get((dte,c),0.0)) for dte in by["date"].unique()}

    ev=events_df.copy()
    ev["start_time"]=pd.to_datetime(ev["start_time"],utc=True); ev["end_time"]=pd.to_datetime(ev["end_time"],utc=True)
    ev["date"]=ev["start_time"].dt.date
    ev["impact"]=ev["mw_unavailable"]*((ev["end_time"]-ev["start_time"]).dt.total_seconds()/3600.0)
    dom_row=ev.sort_values("impact",ascending=False).groupby("date").head(1)[["date","event_id","root_cause_category"]]
    dom_id=dom_row.set_index("date")["event_id"].to_dict()
    dom_cat=dom_row.set_index("date")["root_cause_category"].to_dict()

    rd=recon.copy()
    rd["energy_loss"]=rd["energy_rev_potential"]-rd["energy_rev_actual"]
    rd["capacity_loss"]=rd["capacity_payment_potential"]-rd["capacity_payment_actual"]
    rd["penalty_loss"]=rd["penalties_total_usd"]
    rd["efficiency_loss"]=rd["fuel_overburn_cost"]

    out=[]
    for _,r in rd.iterrows():
        date=r["date"]; unit=r["unit_id"]; eid=dom_id.get(date,"")
        base_cat=dom_cat.get(date, top_cat.get(date,"Boiler-side"))
        base_system=primary_sys.get(base_cat,"Boiler")

        energy=max(float(r["energy_loss"]),0.0)
        cap=max(float(r["capacity_loss"]),0.0)
        pen=max(float(r["penalty_loss"]),0.0)
        eff=max(float(r["efficiency_loss"]),0.0)

        # ENERGY (by root-cause shares with split rules)
        for cat in cats_order:
            s=share.get((date,cat),0.0)
            if s<=0: 
                continue
            val=energy*s
            if val<=0:
                continue
            for sys_name,frac in energy_split.get(cat, [(primary_sys.get(cat,"Controls"),1.0)]):
                sub,comp=sys_meta[sys_name]
                out.append(dict(date=date,unit_id=unit,loss_category="Energy",system=sys_name,subsystem=sub,component=comp,loss_usd=val*frac,linked_event_id=eid))

        # CAPACITY (systemized by dominant daily driver; split to avoid one bucket dominating)
        if cap>0:
            for sys_name,frac in cap_split.get(base_system, cap_split["Boiler"]):
                out.append(dict(date=date,unit_id=unit,loss_category="Capacity",system=sys_name,subsystem="Availability",component="Unit 1",loss_usd=cap*frac,linked_event_id=eid))

        # PENALTY (weighted by shares; include Controls/Electrical tail)
        if pen>0:
            w_boiler = share.get((date,"Boiler-side"),0.0)+share.get((date,"Fuel quality"),0.0)+0.25*share.get((date,"Planned Maintenance"),0.0)
            w_cooling = share.get((date,"Cooling constraints"),0.0)+0.25*share.get((date,"Planned Maintenance"),0.0)
            w_turb = share.get((date,"Turbine-side"),0.0)+0.15*share.get((date,"Planned Maintenance"),0.0)
            w_ctrl = 0.60*share.get((date,"Other"),0.0)+0.05  # baseline controls tail
            w_elec = 0.40*share.get((date,"Other"),0.0)+0.03  # baseline electrical tail
            w_plant = 0.25*share.get((date,"Planned Maintenance"),0.0)
            sysw={"Boiler":w_boiler,"Cooling":w_cooling,"Turbine":w_turb,"Controls":w_ctrl,"Electrical":w_elec,"Plant":w_plant}
            totw=sum(sysw.values()) if sum(sysw.values())>0 else 1.0
            for sys_name,w in sysw.items():
                if w<=0: continue
                sub,comp=sys_meta[sys_name]
                out.append(dict(date=date,unit_id=unit,loss_category="Penalty",system=sys_name,subsystem=sub,component=comp,loss_usd=pen*w/totw,linked_event_id=eid))

        # EFFICIENCY (aux-drift/cooling degradation; spread impact)
        if eff>0:
            for sys_name,frac in [("Cooling",0.40),("Boiler",0.30),("Turbine",0.20),("Controls",0.07),("Electrical",0.03)]:
                sub,comp=sys_meta[sys_name]
                out.append(dict(date=date,unit_id=unit,loss_category="Efficiency",system=sys_name,subsystem=sub,component=comp,loss_usd=eff*frac,linked_event_id="EVT-2024-06-AUXDRIFT" if sys_name=="Cooling" else eid))

    df=pd.DataFrame(out)
    df["loss_usd"]=df["loss_usd"].astype(float)

    # Residual correction per day so sum == total loss exactly
    sums=df.groupby("date")["loss_usd"].sum().reset_index(name="sum_loss")
    chk=rd[["date","revenue_loss_usd"]].merge(sums,on="date",how="left").fillna({"sum_loss":0.0})
    chk["residual"]=chk["revenue_loss_usd"]-chk["sum_loss"]
    for _,rr in chk.iterrows():
        if abs(rr["residual"])<0.01:
            continue
        idx=df.index[df["date"]==rr["date"]]
        if len(idx):
            df.loc[idx[-1],"loss_usd"]+=float(rr["residual"])
        else:
            df=pd.concat([df,pd.DataFrame([dict(date=rr["date"],unit_id="STS-U1",loss_category="Energy",system="Controls",
                                               subsystem="Reconciliation",component="Residual",loss_usd=float(rr["residual"]),linked_event_id="")])],ignore_index=True)

    df["loss_usd"]=df["loss_usd"].round(2)
    return df.sort_values(["date","loss_category","system"]).reset_index(drop=True)

def unstructured_tables(rng, events_df):
    roles=["Shift Supervisor","Control Room Operator","Reliability Engineer","Maintenance Planner","Performance Analyst"]
    maint_types=["Corrective","Preventive"]
    wo_templates={
        "STS-U1-IDF-A": (["IDF-A spd var","Induced draft fan hunting","Draft fan #1 oscill","IDF A damper sat"],
                        "Unstable furnace draft control; ID fan variance; damper saturation near 98–100%. Verify tuning and DP transmitter."),
        "STS-U1-APH-1": (["APH DP high","Air preheater fouling","AIR PREHEATER clog"],
                        "APH DP elevated; recommend cleaning/seal inspection; review sootblowing."),
        "STS-U1-CWP-2": (["CW pump cavit","Condenser pump B noise","CWP-2 low suction"],
                        "CW pump cavitation suspected; inspect strainer/valves; review NPSH."),
        "STS-U1-TB-BRG2": (["TB brg2 vib hi","BRG2 VIB","turbine bearing 2 vibration"],
                          "BRG2 vibration exceeded alert; spectrum check; verify oil/alignment."),
        "STS-U1-MILL-3": (["Mill3 trip","Pulverizer-3 current spike","PF mill three feeder issue"],
                         "Mill 3 current spike/trip; check moisture, feeder calibration, classifier, rejects.")
    }
    common_assets=list(wo_templates.keys())
    wos=[]
    for i in range(1,221):
        linked=rng.random()<0.70; ev=events_df.iloc[int(rng.integers(0,len(events_df)))]
        ev_id=ev["event_id"] if linked else ""
        asset=ev["linked_asset_id"] if linked else rng.choice(common_assets)
        raw_list,long=wo_templates.get(asset,wo_templates["STS-U1-IDF-A"])
        wos.append(dict(wo_id=f"WO-{i:05d}",asset_description_raw=rng.choice(raw_list),long_text=long,
                        maintenance_type=rng.choice(maint_types,p=[0.62,0.38]),cost_usd=round(float(rng.lognormal(9.0,0.6)),2),
                        labor_hours=round(float(rng.uniform(4,48)),1),linked_event_id=ev_id,standard_asset_id_truth=asset))
    work_orders=pd.DataFrame(wos)

    logs=[]
    for i in range(1,261):
        shift_start=pd.Timestamp("2023-01-01T00:00:00Z")+pd.Timedelta(hours=12*int(rng.integers(0,1462)))
        shift_end=shift_start+pd.Timedelta(hours=12)
        linked=rng.random()<0.55; ev=events_df.iloc[int(rng.integers(0,len(events_df)))]
        ev_id=ev["event_id"] if linked else ""
        asset=ev["linked_asset_id"] if linked else rng.choice(["STS-U1-IDF-A","STS-U1-BOI-FURNACE","STS-U1-CND","STS-U1-TB-BRG2","STS-U1-MILL-3"])
        if asset in ["STS-U1-IDF-A","STS-U1-BOI-FURNACE"]:
            txt=rng.choice(["Furnace draft oscillating; IDF hunting; damper near full open; reduced load.",
                            "Draft variance increased; O2 trim unstable; watched ID fan response.",
                            "Draft loop sluggish; applied manual bias; staged ramps."])
        elif asset=="STS-U1-TB-BRG2":
            txt=rng.choice(["BRG2 vibration trending high; kept ramp conservative; requested spectrum.",
                            "BRG2 crossed alert briefly; checked lube oil; stabilized."])
        elif asset=="STS-U1-CND":
            txt=rng.choice(["Condenser temp elevated; vacuum degraded; limited load to protect vacuum.",
                            "Cooling constraint suspected; CW pump noise noted; held load."])
        else:
            txt=rng.choice(["Mill current spikes; coal wet; adjusted feeder; watched stability.",
                            "Mill trip reset; restarted after checks; ramped cautiously."])
        logs.append(dict(log_id=f"LOG-{i:05d}",shift_start=shift_start,shift_end=shift_end,operator_role=rng.choice(["Shift Supervisor","Control Room Operator"]),
                         free_text=txt,linked_event_id=ev_id,standard_asset_id_truth=asset))
    shift_logs=pd.DataFrame(logs)

    em=[]
    for i in range(1,181):
        ev=events_df.iloc[int(rng.integers(0,len(events_df)))]
        t=pd.Timestamp("2023-01-01T00:00:00Z")+pd.Timedelta(days=int(rng.integers(0,731)),minutes=int(rng.integers(0,1440)))
        frm=rng.choice(roles); to=rng.choice([r for r in roles if r!=frm])
        subj=rng.choice(["Draft instability follow-up","Cooling performance issue","Turbine vibration investigation","Fuel moisture concerns","Planned outage scope","Controls issue review"])
        body=f"Event {ev['event_id']} recap: category={ev['root_cause_category']}. Please review {ev['linked_asset_id']}. Naming varies (IDF-A/Draft fan #1/APH/CW Pump)."
        em.append(dict(email_id=f"EML-{i:05d}",timestamp=t,from_role=frm,to_role=to,subject=subj,body=body,linked_event_id=ev["event_id"],standard_event_id_truth=ev["event_id"]))
    emails=pd.DataFrame(em)

    med=[]
    for i in range(1,61):
        ev=events_df.iloc[int(rng.integers(0,len(events_df)))]
        st=pd.to_datetime(ev["start_time"],utc=True); t=st+pd.Timedelta(minutes=int(rng.integers(0,180)))
        mtype=rng.choice(["photo","video"],p=[0.75,0.25])
        med.append(dict(media_id=f"MED-{i:04d}",timestamp=t,media_type=mtype,caption=rng.choice(["Field inspection captured.","Trend capture for incident review.","Maintenance finding documented."]),
                        linked_event_id=ev["event_id"],linked_asset_id=ev["linked_asset_id"],file_path_placeholder=f"/media/MED-{i:04d}.{ 'jpg' if mtype=='photo' else 'mp4'}"))
    media=pd.DataFrame(med)
    return work_orders, shift_logs, emails, media

def alarms_from_scada(rng, scada_5m, dispatch_5m):
    sc=scada_5m.sort_values("timestamp").reset_index(drop=True); ts=pd.to_datetime(sc["timestamp"],utc=True)
    draft_std=sc["FurnaceDraftPressure_Pa"].rolling(12,min_periods=12).std()
    damper_hi=sc["DamperPosition_pct"].to_numpy()>95; idfan_hi=sc["IDFanSpeed_pct"].to_numpy()>92; draft_osc=draft_std.to_numpy()>18
    vib_hi=sc["TurbineVibration_mm_s"].to_numpy()>4.8; cond_hi=sc["CondenserTemp_C"].to_numpy()>41.5; o2_hi=sc["O2_pct"].to_numpy()>6.2
    flag=damper_hi|idfan_hi|draft_osc|vib_hi|cond_hi|o2_hi; idx=np.where(flag)[0]
    if len(idx)>2600: idx=rng.choice(idx,size=2600,replace=False)
    idx=np.sort(idx); ev_at=dispatch_5m["active_event_id"].to_numpy()
    out=[]
    for j,i in enumerate(idx,start=1):
        t=ts.iloc[i]; linked=ev_at[i] if ev_at[i] else ""
        if vib_hi[i]: tag,sev,msg="TAG-U1-TurbineVibration_mm_s","HIGH","BRG2 vib high: check oil/alignment/pedestal. Trip risk."
        elif cond_hi[i]: tag,sev,msg="TAG-U1-CondenserTemp_C","MED","Condenser temp elevated; vacuum risk. Review CW pumps/CT fans."
        elif draft_osc[i]: tag,sev,msg="TAG-U1-FurnaceDraftPressure_Pa","HIGH","Furnace draft oscillation; ID fan hunting suspected. Stabilize draft."
        elif damper_hi[i]: tag,sev,msg="TAG-U1-DamperPosition_pct","MED","Damper near saturation (>95%). Check ID fan response/tuning."
        elif idfan_hi[i]: tag,sev,msg="TAG-U1-IDFanSpeed_pct","MED","ID fan speed high; approaching limit. Investigate draft demand."
        else: tag,sev,msg="TAG-U1-O2_pct","LOW","Excess O2 high; combustion trim unstable. Review air leakage/dampers."
        out.append(dict(alarm_id=f"ALM-{t.strftime('%Y%m%d%H%M')}-{j:05d}",timestamp=t,tag_id=tag,severity=sev,message=msg,linked_event_id=linked,standard_tag_id_truth=tag))
    return pd.DataFrame(out).sort_values("timestamp").reset_index(drop=True)

def build_ontology(asset_df,sensor_df,events_df,wos,logs,emails,media):
    nodes=[]; edges=[]
    def node(nid,typ,name,desc): nodes.append(dict(node_id=nid,node_type=typ,canonical_name=name,description=desc))
    def edge(src,et,dst,ev): edges.append(dict(src_node_id=src,edge_type=et,dst_node_id=dst,evidence_ref=ev))
    for _,r in asset_df.iterrows():
        node(f"ASSET::{r['asset_id']}", "asset", r["canonical_name"], f"System={r['system']} Level={r['level']}")
        if r["parent_asset_id"]: edge(f"ASSET::{r['parent_asset_id']}", "PARENT_OF", f"ASSET::{r['asset_id']}", "asset_hierarchy.csv")
    for _,r in sensor_df.iterrows():
        node(f"TAG::{r['tag_id']}", "sensor", r["tag_name"], r["description"])
        edge(f"TAG::{r['tag_id']}", "MEASURES", f"ASSET::{r['asset_id']}", "sensor_registry.csv")
    for _,r in events_df.iterrows():
        node(f"EVENT::{r['event_id']}", "event", r["type"], f"{r['root_cause_category']}: {r['root_cause_detail']}")
        edge(f"EVENT::{r['event_id']}", "AFFECTS", f"ASSET::{r['linked_asset_id']}", "events_outages_derates.csv")
    for _,r in wos.iterrows():
        node(f"WO::{r['wo_id']}", "work_order", r["asset_description_raw"], r["maintenance_type"])
        edge(f"WO::{r['wo_id']}", "REFERS_TO", f"ASSET::{r['standard_asset_id_truth']}", "work_orders.csv")
        if r["linked_event_id"]: edge(f"WO::{r['wo_id']}", "LINKED_TO", f"EVENT::{r['linked_event_id']}", "work_orders.csv")
    for _,r in logs.iterrows():
        node(f"LOG::{r['log_id']}", "shift_log", r["operator_role"], str(r["free_text"])[:140])
        edge(f"LOG::{r['log_id']}", "MENTIONS", f"ASSET::{r['standard_asset_id_truth']}", "shift_logs.csv")
        if r["linked_event_id"]: edge(f"LOG::{r['log_id']}", "LINKED_TO", f"EVENT::{r['linked_event_id']}", "shift_logs.csv")
    roles=set(emails["from_role"]).union(set(emails["to_role"]))
    for r in roles: node(f"ROLE::{r}","role",r,"Fictional operational role")
    for _,r in emails.iterrows():
        node(f"EMAIL::{r['email_id']}", "email", r["subject"], str(r["body"])[:160])
        edge(f"EMAIL::{r['email_id']}", "MENTIONS", f"EVENT::{r['standard_event_id_truth']}", "emails.csv")
        edge(f"EMAIL::{r['email_id']}", "SENT_FROM", f"ROLE::{r['from_role']}", "emails.csv")
        edge(f"EMAIL::{r['email_id']}", "SENT_TO", f"ROLE::{r['to_role']}", "emails.csv")
    for _,r in media.iterrows():
        node(f"MEDIA::{r['media_id']}", "media", r["media_type"], r["caption"])
        edge(f"MEDIA::{r['media_id']}", "EVIDENCE_FOR", f"EVENT::{r['linked_event_id']}", "media_metadata.csv")
        edge(f"MEDIA::{r['media_id']}", "CAPTURED_AT", f"ASSET::{r['linked_asset_id']}", "media_metadata.csv")
    return pd.DataFrame(nodes), pd.DataFrame(edges)

def write_docs(docs_dir):
    ops="""# STS Ops Manual (Fictional, Demo Only)

- Dispatch following: prioritize stability over aggressive chasing during draft instability.
- Draft instability: rising draft variance + damper saturation + ID fan hunting → reduce ramp, stabilize bias, verify tuning/DP transmitters, check mills.
- Restarts: expect 24–48h NSHR penalty post-outage; avoid fast cycling.
- Cooling/aux drift: persistent aux MW drift + high condenser temp → inspect CT fans/CW pumps; consider condenser cleaning.
"""
    cards="""# Troubleshooting Cards (Fictional)

- IF draft variance↑ AND damper>95% AND ID fan speed↑ THEN reduce ramp; stabilize bias; inspect tuning/sensors.
- IF condenser temp high AND aux drift persists THEN inspect CT fans/CW pumps; consider condenser cleaning.
- IF BRG2 vibration trending↑ THEN limit ramp; run spectrum; inspect alignment/pedestals; verify oil parameters.
"""
    glossary="""# Glossary (Fictional)

Dispatch Target MW: 5-minute grid requirement.
Net Generation MW: exported MW after auxiliaries.
Delta MW: Target − Net (positive shortfall).
NSHR: fuel heat input / net exported energy (Btu/kWh).
RCR: (Energy+Capacity − Penalties − FuelOverburn) / (Potential Energy+Capacity).
"""
    for fn,txt in [("ops_manual.md",ops),("troubleshooting_cards.md",cards),("glossary.md",glossary)]:
        with open(os.path.join(docs_dir,fn),"w",encoding="utf-8") as f: f.write(txt)

def write_schema_manifest(schemas_dir):
    schema={
        "asset_hierarchy.csv":["asset_id","parent_asset_id","level","system","canonical_name","aliases_json","criticality_score"],
        "sensor_registry.csv":["tag_id","asset_id","tag_name","units","sampling_frequency","aliases_json","description"],
        "events_outages_derates.csv":["event_id","unit_id","start_time","end_time","type","mw_unavailable","root_cause_category","root_cause_detail","linked_asset_id"],
        "work_orders.csv":["wo_id","asset_description_raw","long_text","maintenance_type","cost_usd","labor_hours","linked_event_id","standard_asset_id_truth"],
        "shift_logs.csv":["log_id","shift_start","shift_end","operator_role","free_text","linked_event_id","standard_asset_id_truth"],
        "emails.csv":["email_id","timestamp","from_role","to_role","subject","body","linked_event_id","standard_event_id_truth"],
        "media_metadata.csv":["media_id","timestamp","media_type","caption","linked_event_id","linked_asset_id","file_path_placeholder"],
        "alarms.csv":["alarm_id","timestamp","tag_id","severity","message","linked_event_id","standard_tag_id_truth"],
        "ontology_nodes.csv":["node_id","node_type","canonical_name","description"],
        "ontology_edges.csv":["src_node_id","edge_type","dst_node_id","evidence_ref"],
        "dispatch_timeseries_5min.csv.gz":["timestamp","unit_id","available_mw","dispatch_target_mw","net_generation_mw","delta_mw","delta_mwh","deviation_type","root_cause_category","active_event_id"],
        "scada_unit1_5min.csv.gz":["timestamp","unit_id","FurnaceDraftPressure_Pa","IDFanSpeed_pct","DamperPosition_pct","O2_pct","MillCurrent_A","TurbineVibration_mm_s","CondenserTemp_C","CondenserVacuum_kPa","AuxLoad_MW","NetGeneration_MW","draft_intensity_proxy"],
        "heat_rate_hourly.csv":["timestamp","unit_id","net_station_heat_rate","ppa_reference_heat_rate","aux_load_mw","fuel_heat_input_mmbtu","ramp_rate_mw_per_min","restart_flag","heat_rate_deviation_percent","fuel_cost_impact_usd"],
        "energy_settlement_5min.csv.gz":["timestamp","unit_id","price_usd_mwh","energy_revenue_actual","energy_revenue_potential","energy_revenue_loss"],
        "capacity_revenue_daily.csv":["date","unit_id","availability_factor","capacity_payment_actual","capacity_payment_potential","availability_penalty"],
        "penalties_daily.csv":["date","unit_id","miss_mwh","dsm_penalties_usd"],
        "fuel_cost_daily.csv":["date","unit_id","coal_cost_actual","coal_cost_reference","fuel_overburn_cost"],
        "daily_revenue_reconciliation.csv":["date","unit_id","actual_revenue_usd","max_potential_revenue_usd","revenue_loss_usd","revenue_capture_ratio","energy_rev_actual","energy_rev_potential","capacity_payment_actual","capacity_payment_potential","penalties_total_usd","fuel_overburn_cost"],
        "revenue_summary_monthly.csv":["month","unit_id","actual_total_revenue","max_potential_revenue","revenue_capture_ratio","total_revenue_loss"],
        "lost_revenue_attribution_daily.csv":["date","unit_id","loss_category","system","subsystem","component","loss_usd","linked_event_id"],
    }
    with open(os.path.join(schemas_dir,"schema_manifest.json"),"w",encoding="utf-8") as f: json.dump(schema,f,indent=2)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=str,default=".")
    ap.add_argument("--seed",type=int,default=42)
    ap.add_argument("--start",type=str,default="2023-01-01")
    ap.add_argument("--end",type=str,default="2024-12-31",help="inclusive date")
    args=ap.parse_args()
    data_dir,docs_dir,schemas_dir=mkdirs(args.out)
    rng=np.random.default_rng(args.seed)

    end_excl=(pd.Timestamp(args.end)+pd.Timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
    ts=dt_5m(args.start+"T00:00:00Z",end_excl)

    assets=build_asset_hierarchy()
    sensors=build_sensor_registry()
    events=generate_events(rng)

    dispatch, scada=generate_dispatch_scada(rng, ts, events)
    heat=heat_rate_hourly(rng, dispatch, scada, events)
    energy=energy_settlement_5m(rng, dispatch)
    cap, pen, fuel, recon, monthly=daily_finance(rng, dispatch, energy, heat)
    attr=lost_revenue_attribution(dispatch, recon, events)

    wos, logs, emails, media=unstructured_tables(rng, events)
    alarms=alarms_from_scada(rng, scada, dispatch)
    nodes, edges=build_ontology(assets, sensors, events, wos, logs, emails, media)

    assets.to_csv(os.path.join(data_dir,"asset_hierarchy.csv"),index=False)
    sensors.to_csv(os.path.join(data_dir,"sensor_registry.csv"),index=False)
    events.to_csv(os.path.join(data_dir,"events_outages_derates.csv"),index=False)
    wos.to_csv(os.path.join(data_dir,"work_orders.csv"),index=False)

    logs2=logs.copy()
    logs2["shift_start"]=pd.to_datetime(logs2["shift_start"],utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    logs2["shift_end"]=pd.to_datetime(logs2["shift_end"],utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    logs2.to_csv(os.path.join(data_dir,"shift_logs.csv"),index=False)
    emails2=emails.copy(); emails2["timestamp"]=pd.to_datetime(emails2["timestamp"],utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    emails2.to_csv(os.path.join(data_dir,"emails.csv"),index=False)
    media2=media.copy(); media2["timestamp"]=pd.to_datetime(media2["timestamp"],utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    media2.to_csv(os.path.join(data_dir,"media_metadata.csv"),index=False)
    alarms2=alarms.copy(); alarms2["timestamp"]=pd.to_datetime(alarms2["timestamp"],utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    alarms2.to_csv(os.path.join(data_dir,"alarms.csv"),index=False)

    nodes.to_csv(os.path.join(data_dir,"ontology_nodes.csv"),index=False)
    edges.to_csv(os.path.join(data_dir,"ontology_edges.csv"),index=False)

    dispatch2=dispatch.copy(); dispatch2["timestamp"]=pd.to_datetime(dispatch2["timestamp"],utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    dispatch2.to_csv(os.path.join(data_dir,"dispatch_timeseries_5min.csv.gz"),index=False,compression="gzip")
    scada2=scada.copy(); scada2["timestamp"]=pd.to_datetime(scada2["timestamp"],utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    scada2.to_csv(os.path.join(data_dir,"scada_unit1_5min.csv.gz"),index=False,compression="gzip")
    heat2=heat.copy(); heat2["timestamp"]=pd.to_datetime(heat2["timestamp"],utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    heat2.to_csv(os.path.join(data_dir,"heat_rate_hourly.csv"),index=False)
    energy2=energy.copy(); energy2["timestamp"]=pd.to_datetime(energy2["timestamp"],utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    energy2.to_csv(os.path.join(data_dir,"energy_settlement_5min.csv.gz"),index=False,compression="gzip")

    cap.to_csv(os.path.join(data_dir,"capacity_revenue_daily.csv"),index=False)
    pen.to_csv(os.path.join(data_dir,"penalties_daily.csv"),index=False)
    fuel.to_csv(os.path.join(data_dir,"fuel_cost_daily.csv"),index=False)
    recon.to_csv(os.path.join(data_dir,"daily_revenue_reconciliation.csv"),index=False)
    monthly.to_csv(os.path.join(data_dir,"revenue_summary_monthly.csv"),index=False)
    attr.to_csv(os.path.join(data_dir,"lost_revenue_attribution_daily.csv"),index=False)

    write_docs(docs_dir)
    write_schema_manifest(schemas_dir)
    print(f"✅ Generated STS demo dataset: 5-min={len(dispatch):,} hourly={len(heat):,} days={len(recon):,} months={len(monthly):,}")

if __name__=="__main__":
    main()