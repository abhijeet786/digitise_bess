from dataclasses import dataclass
from typing import Dict
import linopy
import pandas as pd
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
from .renewables_ninja import RenewablesNinjaAPI

@dataclass
class SolarParameters:
    """Solar installation parameters"""
    latitude: float
    longitude: float
    capacity: float  # MW
    tilt: float = 25.0
    azimuth: float = 180.0
    system_loss: float = 0.1
    tracking: int = 0  # 0 for fixed, 1 for single-axis, 2 for dual-axis
    inverter_capacity: float = None  # MW, defaults to capacity if None
    battery_has_dedicated_inverter: bool = True  # whether battery has its own inverter
    api_token: str = None  # Renewables.ninja API token
    start_date: str = None  # format: 'YYYY-MM-DD'
    end_date: str = None  # format: 'YYYY-MM-DD'
    capex_per_mw: float = 1000000  # $/MW
    lifetime_years: int = 25  # years

    def __post_init__(self):
        """Set default values after initialization"""
        if self.inverter_capacity is None:
            self.inverter_capacity = self.capacity

class SolarModel:
    """Solar optimization model with constraints"""
    def __init__(self, params: SolarParameters):
        self.params = params
        self.ninja_api = None
        if params.api_token:
            self.ninja_api = RenewablesNinjaAPI(params.api_token)
        
        # Set default dates if not provided
        today = datetime.now()
        self.start_date = params.start_date or (today - timedelta(days=365)).strftime('%Y-%m-%d')
        self.end_date = params.end_date or today.strftime('%Y-%m-%d')
        
        # Initialize generation profile
        self.generation_profile = self._get_generation_profile()

    def _get_generation_profile(self) -> pd.Series:
        """Get solar generation profile from Renewables.ninja API or use default profile"""
        if self.ninja_api:
            try:
                return self.ninja_api.fetch_pv_data(
                    lat=self.params.latitude,
                    lon=self.params.longitude,
                    date_from=self.start_date,
                    date_to=self.end_date,
                    capacity=self.params.capacity,
                    system_loss=self.params.system_loss,
                    tracking=self.params.tracking,
                    tilt=self.params.tilt,
                    azim=self.params.azimuth
                )
            except Exception as e:
                print(f"Warning: Failed to fetch solar data from Renewables.ninja: {str(e)}")
                print("Using default generation profile instead")
        
        # Default profile if API fails or not configured
        hours_per_year = 8760
        time_index = pd.date_range(self.start_date, periods=hours_per_year, freq='h')
        return pd.Series(
            np.random.uniform(0, 1, hours_per_year),
            index=time_index
        )

    def add_solar_variables(self, model: linopy.Model, time: pd.Index) -> Dict[str, xr.DataArray]:
        """Add solar-related variables to the model"""
        variables = {
            'generation': model.add_variables(
                name="solar_generation",
                coords={"time": time},
                dims=["time"],
                lower=0,
                upper=self.params.capacity
            )
        }
        return variables

    def add_solar_constraints(
        self,
        model: linopy.Model,
        time: pd.Index,
        variables: Dict[str, xr.DataArray],
        shared_inverter: bool,
        battery_capacity: float
    ) -> None:
        """Add solar-specific constraints to the model"""
        # Generation profile constraint
        model.add_constraints(
            variables['generation'] <= self.generation_profile,
            name='solar_generation_profile'
        )


        # model.add_constraints(
        #         variables['generation'] <= self.params.inverter_capacity,
        #         name='solar_inverter_capacity'
        #     )

    def calculate_solar_costs(self, discount_rate: float) -> float:
        """Calculate solar costs including CAPEX and annuity factor"""
        annuity_factor = (discount_rate * 
                         (1 + discount_rate) ** self.params.lifetime_years) / \
                        ((1 + discount_rate) ** self.params.lifetime_years - 1)
        
        return self.params.capex_per_mw * self.params.capacity * annuity_factor 