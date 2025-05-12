import os
import sys
import streamlit as st
import pandas as pd
import numpy as np

# Add the project root to PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from applications.solar_clipping import SolarClippingApplication
st.markdown(
    """
    <style>
    /* Change background color of the sidebar */
    [data-testid="stSidebar"] {
        background-color: #cccccf; /* change this to any hex or RGB color */
    }
    </style>
    """,
    unsafe_allow_html=True
)
def main(
    battery_capacity, solar_capacity, inverter_capacity, max_export,
    discount_rate, peak_price, offpeak_price, latitude, longitude,
    api_token, start_date, end_date, clip_threshold
):
    app = SolarClippingApplication(
        battery_capacity=battery_capacity,
        solar_capacity=solar_capacity,
        inverter_capacity=inverter_capacity,
        max_export=max_export,
        discount_rate=discount_rate,
        peak_price=peak_price,
        offpeak_price=offpeak_price,
        latitude=latitude,
        longitude=longitude,
        api_token=api_token,
        start_date=start_date,
        end_date=end_date,
        clip_threshold=clip_threshold
    )

    st.subheader("Solar Generation Profile (2023)")
    generation_profile = app.solar_model.generation_profile
    st.write(f"Total Annual Generation: {generation_profile.sum():.2f} MWh")
    st.write(f"Average Daily Generation: {generation_profile.mean():.2f} MW")
    st.write(f"Peak Generation: {generation_profile.max():.2f} MW")
    st.area_chart(generation_profile)

    st.subheader("Price Profile (2023)")
    price_profile = app.grid_params.price_profile
    st.write(f"Average Price: ${price_profile.mean():.2f}/MWh")
    st.write(f"Maximum Price: ${price_profile.max():.2f}/MWh")
    st.write(f"Minimum Price: ${price_profile.min():.2f}/MWh")
    st.line_chart(price_profile)

    results = app.run_optimization()
    summary = app.get_summary(results)
    st.subheader("Optimization Summary")
    st.write(summary)

    if 'clipping' in results:
        st.subheader("Clipping Results")
        st.write(f"Clipping Threshold: {results['clipping']['threshold']:.2f}")
        st.write(f"Clipped Energy: {results['clipping']['clipped_energy']:.2f} MWh")


if __name__ == "__main__":
    st.title("Solar Clipping Optimization")

    with st.sidebar:
        st.header("Input Parameters")
        solar_capacity = st.number_input("Solar Capacity (MW)", value=20.0)
        inverter_capacity = st.number_input("Inverter Capacity (MW)", value=10.0)
        battery_capacity = st.number_input("Battery Capacity (MWh)", value=0.0)
        battery_capacity = None if battery_capacity == 0.0 else battery_capacity
        max_export = st.number_input("Max Export (MW)", value=100.0)
        discount_rate = st.number_input("Discount Rate", value=0.08)
        peak_price = st.number_input("Peak Price ($/MWh)", value=30.0)
        offpeak_price = st.number_input("Off-peak Price ($/MWh)", value=30.0)
        latitude = st.number_input("Latitude", value=28.6139)
        longitude = st.number_input("Longitude", value=77.2090)
        api_token = st.text_input("API Token", value="your_api_token_here")
        start_date = st.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
        end_date = st.date_input("End Date", value=pd.to_datetime("2023-12-31"))
        clip_threshold = st.slider("Clip Threshold (%)", 0.0, 1.0, 0.8)

    if st.button("Run Optimization"):
        main(
            battery_capacity,
            solar_capacity,
            inverter_capacity,
            max_export,
            discount_rate,
            peak_price,
            offpeak_price,
            latitude,
            longitude,
            api_token,
            str(start_date),
            str(end_date),
            clip_threshold
        )
