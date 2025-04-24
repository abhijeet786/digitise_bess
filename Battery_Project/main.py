import os
import sys

# Add the project root to PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

import pandas as pd
import numpy as np
# from applications.peak_shaving import PeakShavingApplication
from applications.solar_clipping import SolarClippingApplication
from battery_components.solar import SolarParameters

def main():
    # Create the application with optimal battery sizing
    # app = PeakShavingApplication(
    #     battery_capacity=None,  # MWh, None for optimal sizing
    #     solar_capacity=20.0,    # MW
    #     max_export=100.0,        # MW
    #     discount_rate=0.08,
    #     peak_price=30.0,       # $/MWh (higher price during non-solar hours)
    #     offpeak_price=20.0,     # $/MWh (lower price during solar hours)
    #     latitude=28.6139,       # Default to New Delhi coordinates
    #     longitude=77.2090,
    #     api_token='ec07a7a7ee0b18ae2f6f28fc237a58dfe4b52b5a',  # Renewables.ninja API token
    #     start_date='2023-01-01',  # Start of 2023
    #     end_date='2023-12-31'    # End of 2023
    # )
    app = SolarClippingApplication(
        battery_capacity=None,  # MWh, None for optimal sizing
        solar_capacity=20.0,    # MW
        inverter_capacity=10,
        max_export=100.0,        # MW
        discount_rate=0.08,
        peak_price=30.0,       # $/MWh (higher price during non-solar hours)
        offpeak_price=30.0,     # $/MWh (lower price during solar hours)
        latitude=28.6139,       # Default to New Delhi coordinates
        longitude=77.2090,
        api_token='ec07a7a7ee0b18ae2f6f28fc237a58dfe4b52b5a',  # Renewables.ninja API token
        start_date='2023-01-01',  # Start of 2023
        end_date='2023-12-31',    # End of 2023
        clip_threshold=0.8  # Clip at 80% of solar capacity
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


    # Print clipping results if available
    if 'clipping' in results:
        print("\nClipping Results:")
        print("----------------")
        print(f"Clipping Threshold: {results['clipping']['threshold']:.2f}")
        print(f"Clipped Energy: {results['clipping']['clipped_energy']:.2f} MWh")

if __name__ == "__main__":
    main()

