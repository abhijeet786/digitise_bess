# -*- coding: utf-8 -*-
"""
Created on Wed May 21 12:15:00 2025

@author: neshw
"""

from dataclasses import dataclass
from typing import Dict
import linopy
import pandas as pd
import xarray as xr


# ────────────────────────────
# 1. Input parameters
# ────────────────────────────
@dataclass
class BatteryParameters:
    """Battery system technical parameters"""
    capacity: float = None          # MWh; if None, model will size it optimally
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    standing_loss: float = 0.005    # fractional loss per period
    c_rate: float = 0.5             # 0.5 ⇢ power = 0.5 × energy
    capex_per_mwh: float = 150      # $/MWh
    lifetime_years: int = 10
    has_dedicated_inverter: bool = True



# ────────────────────────────
# 2. Battery model
# ────────────────────────────
class BatteryModel:
    """Battery optimization model with degradation-driven usable-capacity limits"""
    def __init__(self, params: BatteryParameters):
        self.params = params


    # ── 2.1 Variables ────────────────────────────────────────────
    def add_battery_variables(
        self,
        model: linopy.Model,
        time: pd.Index
    ) -> Dict[str, xr.DataArray]:
        """Add battery‐related variables to the model"""

        variables = {
            "charge": model.add_variables(
                name="battery_charge", coords={"time": time}, dims=["time"], lower=0
            ),
            "discharge": model.add_variables(
                name="battery_discharge", coords={"time": time}, dims=["time"], lower=0
            ),
            "soc": model.add_variables(
                name="battery_soc", coords={"time": time}, dims=["time"], lower=0
            ),
            # NEW: State-of-Health, bounded [0, 1]
            "soh": model.add_variables(
                name="battery_soh", coords={"time": time}, dims=["time"], lower=0, upper=1
            ),
        }

        # Fixed-vs-optimised capacity
        if self.params.capacity is not None:
            variables["capacity"] = model.add_variables(
                name="battery_capacity",
                lower=self.params.capacity,
                upper=self.params.capacity,
            )
        else:
            variables["capacity"] = model.add_variables(
                name="battery_capacity", lower=0
            )

        return variables


    # ── 2.2 Constraints ──────────────────────────────────────────
    def add_battery_constraints(
        self,
        model: linopy.Model,
        time: pd.Index,
        variables: Dict[str, xr.DataArray],
    ) -> None:
        """Add all battery constraints (energy balance, C-rate, degradation)"""

        charge, discharge, soc, soh, capacity = (
            variables["charge"],
            variables["discharge"],
            variables["soc"],
            variables["soh"],
            variables["capacity"],
        )

        η_c, η_d, σ = (
            self.params.charge_efficiency,
            self.params.discharge_efficiency,
            self.params.standing_loss,
        )

        # ── Energy-balance on SOC ───────────────────────────
        t0, t_rest = time[0], time[1:]

        # first step (wrap-around / cyclic balance)
        model.add_constraints(
            soc.at[t0]
            - soc.at[time[-1]] * (1 - σ)
            - charge.at[t0] * η_c
            + discharge.at[t0] / η_d
            == 0,
            name="soc_balance_0",
        )

        # remaining steps
        model.add_constraints(
            soc.sel(time=t_rest)
            - soc.shift(1).sel(time=t_rest) * (1 - σ)
            - charge.sel(time=t_rest) * η_c
            + discharge.sel(time=t_rest) / η_d
            == 0,
            name="soc_balance_rest",
        )

        # ── C-rate limits ──────────────────────────────────
        model.add_constraints(
            charge <= self.params.c_rate * capacity, name="charge_c_rate_limit"
        )
        model.add_constraints(
            discharge <= self.params.c_rate * capacity, name="discharge_c_rate_limit"
        )

        # ── Degradation: SoH dynamics ──────────────────────
        #
        # We approximate linear degradation with cumulative throughput:
        #
        #   soh_{t+1} = soh_t − α · discharge_t
        #
        # where α = 1 / E_life,  E_life = (capacity × cycles_life).
        #
        cycles_life = 8_000                    #   ← adjust if you have better data
        alpha = 1 / (cycles_life * capacity)   # dynamic because capacity may be a variable

        # Initial SoH = 1
        model.add_constraints(soh.at[t0] == 1, name="soh_init")

        # Evolution for t > 0
        model.add_constraints(
            soh.sel(time=t_rest) - soh.shift(1).sel(time=t_rest) + alpha * discharge.sel(time=t_rest) == 0,
            name="soh_evolution",
        )

        # ── Usable-capacity limit ──────────────────────────
        model.add_constraints(
            soc <= soh * capacity, name="soc_soh_limit"
        )


    # ── 2.3 CAPEX annuity helper ───────────────────────────────
    def calculate_battery_costs(
        self,
        variables: Dict[str, xr.DataArray],
        discount_rate: float,
    ) -> float:
        """Annuity‐adjusted annualised CAPEX (for objective function)"""

        annuity_factor = (
            discount_rate * (1 + discount_rate) ** self.params.lifetime_years
        ) / ((1 + discount_rate) ** self.params.lifetime_years - 1)

        capacity = variables.get("capacity", self.params.capacity)
        return self.params.capex_per_mwh * capacity * annuity_factor
