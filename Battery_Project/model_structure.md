# 🔋 Battery Optimization Model Structure

```
  ███████╗███████╗ █████╗ ██╗     ██╗██╗██╗  ██╗
  ╚══███╔╝██╔════╝██╔══██╗██║     ██║██║╚██╗██╔╝
    ███╔╝ ███████╗███████║██║     ██║██║ ╚███╔╝ 
   ███╔╝  ██║     ██╔══██║██║     ██║██║ ██╔██╗ 
  ███████╗███████║██║  ██║███████╗██║██║██╔╝ ██╗
  ╚══════╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝╚═╝╚═╝  ╚═╝
```

## 📚 Table of Contents
1. [Overview](#overview)
2. [How to Run](#how-to-run)
3. [Model Structure](#model-structure)
4. [Components](#components)
5. [Applications](#applications)
6. [Example Usage](#example-usage)
7. [Component Details](#component-details)
8. [Application Details](#application-details)
9. [References](#references)

---

## 📝 Overview

This project is a modular battery optimization model for power grid applications. The model is divided into **components** (building blocks like Battery, Solar, Grid) and **applications** (use-cases like Peak Shaving, Solar Clipping, Grid Export Target). Each application combines components to solve a specific grid or energy management problem.
---
![Basic build: Optimization model to schedule battery's operation in power grid systems](https://miro.medium.com/v2/resize:fit:640/format:webp/1*EjtFvWbWYmVn0kqSas--tw.png)
![Basic build: Optimization model to schedule battery's operation in power grid systems](https://cdn.prod.website-files.com/64e46c9ca980cf228bbbbf55/6740bb6e47db03a3314935cb_6740ba95e27950f8397b8ea1_saved-searches-small.gif)


1. **Install dependencies** (see `requirements.txt`).
2. **Configure your scenario** in `main.py` by selecting the application and setting parameters.
3. **Run the main script:**
   ```bash
   python main.py
   ```
4. **View results** in the console or output files (e.g., Excel, CSV).

---

## 🏗️ Model Structure

```
Applications
├── PeakShavingApplication
├── SolarClippingApplication
└── GridExportTargetApplication
    │
    ├── BatteryComponent
    │   ├── BatteryParameters
    │   │   ├── capacity (MWh)
    │   │   ├── charge_efficiency
    │   │   ├── discharge_efficiency
    │   │   ├── standing_loss
    │   │   ├── c_rate
    │   │   ├── capex_per_mwh
    │   │   ├── lifetime_years
    │   │   └── has_dedicated_inverter
    │   └── BatteryModel
    │       ├── add_battery_variables()
    │       └── add_battery_constraints()
    │
    ├── SolarComponent
    │   ├── SolarParameters
    │   │   ├── capacity (MW)
    │   │   ├── latitude
    │   │   ├── longitude
    │   │   ├── capex_per_mw
    │   │   ├── lifetime_years
    │   │   ├── inverter_capacity
    │   │   ├── data_source ('renewables_ninja' or 'csv')
    │   │   ├── api_token
    │   │   ├── start_date
    │   │   └── end_date
    │   └── SolarModel
    │       ├── generation_profile
    │       ├── add_solar_variables()
    │       └── add_solar_constraints()
    │
    └── GridComponent
        ├── GridParameters
        │   ├── max_import (MW)
        │   ├── max_export (MW)
        │   ├── price_profile
        │   ├── connection_cost
        │   └── export_target (MW)
        └── GridModel
            ├── add_grid_variables()
            └── add_grid_constraints()
```

---

## 🧩 Components

### 1. **BatteryComponent**
- **Purpose:** Models battery storage, state of charge, charge/discharge, and efficiency.
- **Key Parameters:**  
  - `capacity` (MWh): Battery storage size  
  - `charge_efficiency`, `discharge_efficiency`: Round-trip efficiency  
  - `standing_loss`: Self-discharge rate  
  - `c_rate`: Max charge/discharge rate  
  - `capex_per_mwh`: Capital cost per MWh  
  - `lifetime_years`: Battery lifetime  
  - `has_dedicated_inverter`: Boolean

### 2. **SolarComponent**
- **Purpose:** Models solar PV generation, inverter limits, and data sources.
- **Key Parameters:**  
  - `capacity` (MW): Solar PV size  
  - `latitude`, `longitude`: Location  
  - `capex_per_mw`: Capital cost per MW  
  - `lifetime_years`: Solar lifetime  
  - `inverter_capacity`: Inverter size  
  - `data_source`: 'renewables_ninja' or 'csv'  
  - `api_token`, `start_date`, `end_date`: For API data

### 3. **GridComponent**
- **Purpose:** Models grid import/export, connection limits, and price profiles.
- **Key Parameters:**  
  - `max_import`, `max_export` (MW): Grid limits  
  - `price_profile`: Time series of prices  
  - `connection_cost`: Grid connection cost  
  - `export_target`: Export target (MW)

---

## 🏷️ Applications

### 1. **Peak Shaving Application**
- **Goal:** The primary objective of the Peak Shaving Application is to maximize the economic value of solar generation and reduce grid peak demand through optimal battery dispatch. This is achieved by intelligently charging and discharging the battery based on real-time or time-of-use electricity prices and solar availability.
- **How:** Uses battery to shift generation from peak to off-peak periods.
- **Key Metrics:** battery utilization, cost savings.

![Basic build: Optimization model to schedule battery's operation in power grid systems](https://quartux.com/wp-content/uploads/animacion-solucion.gif)

### 2. **Solar Clipping Application**
- **Goal:** Store excess solar energy that would be lost due to inverter limits.
- **How:** Battery charges from clipped solar, discharges when needed.
- **Key Metrics:** Clipped energy captured, battery utilization, solar utilization.

### 3. **Grid Export Target Application**
- **Goal:** Ensure a minimum export to the grid.
- **How:** Optimizes battery and solar operation to meet export targets.
- **Key Metrics:** Export compliance, battery cycles, revenue from export.

---

## 💻 Example Usage

Here's how to run a **Grid Export Target Application** in `main.py`:

```python
from applications.grid_export_target import GridExportTargetApplication

app = GridExportTargetApplication(
    battery_capacity=10.0,  # MWh
    charge_efficiency=0.95,
    discharge_efficiency=0.95,
    standing_loss=0.005,
    c_rate=0.5,
    battery_capex_per_mwh=15000,
    battery_lifetime_years=10,
    has_dedicated_inverter=True,
    solar_capacity=5.0,  # MW
    solar_capex_per_mw=1000000,
    solar_lifetime_years=25,
    solar_inverter_capacity=5.0,
    max_export=2.0,  # MW
    grid_connection_cost=50000,
    discount_rate=0.08,
    peak_price=0.15,
    offpeak_price=0.08,
    latitude=52.0,
    longitude=13.0,
    api_token=None,
    start_date="2022-01-01",
    end_date="2022-12-31",
    export_target=2.0,
    data_source='csv'
)
results = app.run_optimization()
print(results)
```

---

## 🔍 Component Details

### **BatteryComponent**
- **Variables:** State of Charge (SoC), charge/discharge power.
- **Constraints:** SoC evolution, SoC limits, charge/discharge limits, cyclic operation.

### **SolarComponent**
- **Variables:** Solar generation profile.
- **Constraints:** Generation limits, inverter clipping, integration with battery.

### **GridComponent**
- **Variables:** Grid import/export power.
- **Constraints:** Import/export limits, power balance, export target.

---

## 🏷️ Application Details

### **Peak Shaving Application**
- **Description:** Reduces grid peak demand by charging the battery during off-peak and discharging during peak.
- **Inputs:** Battery and grid parameters, price profile.
- **Outputs:** Peak demand reduction, cost savings.

### **Solar Clipping Application**
- **Description:** Captures excess solar energy that would be clipped by inverter limits and stores it in the battery.
- **Inputs:** Solar and battery parameters, inverter size.
- **Outputs:** Clipped energy captured, improved solar utilization.

### **Grid Export Target Application**
- **Description:** Ensures a minimum export to the grid by optimizing battery and solar operation.
- **Inputs:** Export target, battery, solar, and grid parameters.
- **Outputs:** Export compliance, battery cycles, export revenue.

---

## 📖 References

- [Basic build: Optimization model to schedule battery's operation in power grid systems](https://medium.com/@yeap0022/basic-build-optimization-model-to-schedule-batterys-operation-in-power-grid-systems-51a8c04b3a0e)
- [Battery Optimization Model GitHub](https://github.com/zealix/battery-optimization)
