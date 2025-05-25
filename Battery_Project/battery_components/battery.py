from dataclasses import dataclass
from typing import Dict
import linopy
import pandas as pd
import xarray as xr

@dataclass
class BatteryParameters:
    """Battery system technical parameters"""
    capacity: float = None  # MWh, None for optimal sizing
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    standing_loss: float = 0.005
    c_rate: float = 0.5
    capex_per_mwh: float = 150  # $/MWh
    lifetime_years: int = 10
    has_dedicated_inverter: bool = True
    cycles_life: int = 4_000  # Number of cycles before end of life

class BatteryModel:
    """Battery optimization model with constraints"""
    def __init__(self, params: BatteryParameters):
        self.params = params

    def add_battery_variables(self, model: linopy.Model, time: pd.Index) -> Dict[str, xr.DataArray]:
        """Add battery-related variables to the model"""
        variables = {
            'charge': model.add_variables(
                name="battery_charge",
                coords={"time": time},
                dims=["time"],
                lower=0
            ),
            'discharge': model.add_variables(
                name="battery_discharge",
                coords={"time": time},
                dims=["time"],
                lower=0
            ),
            'soc': model.add_variables(
                name="battery_soc",
                coords={"time": time},
                dims=["time"],
                lower=0
            ),
        }
        
        
        # Add capacity variable with bounds
        if self.params.capacity is not None:
            # Fixed capacity case
            variables['capacity'] = model.add_variables(
                name="battery_capacity",
                lower=self.params.capacity,
                upper=self.params.capacity
            )
        else:
            # Variable capacity case - no upper bound
            variables['capacity'] = model.add_variables(
                name="battery_capacity",
                lower=0
            )
            
        return variables

    def add_battery_constraints(
        self, 
        model: linopy.Model, 
        time: pd.Index, 
        variables: Dict[str, xr.DataArray]
    ) -> None:
        """Add battery-specific constraints to the model"""
        # Initial SOC balance
        t0 = time[0]
        t_prev = time[-1]  # Last timestep of previous period
        expr0 = variables['soc'].at[t0] - variables['soc'].at[t_prev] * (1 - self.params.standing_loss) - \
                variables['charge'].at[t0] * self.params.charge_efficiency + \
                variables['discharge'].at[t0] / self.params.discharge_efficiency
        model.add_constraints(expr0 == 0, name="soc_balance_0")

        # SOC balance for remaining timesteps
        t_later = time[1:]
        t_prev = time[:-1]  # Previous timesteps
        soc_expr = variables['soc'].sel(time=t_later)
        soc_prev = variables['soc'].sel(time=t_prev) * (1 - self.params.standing_loss)
        charge_t = variables['charge'].sel(time=t_later)
        discharge_t = variables['discharge'].sel(time=t_later)

        expr_later = soc_expr - soc_prev - charge_t * self.params.charge_efficiency + \
                    discharge_t / self.params.discharge_efficiency
        model.add_constraints(expr_later == 0, name="soc_balance_rest")

        # Get capacity value (fixed or variable)
        capacity = variables.get('capacity', self.params.capacity)

        # C-rate constraints
        model.add_constraints(
            variables['charge'] <= self.params.c_rate * capacity,
            name="charge_c_rate_limit"
        )
        model.add_constraints(
            variables['discharge'] <= self.params.c_rate * capacity,
            name="discharge_c_rate_limit"
        )

        # SOC upper bound
        model.add_constraints(
            variables['soc'] <= capacity,
            name="soc_limit"
        )
        # add a cumulative variable
        cum_dis = model.add_variables(
            name="battery_cum_dis",
            coords={"time": time},
            dims=["time"],
            lower=0
        )
        

        # ── cumulative-discharge initial step ──────────────────────
        model.add_constraints(
            cum_dis.at[time[0]] - variables["discharge"].at[time[0]] == 0,
            name="cum_dis_init",
        )
        
        # ── cumulative-discharge evolution for t > 0 ──────────────
        model.add_constraints(
            cum_dis.sel(time=time[1:])
            - cum_dis.shift(time=1).sel(time=time[1:])      # previous timestep
            - variables["discharge"].sel(time=time[1:])     # add current discharge
            == 0,
            name="cum_dis_evolution",
        )

        # Calculate annual cycles limit by dividing total cycles by lifetime years
        annual_cycles_limit = self.params.cycles_life / self.params.lifetime_years
        model.add_constraints(
            cum_dis <= annual_cycles_limit * variables["capacity"],
            name="lifetime_throughput_cap",
        )



    def calculate_battery_costs(self, variables: Dict[str, xr.DataArray], discount_rate: float) -> float:
        """Calculate battery costs including CAPEX and annuity factor"""
        annuity_factor = 1
        
        # Get capacity value (fixed or variable)
        capacity = variables.get('capacity', self.params.capacity)
        
        return self.params.capex_per_mwh * capacity * annuity_factor 

    def calculate_degradation_cost(self, discharge_sum: xr.DataArray) -> float:
        """Calculate battery degradation cost based on total discharge"""
        deg_cost_per_mwh = self.params.capex_per_mwh / self.params.cycles_life  # $/MWh
        return deg_cost_per_mwh * discharge_sum 