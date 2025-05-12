import os
import sys

# Add the project root to PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

import pandas as pd
import numpy as np
from applications.peak_shaving import PeakShavingApplication
from applications.solar_clipping import SolarClippingApplication
from applications.grid_export_target import GridExportTargetApplication
from battery_components.solar import SolarParameters

def main():
    # Create the application with optimal battery sizing
    # app = PeakShavingApplication(
    #     # Battery parameters
    #     battery_capacity=None,  # MWh, None for optimal sizing
    #     charge_efficiency=0.95,
    #     discharge_efficiency=0.95,
    #     standing_loss=0.005,
    #     c_rate=0.5,
    #     battery_capex_per_mwh=15000,
    #     battery_lifetime_years=10,
    #     has_dedicated_inverter=True,
        
    #     # Solar parameters
    #     solar_capacity=20.0,    # MW
    #     solar_capex_per_mw=1000000,
    #     solar_lifetime_years=20,
    #     solar_inverter_capacity=5.0,
        
    #     # Grid parameters
    #     max_export=100.0,       # MW
    #     grid_connection_cost=50000,  # $/MW
        
    #     # Economic parameters
    #     discount_rate=0.08,
    #     peak_price=30.0,        # $/MWh (higher price during non-solar hours)
    #     offpeak_price=20.0,     # $/MWh (lower price during solar hours)
        
    #     # Location parameters
    #     latitude=28.6139,       # Default to New Delhi coordinates
    #     longitude=77.2090,
        
    #     # API parameters
    #     api_token='ec07a7a7ee0b18ae2f6f28fc237a58dfe4b52b5a',  # Renewables.ninja API token
    #     start_date='2023-01-01',  # Start of 2023
    #     end_date='2023-12-31'    # End of 2023
    # )
    # app = SolarClippingApplication(
    #     battery_capacity=None,  # MWh, None for optimal sizing
    #     solar_capacity=20.0,    # MW
    #     inverter_capacity=10,
    #     max_export=100.0,        # MW
    #     discount_rate=0.08,
    #     peak_price=30.0,       # $/MWh (higher price during non-solar hours)
    #     offpeak_price=30.0,     # $/MWh (lower price during solar hours)
    #     latitude=28.6139,       # Default to New Delhi coordinates
    #     longitude=77.2090,
    #     api_token='ec07a7a7ee0b18ae2f6f28fc237a58dfe4b52b5a',  # Renewables.ninja API token
    #     start_date='2023-01-01',  # Start of 2023
    #     end_date='2023-12-31',    # End of 2023
    #     clip_threshold=0.8  # Clip at 80% of solar capacity
    # ) 
    app = GridExportTargetApplication(
        # Battery parameters
        battery_capacity=None,  # MWh, None for optimal sizing
        charge_efficiency=0.95,
        discharge_efficiency=0.95,
        standing_loss=0.005,
        c_rate=0.5,
        battery_capex_per_mwh=15000,
        battery_lifetime_years=10,
        has_dedicated_inverter=True,
        
        # Solar parameters
        solar_capacity=30.0,    # MW - reduced from 1000 MW to match max export
        solar_capex_per_mw=1000000,
        solar_lifetime_years=20,
        solar_inverter_capacity=5.0,
        data_source='csv',  # Use CSV data source instead of Renewables.ninja
        
        # Grid parameters
        max_export=100.0,       # MW
        grid_connection_cost=50000,  # $/MW
        export_target=5,      # MW - reduced from 5 MW to be more achievable
        
        # Economic parameters
        discount_rate=0.08,
        peak_price=30.0,        # $/MWh
        offpeak_price=20.0,     # $/MWh
        
        # Location parameters
        latitude=28.6139,       # Default to New Delhi coordinates
        longitude=77.2090,
        
        # API parameters
        start_date='2023-01-01',  # Start of 2023
        end_date='2023-12-31'    # End of 2023
    )

    # Print solar generation profile
    print("\nSolar Generation Profile (2023):")
    print("-------------------------------")
    generation_profile = app.solar_model.generation_profile
    print(f"Total Annual Generation: {generation_profile.sum():.2f} MWh")
    print(f"Average Daily Generation: {generation_profile.mean():.2f} MW")
    print(f"Peak Generation: {generation_profile.max():.2f} MW")
    print("\nMonthly Generation:")
    monthly_gen = generation_profile
    monthly_gen.to_csv("monthly_gen.csv")
    print(monthly_gen)

    # Print price profile
    print("\nPrice Profile (2023):")
    print("--------------------")
    price_profile = app.grid_params.price_profile
    print(f"Average Price: ${price_profile.mean():.2f}/MWh")
    print(f"Maximum Price: ${price_profile.max():.2f}/MWh")
    print(f"Minimum Price: ${price_profile.min():.2f}/MWh")
    print("\nHourly Prices:")
    price_profile.to_csv("price_profile.csv")
    print(price_profile)

    global results, summary
    # Run the optimization
    results = app.run_optimization()

    # Get summary of results
    summary = app.get_summary(results)

    # Print results based on application type
    if isinstance(app, GridExportTargetApplication):
        print("\nGrid Export Target Results:")
        print("-------------------------")
        print(f"Export Target: {results['grid']['export_target']:.2f} MW")
        print(f"Export Compliance: {results['grid']['export_compliance']:.1f}%")
        print(f"Grid Revenue: ${results['revenue']:,.2f}")
        print(f"Net Cost: ${results['net_cost']:,.2f}")
    elif isinstance(app, SolarClippingApplication):
        print("\nClipping Results:")
        print("----------------")
        print(f"Clipping Threshold: {results['clipping']['threshold']:.2f}")
        print(f"Clipped Energy: {results['clipping']['clipped_energy']:.2f} MWh")
    else:  # PeakShavingApplication
        print("\nPeak Shaving Results:")
        print("-------------------")
        print(f"Battery Capacity: {results['battery']['capacity']:.2f} MWh")
        print(f"Grid Revenue: ${results['revenue']:,.2f}")
        print(f"Net Cost: ${results['net_cost']:,.2f}")

    # Create DataFrame with results
    # Create timestamp index for the year
    timestamps = pd.date_range(start='2023-01-01', periods=len(results['battery']['soc']), freq='H')
    global df
    df = pd.DataFrame({
        'timestamp': timestamps,
        'charge': results['battery']['charge'],
        'discharge': results['battery']['discharge'],
        'soc': results['battery']['soc'],
        'solar_generation': results['solar']['generation'],
        'grid_export': results['grid']['export']
    })

    # Export to Excel
    df.to_excel('battery_simulation_results.xlsx', index=False)

if __name__ == "__main__":
    main()

