from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import linopy
import xarray as xr
from datetime import datetime, timedelta

# Component Layer Classes
@dataclass
class BatteryComponent:
    """Battery system component parameters"""
    capacity: float  # MWh
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    standing_loss: float = 0.005
    c_rate: float = 0.5
    capex_per_mwh: float = 15000  # $/MWh
    lifetime_years: int = 10
    has_dedicated_inverter: bool = True

@dataclass
class RenewableGeneratorComponent:
    """Renewable energy generator component parameters"""
    capacity: float  # MW
    generation_profile: pd.Series  # Time series of generation
    capex_per_mw: float
    lifetime_years: int
    inverter_capacity: float  # MW
    system_loss: float = 0.1

@dataclass
class GridInterfaceComponent:
    """Grid interface component parameters"""
    max_export_capacity: float  # MW
    electricity_price_peak: float  # $/MWh
    electricity_price_offpeak: float  # $/MWh
    peak_hours: Dict[str, List[int]]  # e.g., {"morning": [6,9], "evening": [18,22]}

# Application Layer Classes
class BatteryApplication:
    """Base class for battery applications"""
    def __init__(
        self,
        battery: BatteryComponent,
        renewable: RenewableGeneratorComponent,
        grid: GridInterfaceComponent,
        discount_rate: float
    ):
        self.battery = battery
        self.renewable = renewable
        self.grid = grid
        self.discount_rate = discount_rate

    def add_component_constraints(self, model: linopy.Model, time: pd.Index) -> None:
        """Add component-level constraints"""
        raise NotImplementedError

    def add_application_constraints(self, model: linopy.Model, time: pd.Index) -> None:
        """Add application-specific constraints"""
        raise NotImplementedError

    def set_objective(self, model: linopy.Model) -> None:
        """Set optimization objective"""
        raise NotImplementedError

