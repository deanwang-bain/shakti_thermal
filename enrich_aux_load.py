#!/usr/bin/env python3
"""
Enrich heat rate data to make auxiliary load correlate with anomalies/sudden changes.
This modifies heat_rate_daily.csv and heat_rate_monthly.csv in place.
"""

import pandas as pd
import numpy as np

# Read daily heat rate data
df_daily = pd.read_csv('data/heat_rate_daily.csv')

# Create a random generator for reproducibility
rng = np.random.RandomState(42)

# Identify anomaly and sudden change rows
anomalies = df_daily['anomaly_flag'] == True
sudden_changes = df_daily['sudden_change_flag'] == True

# For anomalies and sudden changes, increase aux load by 15-35%
for idx in df_daily[anomalies | sudden_changes].index:
    base_aux = df_daily.loc[idx, 'aux_load_mw']
    # Increase by random amount between 15-35%
    spike_factor = 1 + rng.uniform(0.15, 0.35)
    df_daily.loc[idx, 'aux_load_mw'] = base_aux * spike_factor

# Also add some variety: for some normal days, reduce aux load slightly
normal_days = ~(anomalies | sudden_changes)
normal_indices = df_daily[normal_days].index
# Random 20% of normal days get slightly reduced aux load
sample_size = int(len(normal_indices) * 0.2)
reduce_indices = rng.choice(normal_indices, size=sample_size, replace=False)
for idx in reduce_indices:
    base_aux = df_daily.loc[idx, 'aux_load_mw']
    reduce_factor = 1 - rng.uniform(0.05, 0.15)
    df_daily.loc[idx, 'aux_load_mw'] = base_aux * reduce_factor

# Save updated daily data
df_daily.to_csv('data/heat_rate_daily.csv', index=False)
print(f"✓ Updated heat_rate_daily.csv with correlated auxiliary load")
print(f"  - {(anomalies | sudden_changes).sum()} anomaly/sudden-change days with increased aux load")

# Update monthly data (aggregate from daily)
df_daily['month'] = pd.to_datetime(df_daily['date']).dt.to_period('M').astype(str)
monthly_aux = df_daily.groupby('month')['aux_load_mw'].mean().reset_index()

# Read existing monthly data
df_monthly = pd.read_csv('data/heat_rate_monthly.csv')

# Update aux_load_mw values
df_monthly = df_monthly.merge(monthly_aux, on='month', how='left', suffixes=('', '_new'))
df_monthly['aux_load_mw'] = df_monthly['aux_load_mw_new'].fillna(df_monthly['aux_load_mw'])
df_monthly = df_monthly.drop(columns=['aux_load_mw_new'])

# Save updated monthly data
df_monthly.to_csv('data/heat_rate_monthly.csv', index=False)
print(f"✓ Updated heat_rate_monthly.csv with aggregated auxiliary load")
