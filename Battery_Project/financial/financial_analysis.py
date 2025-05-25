# -*- coding: utf-8 -*-
"""
Financial Analysis Module for Battery Project
This module provides functions for calculating various financial metrics including:
- Depreciation schedules
- Unlevered cash flows
- Levered cash flows
- Project and Equity IRR calculations
"""

import numpy_financial as npf
import pandas as pd

def get_depreciation_schedule(depreciation_type, capex, residual_value_pct, years, useful_life=None, dep_rate=None):
    """
    Calculate depreciation schedule based on specified method.
    
    Args:
        depreciation_type (str): 'straight line' or 'wdv'
        capex (float): Capital expenditure
        residual_value_pct (float): Residual value percentage
        years (int): Number of years
        useful_life (int, optional): Useful life for straight line depreciation
        dep_rate (float, optional): Depreciation rate for WDV method
        
    Returns:
        list: Depreciation schedule
    """
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

def calculate_unlevered_cash_flows(capex, revenues, input_costs, om_costs, depreciation_schedule, tax_rate):
    """
    Calculate unlevered cash flows and project IRR.
    
    Args:
        capex (float): Initial capital expenditure
        revenues (list): Annual revenues
        input_costs (list): Annual input costs
        om_costs (list): Annual O&M costs
        depreciation_schedule (list): Depreciation schedule
        tax_rate (float): Tax rate
        
    Returns:
        tuple: (ebitda_list, ebit_list, tax_list, ufcf_list, project_irr)
    """
    years = len(revenues)
    ebitda_list, ebit_list, tax_list, ufcf_list = [], [], [], []

    for i in range(years):
        ebitda = revenues[i] - input_costs[i] - om_costs[i]
        depreciation = depreciation_schedule[i]
        ebit = ebitda - depreciation
        tax = max(0, ebit * tax_rate)
        ufcf = ebit - tax + depreciation
        ebitda_list.append(ebitda)
        ebit_list.append(ebit)
        tax_list.append(tax)
        ufcf_list.append(ufcf)

    cash_flows = [-capex] + ufcf_list
    project_irr = npf.irr(cash_flows)

    return ebitda_list, ebit_list, tax_list, ufcf_list, project_irr * 100

def calculate_levered_cash_flows(ufcf_list, loan_amount, interest_rate, years, equity_amount, repayment_type="equal", dscr_target=1.2):
    """
    Calculate levered cash flows and equity IRR.
    
    Args:
        ufcf_list (list): Unlevered free cash flows
        loan_amount (float): Initial loan amount
        interest_rate (float): Annual interest rate
        years (int): Number of years
        equity_amount (float): Initial equity investment
        repayment_type (str): "equal" or "sculpted"
        dscr_target (float): Debt service coverage ratio target
        
    Returns:
        tuple: (interest_list, principal_list, debt_service_list, lcf_list, equity_irr)
    """
    interest_list, principal_list, debt_service_list, lcf_list = [], [], [], []
    opening_balance = loan_amount

    if repayment_type == "equal":
        annual_principal = loan_amount / years
        for i in range(years):
            interest = opening_balance * interest_rate
            principal = annual_principal
            debt_service = interest + principal
            lcf = ufcf_list[i] - debt_service

            interest_list.append(interest)
            principal_list.append(principal)
            debt_service_list.append(debt_service)
            lcf_list.append(lcf)

            opening_balance -= principal

    elif repayment_type == "sculpted":
        for i in range(years):
            max_debt_service = ufcf_list[i] / dscr_target
            interest = opening_balance * interest_rate
            principal = max(max_debt_service - interest, 0)

            if opening_balance < principal:
                principal = opening_balance

            debt_service = interest + principal
            lcf = ufcf_list[i] - debt_service

            interest_list.append(interest)
            principal_list.append(principal)
            debt_service_list.append(debt_service)
            lcf_list.append(lcf)

            opening_balance -= principal

    equity_cash_flows = [-equity_amount] + lcf_list
    equity_irr = npf.irr(equity_cash_flows)

    return interest_list, principal_list, debt_service_list, lcf_list, equity_irr * 100

