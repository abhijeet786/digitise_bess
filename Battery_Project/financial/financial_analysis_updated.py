# -*- coding: utf-8 -*-
"""
Created on Mon May 19 20:57:47 2025

@author: dasdu
"""

import numpy_financial as npf
import pandas as pd

# -----------------------------
# Core Functions
# -----------------------------

def get_depreciation_schedule(depreciation_type, capex, residual_value_pct, years, useful_life=None, dep_rate=None):
    depreciation_schedule = []
    depreciable_base = capex * (1 - residual_value_pct)

    if depreciation_type.lower() == 'straight line':
        depreciation = depreciable_base / useful_life
        depreciation_schedule = [depreciation] * years
    elif depreciation_type.lower() == 'wdv':
        opening_value = depreciable_base
        for _ in range(years):
            dep = opening_value * dep_rate
            depreciation_schedule.append(dep)
            opening_value -= dep
    else:
        raise ValueError("Depreciation type must be 'straight line' or 'wdv'.")
    return depreciation_schedule

def calculate_interest_schedule(loan_amount, interest_rate, debt_tenure, repayment_type, dscr_target, ebitda_list=None):
    interest_schedule = []
    principal_schedule = []
    opening_balance = loan_amount

    if repayment_type == "equal":
        annual_principal = loan_amount / debt_tenure
        for i in range(debt_tenure):
            interest = opening_balance * interest_rate
            principal = annual_principal
            interest_schedule.append(interest)
            principal_schedule.append(principal)
            opening_balance -= principal

    elif repayment_type == "emi":
        emi = npf.pmt(interest_rate, debt_tenure, -loan_amount)
        for i in range(debt_tenure):
            interest = opening_balance * interest_rate
            principal = emi - interest
            interest_schedule.append(interest)
            principal_schedule.append(principal)
            opening_balance -= principal

    elif repayment_type == "sculpted":
        for i in range(debt_tenure):
            max_debt_service = ebitda_list[i] / dscr_target
            interest = opening_balance * interest_rate
            principal = max(max_debt_service - interest, 0)
            if opening_balance < principal:
                principal = opening_balance
            interest_schedule.append(interest)
            principal_schedule.append(principal)
            opening_balance -= principal

        if round(sum(principal_schedule), 2) < round(loan_amount, 2):
            print("⚠️ WARNING: Total principal paid is less than loan amount — sculpted repayment not sufficient with given DSCR target.")

    # Fill remaining years with 0s if project life > debt tenure
    remaining_years = len(ebitda_list) - debt_tenure
    interest_schedule += [0] * remaining_years
    principal_schedule += [0] * remaining_years

    return interest_schedule, principal_schedule

def calculate_unlevered_cash_flows(capex, revenues, input_costs, om_costs, depreciation_schedule, interest_schedule, tax_rate):
    years = len(revenues)
    ebitda_list, ebit_list, tax_list, ufcf_list = [], [], [], []

    for i in range(years):
        ebitda = revenues[i]  - om_costs[i]  #-input_costs[i]
        depreciation = depreciation_schedule[i]
        ebit = ebitda - depreciation
        interest = interest_schedule[i]
        taxable_income = ebit - interest
        tax = max(0, taxable_income * tax_rate)
        ufcf = ebitda - tax
        ebitda_list.append(ebitda)
        ebit_list.append(ebit)
        tax_list.append(tax)
        ufcf_list.append(ufcf)

    cash_flows = [-capex] + ufcf_list
    project_irr = npf.irr(cash_flows)

    return ebitda_list, ebit_list, tax_list, ufcf_list, project_irr * 100

def calculate_levered_cash_flows(ufcf_list, interest_list, principal_list, equity_amount):
    lcf_list = []
    for i in range(len(ufcf_list)):
        lcf = ufcf_list[i] - interest_list[i] - principal_list[i]
        lcf_list.append(lcf)

    equity_cash_flows = [-equity_amount] + lcf_list
    equity_irr = npf.irr(equity_cash_flows)

    return lcf_list, equity_irr * 100

