from typing import Dict, Any
import linopy
import pandas as pd
import xarray as xr
from .battery import BatteryParameters, BatteryModel
from .grid import GridParameters, GridModel
from .solar import SolarParameters, SolarModel

class OptimizationEngine:
    """Main optimization engine that coordinates all components"""
    def __init__(
        self,
        battery_params: BatteryParameters,
        solar_params: SolarParameters,
        grid_params: GridParameters,
        discount_rate: float = 0.08
    ):
        self.battery_model = BatteryModel(battery_params)
        self.solar_model = SolarModel(solar_params)
        self.grid_model = GridModel(grid_params)
        self.discount_rate = discount_rate

    def optimize(self) -> Dict[str, Any]:
        """Run the optimization and return results"""
        # Create time index using the same timezone as the price profile
        time = pd.date_range(
            start=self.grid_model.params.price_profile.index[0],
            end=self.grid_model.params.price_profile.index[-1],
            freq='h'
        )
        
        # Ensure all time series data is aligned
        self.solar_model.generation_profile = self.solar_model.generation_profile.reindex(time, fill_value=0)
        self.grid_model.params.price_profile = self.grid_model.params.price_profile.reindex(time, fill_value=0)

        # Initialize optimization model
        model = linopy.Model()

        # Add variables from each component
        battery_vars = self.battery_model.add_battery_variables(model, time)
        solar_vars = self.solar_model.add_solar_variables(model, time)
        grid_vars = self.grid_model.add_grid_variables(model, time)

        # Add constraints from each component
        self.battery_model.add_battery_constraints(model, time, battery_vars)
        self.solar_model.add_solar_constraints(
            model, time, solar_vars,
            self.battery_model.params.has_dedicated_inverter,
            battery_vars['capacity'] if 'capacity' in battery_vars else self.battery_model.params.capacity
        )
        self.grid_model.add_grid_constraints(
            model, time, grid_vars,
            solar_vars['generation'],
            battery_vars['charge'],
            battery_vars['discharge']
        )

        # Set objective
        self._set_objective(model, battery_vars, solar_vars, grid_vars)

        # Solve the model
        model.solve()
        
        # Check if solution exists
        # if not model.solution.is_feasible:
        #     raise RuntimeError("Optimization failed to find a feasible solution")
            
        # Extract and return results
        return self._extract_results(model, battery_vars, solar_vars, grid_vars)

    def _set_objective(
        self,
        model: linopy.Model,
        battery_vars: Dict[str, xr.DataArray],
        solar_vars: Dict[str, xr.DataArray],
        grid_vars: Dict[str, xr.DataArray]
    ) -> None:
        """Set the optimization objective"""
        # Calculate annuity factor
        annuity_factor = (self.discount_rate * 
                         (1 + self.discount_rate) ** self.battery_model.params.lifetime_years) / \
                        ((1 + self.discount_rate) ** self.battery_model.params.lifetime_years - 1)
        
        # Get battery capacity (fixed or variable)
        battery_capacity = battery_vars['capacity'] #if 'capacity' in battery_vars else self.battery_model.params.capacity
        
        # Calculate costs
        battery_cost = self.battery_model.params.capex_per_mwh * battery_capacity * annuity_factor
        
        # Calculate revenue/cost from grid interactions
        # Positive export means selling to grid, negative means buying from grid
        grid_interaction = (grid_vars['export'] * self.grid_model.params.price_profile).sum()
        
        # Set objective to minimize net cost
        model.add_objective(battery_cost - grid_interaction)

    def _extract_results(
        self,
        model: linopy.Model,
        battery_vars: Dict[str, xr.DataArray],
        solar_vars: Dict[str, xr.DataArray],
        grid_vars: Dict[str, xr.DataArray]
    ) -> Dict:
        """Extract results from the optimization model"""
        # Debug prints
        print("\nOptimization Results:")
        print(f"Battery Capacity: {float(battery_vars['capacity'].solution):.2f} MWh")

        
        # Calculate some summary statistics
        grid_export = grid_vars['export'].solution.values
        solar_gen = solar_vars['generation'].solution.values
        battery_charge = battery_vars['charge'].solution.values
        battery_discharge = battery_vars['discharge'].solution.values
        
        print("\nAnnual Summary:")
        print(f"Total Solar Generation: {solar_gen.sum():.2f} MWh")
        print(f"Total Battery Charge: {battery_charge.sum():.2f} MWh")
        print(f"Total Battery Discharge: {battery_discharge.sum():.2f} MWh")
        print(f"Net Grid Export: {grid_export.sum():.2f} MWh")
        
        return {
            'battery': {
                'capacity': float(battery_vars['capacity'].solution),

                'soc': battery_vars['soc'].solution.values,
                'charge': battery_vars['charge'].solution.values,
                'discharge': battery_vars['discharge'].solution.values
            },
            'solar': {
                'generation': solar_vars['generation'].solution.values
            },
            'grid': {
                'export': grid_vars['export'].solution.values
            }
        } 