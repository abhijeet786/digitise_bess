from dataclasses import dataclass
from typing import Dict
import linopy
import pandas as pd
import xarray as xr

@dataclass
class GridParameters:
    """Grid connection parameters"""
    max_import: 0  # MW
    max_export: float  # MW
    price_profile: pd.Series  # Time series of prices in $/MWh
    connection_cost: float  # $/MW
    lifetime_years: int = 20

class GridModel:
    """Grid optimization model with constraints"""
    def __init__(self, params: GridParameters):
        self.params = params

    def add_grid_variables(self, model: linopy.Model, time: pd.Index) -> Dict[str, xr.DataArray]:
        """Add grid-related variables to the model"""
        variables = {
            'export': model.add_variables(
                name="grid_export",
                coords={"time": time},
                dims=["time"],
                lower=-self.params.max_import,  # Allow negative values for imports
                upper=self.params.max_export
            )
        }
        return variables

    def add_grid_constraints(
        self,
        model: linopy.Model,
        time: pd.Index,
        variables: Dict[str, xr.DataArray],
        solar_generation: xr.DataArray,
        battery_charge: xr.DataArray,
        battery_discharge: xr.DataArray
    ) -> None:
        """Add grid-specific constraints to the model"""
        # Power balance constraint
        model.add_constraints(
            variables['export'] == solar_generation + battery_discharge - battery_charge,
            name='power_balance'
        )

    def calculate_grid_costs(self, discount_rate: float) -> float:
        """Calculate grid costs including connection cost and annuity factor"""
        annuity_factor = (discount_rate * 
                         (1 + discount_rate) ** self.params.lifetime_years) / \
                        ((1 + discount_rate) ** self.params.lifetime_years - 1)
        
        return self.params.connection_cost * max(self.params.max_import, self.params.max_export) * annuity_factor 