from typing import Dict, Any
import pandas as pd
import numpy as np
import linopy
import xarray as xr
from battery_components.battery import BatteryParameters, BatteryModel
from battery_components.solar import SolarParameters, SolarModel
from battery_components.grid import GridParameters, GridModel
from financial.financial_analysis_updated import analyze_battery_project

class EnergyArbitrageApplication:
    """Energy arbitrage application using battery storage"""
    def __init__(
        self,
        # Battery parameters
        battery_capacity: float = None,  # MWh, None for optimal sizing
        charge_efficiency: float = 0.95,
        discharge_efficiency: float = 0.95,
        standing_loss: float = 0.005,
        c_rate: float = 0.5,
        battery_capex_per_mwh: float = 15000,
        battery_lifetime_years: int = 10,
        has_dedicated_inverter: bool = True,
        
        # Solar parameters
        solar_capacity: float = 10.0,  # MW
        solar_capex_per_mw: float = 1000000,
        solar_lifetime_years: int = 20,
        solar_inverter_capacity: float = 5.0,
        data_source: str = 'renewables_ninja',
        
        # Grid parameters
        max_export: float = 10.0,  # MW
        max_import: float = 0,  # MW (added)
        grid_connection_cost: float = 50000,  # $/MW
        
        # Economic parameters
        discount_rate: float = 0.08,
        peak_price: float = 100.0,  # $/MWh (higher price during non-solar hours)
        offpeak_price: float = 20.0,  # $/MWh (lower price during solar hours)
        
        # Location parameters
        latitude: float = 28.6139,  # Default to New Delhi coordinates
        longitude: float = 77.2090,
        
        # API parameters
        api_token: str = None,  # Renewables.ninja API token
        start_date: str = None,  # format: 'YYYY-MM-DD'
        end_date: str = None,    # format: 'YYYY-MM-DD'
        
        # Price data parameters
        use_csv_prices: bool = False,  # Whether to use prices from CSV
        csv_path: str = 'data/combined_iex_cleaned.csv'  # Path to the CSV file
    ):
        # Create battery parameters
        self.battery_params = BatteryParameters(
            capacity=battery_capacity,
            charge_efficiency=charge_efficiency,
            discharge_efficiency=discharge_efficiency,
            standing_loss=standing_loss,
            c_rate=c_rate,
            capex_per_mwh=battery_capex_per_mwh,
            lifetime_years=battery_lifetime_years,
            has_dedicated_inverter=has_dedicated_inverter
        )

        # Create solar parameters
        self.solar_params = SolarParameters(
            latitude=latitude,
            longitude=longitude,
            capacity=solar_capacity,
            api_token=api_token,
            capex_per_mw=solar_capex_per_mw,
            lifetime_years=solar_lifetime_years,
            inverter_capacity=solar_inverter_capacity,
            start_date=start_date,
            end_date=end_date,
            data_source=data_source
        )

        # Create solar model to get generation profile
        self.solar_model = SolarModel(self.solar_params)
        generation_profile = self.solar_model.generation_profile

        # Create price profile
        if use_csv_prices:
            # Read and process price data from CSV
            price_profile = self._get_price_profile_from_csv(csv_path, start_date, end_date)
        else:
            # Set off-peak for 10am-5pm, peak otherwise
            hours = generation_profile.index.hour
            price_profile = pd.Series(
                np.where((hours >= 10) & (hours <= 17),
                         offpeak_price,  # Off-peak 10am-5pm
                         peak_price),    # Peak other hours
                index=generation_profile.index
            )

        # Create grid parameters
        self.grid_params = GridParameters(
            max_import=max_import,  # Pass max_import here
            max_export=max_export,
            price_profile=price_profile,
            connection_cost=grid_connection_cost
        )

        # Create component models
        self.battery_model = BatteryModel(self.battery_params)
        self.grid_model = GridModel(self.grid_params)
        self.discount_rate = discount_rate

    def _get_price_profile_from_csv(self, csv_path: str, start_date: str, end_date: str) -> pd.Series:
        """Read and process price data from CSV file"""
        df = pd.read_csv(csv_path)
        # Combine Date and Time Block to create a timestamp
        # Extract start time from Time Block (e.g., '00:00 - 00:15' -> '00:00')
        df['start_time'] = df['Time Block'].str.split(' - ').str[0]
        df['timestamp'] = pd.to_datetime(df['Date'] + ' ' + df['start_time'], format='%d-%m-%Y %H:%M')
        # Filter data for the specified date range
        mask = (df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)
        df = df[mask]
        df.set_index('timestamp', inplace=True)
        # Use MCP (Rs/MWh) column and resample to hourly resolution
        price_series = df['MCP (Rs/MWh) *'].resample('H').mean()
        price_series = price_series.fillna(method='ffill')
        return price_series

    def run_optimization(self) -> Dict[str, Any]:
        """Run the optimization and return results"""
        # Create time index using the same timezone as the price profile
        time = pd.date_range(
            start=self.grid_params.price_profile.index[0],
            end=self.grid_params.price_profile.index[-1],
            freq='h'
        )
        
        # Ensure all time series data is aligned
        self.solar_model.generation_profile = self.solar_model.generation_profile.reindex(time, fill_value=0)
        self.grid_params.price_profile = self.grid_params.price_profile.reindex(time, fill_value=0)

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
        annuity_factor = 1
        
        # Calculate revenue/cost from grid interactions
        grid_interaction = (grid_vars['export'] * self.grid_params.price_profile).sum()
        discharge_sum = battery_vars["discharge"].sum()  # xr.DataArray expression
        degradation_term = self.battery_model.calculate_degradation_cost(discharge_sum)
        
        # Set objective to minimize net cost
        # Only include battery cost term if capacity is a variable
        if self.battery_params.capacity is None:
            battery_cost_term = self.battery_params.capex_per_mwh * annuity_factor * battery_vars['capacity']
            model.add_objective(battery_cost_term - grid_interaction + degradation_term)
        else:
            model.add_objective(-grid_interaction + degradation_term)  # Only maximize grid revenue for fixed battery capacity

    def _extract_results(
        self,
        model: linopy.Model,
        battery_vars: Dict[str, xr.DataArray],
        solar_vars: Dict[str, xr.DataArray],
        grid_vars: Dict[str, xr.DataArray]
    ) -> Dict[str, Any]:
        """Extract results from the optimization model"""
        # Get battery capacity (either fixed or optimized)
        battery_capacity = float(battery_vars['capacity'].solution) if 'capacity' in battery_vars else self.battery_params.capacity
        
        # Calculate costs and revenue
        annuity_factor = 1#(self.discount_rate * 
                         #(1 + self.discount_rate) ** self.battery_params.lifetime_years) / \
                        #((1 + self.discount_rate) ** self.battery_params.lifetime_years - 1)
        
        # Calculate costs
        battery_cost = self.battery_params.capex_per_mwh * battery_capacity * annuity_factor
        solar_cost = self.solar_params.capex_per_mw * self.solar_params.capacity * annuity_factor
        
        # Calculate grid revenue using solution values
        grid_export = grid_vars['export'].solution.values
        grid_revenue = float(np.sum(grid_export * self.grid_params.price_profile.values))
        
        return {
            'battery': {
                'capacity': battery_capacity,
                'cost': battery_cost,
                'soc': battery_vars['soc'].solution.values,
                'charge': battery_vars['charge'].solution.values,
                'discharge': battery_vars['discharge'].solution.values
            },
            'solar': {
                'capacity': self.solar_params.capacity,
                'cost': solar_cost,
                'generation': solar_vars['generation'].solution.values
            },
            'grid': {
                'max_export': self.grid_params.max_export,
                'max_import': self.grid_params.max_import,
                'connection_cost': self.grid_params.connection_cost,
                'export': grid_export,
                'revenue': grid_revenue,
                'price_profile': self.grid_params.price_profile  # Save price profile here
            },
            'total_cost': battery_cost + solar_cost,
            'revenue': grid_revenue,
            'net_cost': battery_cost + solar_cost - grid_revenue
        }

    def get_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the optimization results"""
        return {
            'battery': {
                'capacity': results['battery']['capacity'],
                'cost': results['battery']['cost']
            },
            'solar': {
                'capacity': results['solar']['capacity'],
                'cost': results['solar']['cost']
            },
            'grid': {
                'max_export': results['grid']['max_export'],
                'connection_cost': results['grid']['connection_cost']
            },
            'total_cost': results['total_cost'],
            'revenue': results['revenue'],
            'net_cost': results['net_cost']
        }

    def run_financial_analysis(self, results, capex_multiplier=8):
        """
        Run financial analysis using the simulation results and app parameters.
        """
        total_capex = results['battery']['capacity'] * self.battery_params.capex_per_mwh * capex_multiplier
        financial_df, project_irr, equity_irr = analyze_battery_project(
            simulation_results=results,
            capex=total_capex,
            years=self.battery_params.lifetime_years,
            residual_value_pct=0.1,
            tax_rate=0.25,
            depreciation_type='straight line',
            dep_rate=0.4,
            debt_ratio=0.7,
            equity_ratio=0.3,
            interest_rate=0.10,
            repayment_type="emi",
            dscr_target=1.3
        )
        return financial_df, project_irr, equity_irr 