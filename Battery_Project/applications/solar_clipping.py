from typing import Dict, Any
import pandas as pd
import numpy as np
import linopy
import xarray as xr
from battery_components.battery import BatteryParameters, BatteryModel
from battery_components.solar import SolarParameters, SolarModel
from battery_components.grid import GridParameters, GridModel

class SolarClippingApplication:
    """Peak shaving application using battery storage"""
    def __init__(
        self,
        battery_capacity: float = None,  # MWh, None for optimal sizing
        solar_capacity: float = 10.0,  # MW
        inverter_capacity: float = 10.0,
        max_export: float = 10.0,  # MW
        discount_rate: float = 0.08,
        peak_price: float = 100.0,  # $/MWh (higher price during non-solar hours)
        offpeak_price: float = 20.0,  # $/MWh (lower price during solar hours)
        generation_profile: pd.Series = None,
        latitude: float = 28.6139,  # Default to New Delhi coordinates
        longitude: float = 77.2090,
        api_token: str = None,  # Renewables.ninja API token
        start_date: str = None,  # format: 'YYYY-MM-DD'
        end_date: str = None,    # format: 'YYYY-MM-DD'
        clip_threshold: float = 0.0  # Added for clipping functionality
    ):
        # Create battery parameters
        self.battery_params = BatteryParameters(
            capacity=battery_capacity,
            charge_efficiency=0.95,
            discharge_efficiency=0.95,
            standing_loss=0.005,
            c_rate=0.5,
            capex_per_mwh=15000,
            lifetime_years=10,
            has_dedicated_inverter=True
        )

        # Create solar parameters
        self.solar_params = SolarParameters(
            latitude=latitude,
            longitude=longitude,
            capacity=solar_capacity,
            api_token=api_token,
            battery_has_dedicated_inverter=True,
            capex_per_mw=1000000,
            lifetime_years=20,
            inverter_capacity=inverter_capacity,
            start_date=start_date,
            end_date=end_date
        )

        # Create grid parameters
        self.grid_params = GridParameters(
            max_import=0,  # Using max_export as max_import for simplicity
            max_export=max_export,
            price_profile=None,  # Will be set after solar model is created
            connection_cost=50000  # $/MW
        )

        # Create component models
        self.battery_model = BatteryModel(self.battery_params)
        self.solar_model = SolarModel(self.solar_params)
        self.grid_model = GridModel(self.grid_params)

        # Get generation profile from solar model
        generation_profile = self.solar_model.generation_profile

        # Create price profile based on solar generation
        # Higher price when solar generation is low, lower price when solar generation is high
        price_profile = pd.Series(
            np.where(generation_profile > generation_profile.mean(),
                    offpeak_price,  # Lower price during solar hours
                    peak_price),    # Higher price during non-solar hours
            index=generation_profile.index
        )

        # Update grid parameters with price profile
        self.grid_params.price_profile = price_profile
        self.grid_model.params.price_profile = price_profile

        self.discount_rate = discount_rate
        self.clip_threshold = clip_threshold

    def _apply_clipping(self, profile: pd.Series, capacity: float, threshold: float) -> pd.Series:
        """Apply clipping to the generation profile"""
        return profile.clip(upper=threshold * capacity)

    def _calculate_clipped_energy(self, profile: pd.Series, capacity: float, threshold: float) -> float:
        """Calculate the amount of energy that would be clipped"""
        clipped_profile = self._apply_clipping(profile, capacity, threshold)
        return (profile - clipped_profile).sum()

    def run_optimization(self) -> Dict[str, Any]:
        """Run the optimization and return results"""
        # Modify solar generation profile to include clipping
        self.solar_model.generation_profile = self._apply_clipping(
            self.solar_model.generation_profile,
            self.solar_params.capacity,
            self.clip_threshold
        )
        
        # Create time index using the same timezone as the price profile
        time = pd.date_range(
            start=self.grid_params.price_profile.index[0],
            end=self.grid_params.price_profile.index[-1],
            freq='h'
        )
        
        # Ensure all time series data is aligned
        self.solar_model.generation_profile = self.solar_model.generation_profile.reindex(time, fill_value=0)
        self.grid_params.price_profile = self.grid_params.price_profile.reindex(time, fill_value=0)
        self.grid_model.params.price_profile = self.grid_params.price_profile

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

        # Add inverter capacity constraint
        model.add_constraints(
            solar_vars['generation'] + battery_vars['discharge'] - battery_vars['charge'] <= self.solar_params.inverter_capacity,
            name='inverter_capacity'
        )

        # Set objective
        self._set_objective(model, battery_vars, solar_vars, grid_vars)

        # Solve the model
        model.solve()
        
        # Extract and return results
        results = self._extract_results(model, battery_vars, solar_vars, grid_vars)
        
        # Add clipping-specific metrics
        results['clipping'] = {
            'threshold': self.clip_threshold,
            'clipped_energy': self._calculate_clipped_energy(
                self.solar_model.generation_profile,
                self.solar_params.capacity,
                self.clip_threshold
            )
        }
        
        return results

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
                         (1 + self.discount_rate) ** self.battery_params.lifetime_years) / \
                        ((1 + self.discount_rate) ** self.battery_params.lifetime_years - 1)
        
        # Get battery capacity (fixed or variable)
        battery_capacity = battery_vars['capacity'] if 'capacity' in battery_vars else self.battery_params.capacity
        
        # Calculate costs
        battery_cost = self.battery_params.capex_per_mwh * battery_capacity * annuity_factor
        solar_cost = self.solar_params.capex_per_mw * self.solar_params.capacity * annuity_factor
        
        # Calculate revenue/cost from grid interactions
        grid_interaction = (grid_vars['export'] * self.grid_params.price_profile).sum()
        
        # Set objective to minimize net cost
        model.add_objective(battery_cost + grid_interaction)

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

    def get_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the optimization results"""
        # Get battery capacity (either fixed or optimized)
        battery_capacity = self.battery_params.capacity if self.battery_params.capacity is not None else results.get('battery_capacity')
        
        return {
            'battery': {
                'capacity': battery_capacity,
                'cost': results.get('battery_cost', 0.0)
            },
            'solar': {
                'capacity': self.solar_params.capacity,
                'cost': results.get('solar_cost', 0.0)
            },
            'grid': {
                'max_export': self.grid_params.max_export,
                'connection_cost': self.grid_params.connection_cost
            },
            'total_cost': results.get('total_cost', 0.0),
            'revenue': results.get('revenue', 0.0),
            'net_cost': results.get('net_cost', 0.0)
        } 