def run_financial_analysis(capex, years, residual_value_pct, revenues, input_costs, om_costs, 
                         tax_rate, depreciation_type, dep_rate, useful_life, debt_ratio, 
                         equity_ratio, interest_rate, repayment_type="sculpted", dscr_target=1.3):
    """
    Run complete financial analysis and return results as a DataFrame.
    
    Args:
        capex (float): Capital expenditure
        years (int): Number of years
        residual_value_pct (float): Residual value percentage
        revenues (list): Annual revenues
        input_costs (list): Annual input costs
        om_costs (list): Annual O&M costs
        tax_rate (float): Tax rate
        depreciation_type (str): Depreciation method
        dep_rate (float): Depreciation rate
        useful_life (int): Useful life
        debt_ratio (float): Debt ratio
        equity_ratio (float): Equity ratio
        interest_rate (float): Interest rate
        repayment_type (str): Repayment type
        dscr_target (float): DSCR target
        
    Returns:
        tuple: (DataFrame with results, project_irr, equity_irr)
    """
    loan_amount = capex * debt_ratio
    equity_amount = capex * equity_ratio

    depreciation_schedule = get_depreciation_schedule(depreciation_type, capex, residual_value_pct, 
                                                    years, useful_life, dep_rate)
    
    ebitda_list, ebit_list, tax_list, ufcf_list, project_irr = calculate_unlevered_cash_flows(
        capex, revenues, input_costs, om_costs, depreciation_schedule, tax_rate)
    
    interest_list, principal_list, debt_service_list, lcf_list, equity_irr = calculate_levered_cash_flows(
        ufcf_list, loan_amount, interest_rate, years, equity_amount,
        repayment_type=repayment_type, dscr_target=dscr_target)

    df = pd.DataFrame({
        "Year": list(range(1, years + 1)),
        "Revenue": revenues,
        "Input Cost": input_costs,
        "O&M Cost": om_costs,
        "EBITDA": ebitda_list,
        "Depreciation": depreciation_schedule,
        "EBIT": ebit_list,
        "Tax": tax_list,
        "Unlevered Free Cash Flow": ufcf_list,
        "Interest": interest_list,
        "Principal": principal_list,
        "Debt Service": debt_service_list,
        "Levered Cash Flow": lcf_list
    })

    return df, project_irr, equity_irr 

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
        repayment_type (str): Repayment type ("equal" or "sculpted")
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
    df['hourly_input_cost'] = df['charge'] * df['price']*0
    annual_input_costs = df.groupby(df['timestamp'].dt.year)['hourly_input_cost'].sum().tolist()
    
    # Ensure we have enough years of data
    if len(annual_revenues) < years:
        # Extend the last year's values to fill remaining years
        last_revenue = annual_revenues[-1]
        last_input_cost = annual_input_costs[-1]
        annual_revenues.extend([last_revenue] * (years - len(annual_revenues)))
        annual_input_costs.extend([last_input_cost] * (years - len(annual_input_costs)))
    elif len(annual_revenues) > years:
        # Truncate to the specified number of years
        annual_revenues = annual_revenues[:years]
        annual_input_costs = annual_input_costs[:years]
    
    # Calculate O&M costs (2% of capex per year)
    om_costs = [0.02 * capex] * years
    
    # Run financial analysis
    return run_financial_analysis(
        capex=capex,
        years=years,
        residual_value_pct=residual_value_pct,
        revenues=annual_revenues,
        input_costs=annual_input_costs,
        om_costs=om_costs,
        tax_rate=tax_rate,
        depreciation_type=depreciation_type,
        dep_rate=dep_rate,
        useful_life=years,
        debt_ratio=debt_ratio,
        equity_ratio=equity_ratio,
        interest_rate=interest_rate,
        repayment_type=repayment_type,
        dscr_target=dscr_target
    ) 