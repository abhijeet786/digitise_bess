# -*- coding: utf-8 -*-
"""
Created on Fri May 23 14:25:00 2025

@author: neshw
"""


# Input Parameters
capex_per_mwh = 70_00_000  # ₹60 lakh/MWh
project_life_years = 10
target_irr = 0.10  # 10%
annual_om_cost = 1_00_000  # ₹1 lakh/year
other_annual_costs = 2_00_000  # inverter, BMS, degradation etc. (assumed lump sum)

# Calculate the Capital Recovery Factor (CRF)
r = target_irr
n = project_life_years
crf = (r * (1 + r)**n) / ((1 + r)**n - 1)

# Annualized CapEx using CRF
annualized_capex = capex_per_mwh * crf

# Total Annual Cost
total_annual_cost = annualized_capex + annual_om_cost + other_annual_costs

total_annual_cost
