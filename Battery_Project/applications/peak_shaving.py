from typing import Dict, Any
import pandas as pd
import numpy as np
from battery_components.battery import BatteryParameters, BatteryModel
from battery_components.solar import SolarParameters, SolarModel
from battery_components.grid import GridParameters, GridModel
from battery_components.optimization_engine import OptimizationEngine

class PeakShavingApplication:
    """Peak shaving application using battery storage"""
    def __init__(
        self,
        battery_capacity: float = None,  # MWh, None for optimal sizing
        solar_capacity: float = 10.0,  # MW
        max_export: float = 10.0,  # MW
        discount_rate: float = 0.08,
        peak_price: float = 100.0,  # $/MWh (higher price during non-solar hours)
        offpeak_price: float = 20.0,  # $/MWh (lower price during solar hours)
        generation_profile: pd.Series = None,
        latitude: float = 28.6139,  # Default to New Delhi coordinates
        longitude: float = 77.2090,
        api_token: str = None,  # Renewables.ninja API token
        start_date: str = None,  # format: 'YYYY-MM-DD'
        end_date: str = None    # format: 'YYYY-MM-DD'
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
            capex_per_mw=1000000,
            lifetime_years=20,
            inverter_capacity=5.0,
            start_date=start_date,
            end_date=end_date
        )

        # Create solar model to get generation profile
        self.solar_model = SolarModel(self.solar_params)
        generation_profile = self.solar_model.generation_profile

        # Create price profile based on solar generation
        # Higher price when solar generation is low, lower price when solar generation is high
        price_profile = pd.Series(
            np.where(generation_profile > generation_profile.mean(),
                    offpeak_price,  # Lower price during solar hours
                    peak_price),    # Higher price during non-solar hours
            index=generation_profile.index
        )

        # Create grid parameters
        self.grid_params = GridParameters(
            max_import=0,  # Using max_export as max_import for simplicity
            max_export=max_export,
            price_profile=price_profile,
            connection_cost=50000  # $/MW
        )

        # Create optimization engine
        self.engine = OptimizationEngine(
            battery_params=self.battery_params,
            solar_params=self.solar_params,
            grid_params=self.grid_params,
            discount_rate=discount_rate
        )

    def run_optimization(self) -> Dict[str, Any]:
        """Run the optimization and return results"""
        return self.engine.optimize()

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