import pandas as pd
import numpy as np
from battery_components.battery import BatteryParameters, BatteryModel
from battery_components.grid import GridParameters, GridModel
from battery_components.solar import SolarParameters, SolarModel
from battery_components.optimization_engine import OptimizationEngine
from applications.peak_shaving import PeakShavingApplication
import linopy

def extract_constraints_to_file():
    # Create a sample load profile
    load_profile = pd.Series(
        np.random.uniform(0.5, 1.0, 8760),
        index=pd.date_range('2024-01-01', periods=8760, freq='h')
    )
    
    # Initialize parameters
    battery_params = BatteryParameters(
        capacity=None,  # Optimal sizing
        charge_efficiency=0.95,
        discharge_efficiency=0.95,
        standing_loss=0.005,
        c_rate=0.5,
        capex_per_mwh=15000,
        lifetime_years=10,
        has_dedicated_inverter=True
    )
    
    solar_params = SolarParameters(
        capacity=0.0,
        generation_profile=pd.Series(0.0, index=load_profile.index),
        capex_per_mw=1000000,
        lifetime_years=25,
        inverter_capacity=0.0,
        latitude=28.6139,  # Adding required latitude
        longitude=77.2090  # Adding required longitude
    )
    
    # Create price profile based on solar generation
    price_profile = pd.Series(
        np.where(load_profile > load_profile.mean(),
                20.0,  # Lower price during high generation hours
                100.0),  # Higher price during low generation hours
        index=load_profile.index
    )
    
    grid_params = GridParameters(
        max_import=1.0,
        max_export=1.0,
        price_profile=price_profile,
        connection_cost=50000
    )
    
    # Create optimization engine
    engine = OptimizationEngine(
        battery_params=battery_params,
        solar_params=solar_params,
        grid_params=grid_params,
        discount_rate=0.08
    )
    
    # Create time index
    time = pd.date_range('2024-01-01', periods=8760, freq='h')
    
    # Initialize optimization model
    model = linopy.Model()
    
    # Add variables from each component
    battery_vars = engine.battery_model.add_battery_variables(model, time)
    solar_vars = engine.solar_model.add_solar_variables(model, time)
    grid_vars = engine.grid_model.add_grid_variables(model, time)
    
    # Add constraints from each component
    engine.battery_model.add_battery_constraints(model, time, battery_vars)
    engine.solar_model.add_solar_constraints(
        model, time, solar_vars,
        engine.battery_model.params.has_dedicated_inverter,
        battery_vars['capacity']
    )
    engine.grid_model.add_grid_constraints(
        model, time, grid_vars,
        solar_vars['generation'],
        battery_vars['charge'],
        battery_vars['discharge']
    )
    
    # Set objective
    engine._set_objective(model, battery_vars, solar_vars, grid_vars)
    
    # Extract constraints to file
    with open('constraints.txt', 'w') as f:
        f.write("=== Optimization Constraints ===\n\n")
        
        f.write("Battery Constraints:\n")
        f.write("1. State of Charge (SOC) limits: 0 <= SOC <= 1\n")
        f.write("2. Charge/Discharge limits: Charge <= C-rate * Capacity\n")
        f.write("3. SOC evolution: SOC[t] = SOC[t-1] + (Charge[t] * η_charge - Discharge[t]/η_discharge) * Δt\n")
        f.write("4. Initial SOC = Final SOC\n\n")
        
        f.write("Solar Constraints:\n")
        f.write("1. Generation <= Generation Profile\n")
        if engine.battery_model.params.has_dedicated_inverter:
            f.write("2. Generation <= Inverter Capacity\n")
        else:
            f.write("2. Generation + Charge + Discharge <= Battery C-rate * Capacity\n\n")
        
        f.write("Grid Constraints:\n")
        f.write(f"1. Import limit: Import <= {grid_params.max_import} MW\n")
        f.write(f"2. Export limit: Export <= {grid_params.max_export} MW\n")
        f.write("3. Power balance: Load + Charge = Generation + Discharge + Import - Export\n\n")
        
        f.write("Peak Shaving Constraints:\n")
        f.write("1. Evening peak hours (18:00-22:00): Import <= 50% of max import\n")
        
        f.write("\n=== Objective Function ===\n")
        f.write("Minimize: Battery Cost + Solar Cost + Grid Cost + Import Cost - Export Revenue\n")
        
        f.write("\n=== Component Parameters ===\n")
        f.write(f"Battery:\n")
        f.write(f"- Capacity: {battery_params.capacity if battery_params.capacity else 'Optimal'} MWh\n")
        f.write(f"- Charge Efficiency: {battery_params.charge_efficiency}\n")
        f.write(f"- Discharge Efficiency: {battery_params.discharge_efficiency}\n")
        f.write(f"- Standing Loss: {battery_params.standing_loss}\n")
        f.write(f"- C-rate: {battery_params.c_rate}\n")
        f.write(f"- CAPEX: ${battery_params.capex_per_mwh:,.2f}/MWh\n")
        f.write(f"- Lifetime: {battery_params.lifetime_years} years\n")
        f.write(f"- Dedicated Inverter: {battery_params.has_dedicated_inverter}\n\n")
        
        f.write(f"Solar:\n")
        f.write(f"- Capacity: {solar_params.capacity} MW\n")
        f.write(f"- CAPEX: ${solar_params.capex_per_mw:,.2f}/MW\n")
        f.write(f"- Lifetime: {solar_params.lifetime_years} years\n")
        f.write(f"- Inverter Capacity: {solar_params.inverter_capacity} MW\n\n")
        
        f.write(f"Grid:\n")
        f.write(f"- Max Import: {grid_params.max_import} MW\n")
        f.write(f"- Max Export: {grid_params.max_export} MW\n")
        f.write(f"- Connection Cost: ${grid_params.connection_cost:,.2f}\n")
        
        f.write("\n=== Price Profile ===\n")
        f.write(f"Peak Price: ${price_profile.max():.2f}/MWh\n")
        f.write(f"Off-peak Price: ${price_profile.min():.2f}/MWh\n")
        f.write(f"Average Price: ${price_profile.mean():.2f}/MWh\n")

if __name__ == "__main__":
    extract_constraints_to_file()
    print("Constraints have been written to 'constraints.txt'") 