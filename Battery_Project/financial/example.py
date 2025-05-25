# -*- coding: utf-8 -*-
"""
Example script demonstrating how to use the financial analysis module
"""

from financial_analysis import run_financial_analysis

def main():
    # Example parameters
    capex = 100  # Capital expenditure
    years = 10   # Project lifetime
    residual_value_pct = 0.1  # 10% residual value
    revenues = [25, 26, 26, 27, 27, 26, 25, 24, 23, 22]  # Annual revenues
    input_costs = [2, 2, 2.2, 2.3, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8]  # Annual input costs
    om_costs = [0.02 * capex] * years  # O&M costs as 2% of capex
    tax_rate = 0.25  # 25% tax rate
    
    # Depreciation parameters
    depreciation_type = 'straight line'  # or 'wdv'
    dep_rate = 0.4  # Used for WDV method
    useful_life = years
    
    # Financing parameters
    debt_ratio = 0.7  # 70% debt
    equity_ratio = 0.3  # 30% equity
    interest_rate = 0.10  # 10% interest rate
    repayment_type = "sculpted"  # or "equal"
    dscr_target = 1.3  # Debt service coverage ratio target
    
    # Run financial analysis
    df, project_irr, equity_irr = run_financial_analysis(
        capex=capex,
        years=years,
        residual_value_pct=residual_value_pct,
        revenues=revenues,
        input_costs=input_costs,
        om_costs=om_costs,
        tax_rate=tax_rate,
        depreciation_type=depreciation_type,
        dep_rate=dep_rate,
        useful_life=useful_life,
        debt_ratio=debt_ratio,
        equity_ratio=equity_ratio,
        interest_rate=interest_rate,
        repayment_type=repayment_type,
        dscr_target=dscr_target
    )
    
    # Print results
    print("\nDetailed Cash Flow Table:")
    print(df.to_string(index=False))
    print(f"\nProject IRR (Unlevered): {project_irr:.2f}%")
    print(f"Equity IRR (Levered): {equity_irr:.2f}%")

if __name__ == "__main__":
    main() 