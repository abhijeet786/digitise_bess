import pandas as pd
from applications.solar_clipping import SolarClippingApp
from battery_components.battery import BatteryParameters
from battery_components.solar import SolarParameters
from battery_components.grid import GridParameters

def main():
    # Create price profile (example data)
    time_index = pd.date_range('2023-01-01', periods=8760, freq='h')
    price_profile = pd.Series(
        [100.0 if hour in range(17, 22) else 20.0 for hour in range(24)] * 365,
        index=time_index
    )
    
    # Initialize parameters
    battery_params = BatteryParameters(
        capacity=None,  # Let optimizer determine optimal capacity
        charge_efficiency=0.95,
        discharge_efficiency=0.95,
        standing_loss=0.005,
        c_rate=0.5,
        capex_per_mwh=150,
        lifetime_years=10,
        has_dedicated_inverter=False
    )
    
    solar_params = SolarParameters(
        latitude=37.7749,
        longitude=-122.4194,
        capacity=10.0,  # MW
        tilt=25.0,
        azimuth=180.0,
        system_loss=0.1,
        tracking=0,
        inverter_capacity=5.0,
        battery_has_dedicated_inverter=False,#Has to be false for clipping
        api_token=None,  # Add your Renewables.ninja API token here
        start_date='2023-01-01',
        end_date='2023-12-31',
        capex_per_mw=1000000,
        lifetime_years=25
    )
    
    grid_params = GridParameters(
        max_import=5.0,  # MW
        max_export=5.0,  # MW
        price_profile=price_profile,
        connection_cost=100000,  # $/MW
        lifetime_years=20
    )
    
    # Create and run application
    app = SolarClippingApp(
        battery_params=battery_params,
        solar_params=solar_params,
        grid_params=grid_params,
        clip_threshold=0.8,  # Clip at 80% of solar capacity
        discount_rate=0.08
    )
    
    # Run optimization
    results = app.run_optimization()
    
    # Print results
    print("\nOptimization Results:")
    print(f"Battery Capacity: {results['battery']['capacity']:.2f} MWh")

    print(f"Total Clipped Energy: {results['clipping']['clipped_energy']:.2f} MWh")
    print(f"Annual Revenue from Grid: ${(results['grid']['export'] * price_profile).sum():.2f}")

if __name__ == "__main__":
    main() 