def analyze_battery_project(simulation_results, capex, years=10, residual_value_pct=0.1, 
                          tax_rate=0.25, depreciation_type='straight line', dep_rate=0.4,
                          debt_ratio=0.7, equity_ratio=0.3, interest_rate=0.10,
                          repayment_type="sculpted", dscr_target=1.3):
    """
    Analyze financial metrics for a battery project based on simulation results.
    
    Args:
        simulation_results (dict): Dictionary containing simulation results including:
            - battery: dict with 'capacity', 'charge', 'discharge', 'soc'
            - grid: dict with 'export', 'price_profile'
            - revenue: float
            - net_cost: float
        capex (float): Total capital expenditure
        years (int): Project lifetime
        residual_value_pct (float): Residual value percentage
        tax_rate (float): Tax rate
        depreciation_type (str): Depreciation method ('straight line' or 'wdv')
        dep_rate (float): Depreciation rate for WDV method
        debt_ratio (float): Debt ratio
        equity_ratio (float): Equity ratio
        interest_rate (float): Interest rate
        repayment_type (str): Repayment type ("equal", "emi", or "sculpted")
        dscr_target (float): Debt service coverage ratio target
        
    Returns:
        tuple: (DataFrame with results, project_irr, equity_irr)
    """
    # Calculate annual revenues from simulation results
    df = pd.DataFrame({
        'timestamp': pd.date_range(start='2023-01-01', periods=len(simulation_results['battery']['soc']), freq='h'),
        'charge': simulation_results['battery']['charge'],
        'discharge': simulation_results['battery']['discharge'],
        'grid_export': simulation_results['grid']['export'],
        'price': simulation_results['grid']['price_profile'].values[:len(simulation_results['battery']['soc'])]
    })
    
    # Calculate annual revenues
    df['hourly_revenue'] = df['grid_export'] * df['price']
    annual_revenues = df.groupby(df['timestamp'].dt.year)['hourly_revenue'].sum().tolist()
    
    # Calculate annual input costs (charging costs)
    df['hourly_input_cost'] = df['charge'] * df['price']
    annual_input_costs = df.groupby(df['timestamp'].dt.year)['hourly_input_cost'].sum().tolist()
    
    # Ensure we have enough years of data
    if len(annual_revenues) < years:
        last_revenue = annual_revenues[-1]
        last_input_cost = annual_input_costs[-1]
        annual_revenues.extend([last_revenue] * (years - len(annual_revenues)))
        annual_input_costs.extend([last_input_cost] * (years - len(annual_input_costs)))
    elif len(annual_revenues) > years:
        annual_revenues = annual_revenues[:years]
        annual_input_costs = annual_input_costs[:years]
    
    # Calculate O&M costs (2% of capex per year)
    om_costs = [0.02 * capex] * years
    
    # Print EBITDA components
    print("\nEBITDA Components (First Year):")
    print("-------------------------")
    print(f"Revenue: {annual_revenues[0]:,.2f} ₹")
    print(f"Input Costs: {annual_input_costs[0]:,.2f} ₹")
    print(f"O&M Costs: {om_costs[0]:,.2f} ₹")
    print(f"EBITDA: {annual_revenues[0] - annual_input_costs[0] - om_costs[0]:,.2f} ₹")
    
    # Calculate loan and equity amounts
    loan_amount = capex * debt_ratio
    equity_amount = capex * equity_ratio
    debt_tenure = min(years, 10)  # Debt tenure capped at 10 years
    
    # Run financial calculations
    depreciation_schedule = get_depreciation_schedule(
        depreciation_type, capex, residual_value_pct, years, years, dep_rate)
    
    temp_ebitda_list = [annual_revenues[i] - annual_input_costs[i] - om_costs[i] for i in range(years)]
    interest_list, principal_list = calculate_interest_schedule(
        loan_amount, interest_rate, debt_tenure, repayment_type, dscr_target, temp_ebitda_list)
    
    ebitda_list, ebit_list, tax_list, ufcf_list, project_irr = calculate_unlevered_cash_flows(
        capex, annual_revenues, annual_input_costs, om_costs, 
        depreciation_schedule, interest_list, tax_rate)
    
    lcf_list, equity_irr = calculate_levered_cash_flows(
        ufcf_list, interest_list, principal_list, equity_amount)
    
    # Create financial results DataFrame
    financial_df = pd.DataFrame({
        "Year": list(range(1, years + 1)),
        "CAPEX (₹)": [capex] + [0] * (years - 1),  # CAPEX in year 1, 0 for other years
        "Loan Amount (₹)": [loan_amount] + [0] * (years - 1),  # Loan in year 1
        "Equity Amount (₹)": [equity_amount] + [0] * (years - 1),  # Equity in year 1
        "Revenue (₹)": annual_revenues,
        "Input Costs (₹)": annual_input_costs,
        "O&M Costs (₹)": om_costs,
        "EBITDA (₹)": ebitda_list,
        "Depreciation (₹)": depreciation_schedule,
        "EBIT (₹)": ebit_list,
        "Tax (₹)": tax_list,
        "Interest (₹)": interest_list,
        "Principal (₹)": principal_list,
        "Unlevered Cash Flow (₹)": ufcf_list,
        "Levered Cash Flow (₹)": lcf_list
    })
    
    return financial_df, project_irr, equity_irr