class PeakShavingApplication(BatteryApplication):
    """Battery application for peak shaving"""
    def add_component_constraints(self, model: linopy.Model, time: pd.Index) -> None:
        # Add battery constraints
        charge = model.add_variables(name="charge", coords={"time": time}, lower=0)
        discharge = model.add_variables(name="discharge", coords={"time": time}, lower=0)
        soc = model.add_variables(name="soc", coords={"time": time}, lower=0)

        # Battery SOC balance
        t0 = time[0]
        expr0 = soc.at[t0] - charge.at[t0] * self.battery.charge_efficiency + \
                discharge.at[t0] / self.battery.discharge_efficiency
        model.add_constraints(expr0 == 0, name="soc_balance_0")

        # SOC balance for remaining timesteps
        t_later = time[1:]
        soc_expr = soc.sel(time=t_later)
        soc_prev = soc.sel(time=t_later - 1) * (1 - self.battery.standing_loss)
        charge_t = charge.sel(time=t_later)
        discharge_t = discharge.sel(time=t_later)

        expr_later = soc_expr - soc_prev - charge_t * self.battery.charge_efficiency + \
                    discharge_t / self.battery.discharge_efficiency
        model.add_constraints(expr_later == 0, name="soc_balance_rest")

        # Add renewable constraints
        generation = model.add_variables(
            name="generation",
            coords={"time": time},
            lower=0,
            upper=self.renewable.generation_profile
        )

        # Add inverter constraints
        if self.battery.has_dedicated_inverter:
            model.add_constraints(
                charge + discharge <= self.battery.c_rate * self.battery.capacity,
                name="battery_inverter_limit"
            )
            model.add_constraints(
                generation <= self.renewable.inverter_capacity,
                name="generation_inverter_limit"
            )
        else:
            model.add_constraints(
                charge + discharge + generation <= self.battery.c_rate * self.battery.capacity,
                name="shared_inverter_limit"
            )

        # Add grid export constraints
        export = model.add_variables(
            name="export",
            coords={"time": time},
            lower=0,
            upper=self.grid.max_export_capacity
        )

        # Export definition
        model.add_constraints(
            export == generation - charge + discharge,
            name="export_definition"
        )

    def add_application_constraints(self, model: linopy.Model, time: pd.Index) -> None:
        # Peak shaving specific constraints
        price_profile = self._create_price_profile(len(time))
        peak_mask = price_profile == self.grid.electricity_price_peak
        
        # Ensure battery discharges during peak hours
        discharge = model.variables["discharge"]
        model.add_constraints(
            discharge.sel(time=time[peak_mask]) >= 0.1 * self.battery.capacity,
            name="peak_shaving_constraint"
        )

    def set_objective(self, model: linopy.Model) -> None:
        # Calculate annuity factor
        annuity_factor = (self.discount_rate * 
                         (1 + self.discount_rate) ** self.battery.lifetime_years) / \
                        ((1 + self.discount_rate) ** self.battery.lifetime_years - 1)
        
        # Calculate costs
        battery_cost = self.battery.capex_per_mwh * self.battery.capacity * annuity_factor
        renewable_cost = self.renewable.capex_per_mw * self.renewable.capacity * annuity_factor
        
        # Calculate revenue
        price_profile = self._create_price_profile(len(model.variables["export"].coords["time"]))
        revenue = (price_profile * model.variables["export"]).sum()
        
        # Set objective to minimize net cost
        model.add_objective(battery_cost + renewable_cost - revenue)

    def _create_price_profile(self, hours: int) -> np.ndarray:
        """Create price profile based on peak/off-peak hours"""
        hour_of_day = np.tile(np.arange(24), hours // 24)
        price_array = np.full(hours, self.grid.electricity_price_offpeak)
        
        for peak_period in self.grid.peak_hours.values():
            peak_mask = (hour_of_day >= peak_period[0]) & (hour_of_day < peak_period[1])
            price_array[peak_mask] = self.grid.electricity_price_peak
            
        return price_array

class OptimizationEngine:
    """Main optimization engine"""
    def __init__(self, application: BatteryApplication):
        self.application = application

    def optimize(self) -> Dict:
        """Run the optimization"""
        # Create time index
        time = pd.Index(range(len(self.application.renewable.generation_profile)), name="time")
        
        # Initialize model
        model = linopy.Model()
        
        # Add constraints
        self.application.add_component_constraints(model, time)
        self.application.add_application_constraints(model, time)
        
        # Set objective
        self.application.set_objective(model)
        
        # Solve
        model.solve(solver_name='highs')
        
        # Extract results
        results = self._extract_results(model)
        
        return results

    def _extract_results(self, model: linopy.Model) -> Dict:
        """Extract and format optimization results"""
        results = {}
        for var_name, var in model.variables.items():
            results[var_name] = var.solution.values
            
        return results

# Example usage
if __name__ == "__main__":
    # Create components
    battery = BatteryComponent(
        capacity=10.0,
        charge_efficiency=0.95,
        discharge_efficiency=0.95,
        standing_loss=0.005,
        c_rate=0.5,
        capex_per_mwh=15000,
        lifetime_years=10,
        has_dedicated_inverter=True
    )

    # Create dummy generation profile for example
    generation_profile = pd.Series(
        np.random.uniform(0, 10, 8760),  # 8760 hours in a year
        index=pd.date_range('2024-01-01', periods=8760, freq='H')
    )

    renewable = RenewableGeneratorComponent(
        capacity=10.0,
        generation_profile=generation_profile,
        capex_per_mw=1000000,
        lifetime_years=20,
        inverter_capacity=5.0
    )

    grid = GridInterfaceComponent(
        max_export_capacity=10.0,
        electricity_price_peak=3.0,
        electricity_price_offpeak=1.0,
        peak_hours={"morning": [6,9], "evening": [18,22]}
    )

    # Create application
    application = PeakShavingApplication(
        battery=battery,
        renewable=renewable,
        grid=grid,
        discount_rate=0.08
    )

    # Run optimization
    engine = OptimizationEngine(application)
    results = engine.optimize()
    
    print("Optimization Results:")
    for key, value in results.items():
        print(f"{key}: {value}") 