# # -----------------------------
# # Inputs (INR-Based)
# # -----------------------------

# capex = 160*83*1000*2*0.7             #Consider impact of VGF here directly (30% of CAPEX)
# years = 12
# debt_tenure = 10  
# residual_value_pct = 0.1
# revenues = [245000*12] * years
# input_costs = [0] * years
# om_costs = [0.02 * capex * 1.3] * years    #0.3 added to discount the VGF
# tax_rate = 0.25
# depreciation_type = 'straight line'  #straight line or wdv
# dep_rate = 0.4             #enter only if you have selected wdv
# useful_life = years

# debt_ratio = 0.7
# loan_amount = capex * debt_ratio
# equity_amount = capex - loan_amount
# interest_rate = 0.08
# repayment_type = "sculpted"    #equal or emi or sculpted
# dscr_target = 1.15           #enter only if you have selected sculpted

# # -----------------------------
# # Run Calculations
# # -----------------------------

# depreciation_schedule = get_depreciation_schedule(depreciation_type, capex, residual_value_pct, years, useful_life, dep_rate)
# temp_ebitda_list = [revenues[i] - input_costs[i] - om_costs[i] for i in range(years)]
# interest_list, principal_list = calculate_interest_schedule(loan_amount, interest_rate, debt_tenure, repayment_type, dscr_target, temp_ebitda_list)
# ebitda_list, ebit_list, tax_list_unlevered, ufcf_list, project_irr = calculate_unlevered_cash_flows(
#     capex, revenues, input_costs, om_costs, depreciation_schedule, interest_list, tax_rate)
# lcf_list, equity_irr = calculate_levered_cash_flows(ufcf_list, interest_list, principal_list, equity_amount)

# # -----------------------------
# # Output Results
# # -----------------------------

# df = pd.DataFrame({
#     "Year": list(range(1, years + 1)),
#     "Revenue (₹)": revenues,
#     "EBITDA (₹)": ebitda_list,
#     "Depreciation (₹)": depreciation_schedule,
#     "EBIT (₹)": ebit_list,
#     "Tax (₹)": tax_list_unlevered,
#     "Interest (₹)": interest_list,
#     "Principal (₹)": principal_list,
#     "Unlevered Cash Flow (₹)": ufcf_list,
#     "Levered Cash Flow (₹)": lcf_list
# })

# df.to_csv("project_cash_flow_summary.csv", index=False)

# print("\n✅ Cash flow results exported to 'project_cash_flow_summary.csv'")
# print(f"📊 Project IRR (Unlevered): {project_irr:.2f}%")
# print(f"📈 Equity IRR (Levered): {equity_irr:.2f}%") 