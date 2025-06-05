# import os
# import sys
# import streamlit as st
# import pandas as pd

# # Ensure project modules are accessible
# project_root = os.path.dirname(os.path.abspath(__file__))
# sys.path.insert(0, project_root)

# # Import your domain modules
# from applications.solar_clipping import SolarClippingApplication

# st.title("Solar Clipping Optimization Dashboard")

# # Sidebar Inputs
# st.sidebar.header("Simulation Parameters")

# solar_capacity = st.sidebar.number_input("Solar Capacity (MW)", value=20.0)
# inverter_capacity = st.sidebar.number_input("Inverter Capacity (MW)", value=10.0)
# battery_capacity = st.sidebar.number_input("Battery Capacity (MWh, None for optimal)", value=0.0)
# battery_capacity = None if battery_capacity == 0.0 else battery_capacity

# max_export = st.sidebar.number_input("Max Export Limit (MW)", value=100.0)
# discount_rate = st.sidebar.number_input("Discount Rate", value=0.08)
# peak_price = st.sidebar.number_input("Peak Price ($/MWh)", value=30.0)
# offpeak_price = st.sidebar.number_input("Off-Peak Price ($/MWh)", value=30.0)

# latitude = st.sidebar.number_input("Latitude", value=28.6139)
# longitude = st.sidebar.number_input("Longitude", value=77.2090)

# api_token = st.sidebar.text_input("API Token", value="ec07a7a7ee0b18ae2f6f28fc237a58dfe4b52b5a", type="password")

# start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
# end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("2023-12-31"))

# clip_threshold = st.sidebar.slider("Clip Threshold (fraction of solar capacity)", min_value=0.0, max_value=1.0, value=0.8)

# # Run simulation
# if st.button("Run Optimization"):
#     with st.spinner("Running solar clipping optimization..."):

#         app = SolarClippingApplication(
#             battery_capacity=battery_capacity,
#             solar_capacity=solar_capacity,
#             inverter_capacity=inverter_capacity,
#             max_export=max_export,
#             discount_rate=discount_rate,
#             peak_price=peak_price,
#             offpeak_price=offpeak_price,
#             latitude=latitude,
#             longitude=longitude,
#             api_token=api_token,
#             start_date=start_date.strftime('%Y-%m-%d'),
#             end_date=end_date.strftime('%Y-%m-%d'),
#             clip_threshold=clip_threshold
#         )

#         # Solar generation
#         generation_profile = app.solar_model.generation_profile
#         st.subheader("Solar Generation Profile (2023)")
#         st.metric("Total Annual Generation (MWh)", f"{generation_profile.sum():.2f}")
#         st.metric("Average Daily Generation (MW)", f"{generation_profile.mean():.2f}")
#         st.metric("Peak Generation (MW)", f"{generation_profile.max():.2f}")
#         st.line_chart(generation_profile)

#         # Price profile
#         price_profile = app.grid_params.price_profile
#         st.subheader("Price Profile (2023)")
#         st.metric("Average Price ($/MWh)", f"{price_profile.mean():.2f}")
#         st.metric("Max Price ($/MWh)", f"{price_profile.max():.2f}")
#         st.metric("Min Price ($/MWh)", f"{price_profile.min():.2f}")
#         st.line_chart(price_profile)

#         # Optimization
#         results = app.run_optimization()
#         summary = app.get_summary(results)

#         st.subheader("Optimization Summary")
#         st.json(summary)

#         if 'clipping' in results:
#             st.subheader("Clipping Results")
#             st.metric("Clipping Threshold", f"{results['clipping']['threshold']:.2f}")
#             st.metric("Clipped Energy (MWh)", f"{results['clipping']['clipped_energy']:.2f}")

#         # Optional: download CSV
#         st.download_button("Download Generation Profile CSV", generation_profile.to_csv().encode(), file_name="generation_profile.csv")
#         st.download_button("Download Price Profile CSV", price_profile.to_csv().encode(), file_name="price_profile.csv")



import os
import sys
import streamlit as st
import pandas as pd

# Add the project root to PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from applications.solar_clipping import SolarClippingApplication
# from applications.peak_shaving import PeakShavingApplication
# from battery_components.solar import SolarParameters

def main():
    st.title("Solar Clipping Optimization Dashboard (Streamlit Version)")

    st.sidebar.header("Simulation Parameters")

    solar_capacity = st.sidebar.number_input("Solar Capacity (MW)", value=20.0)
    inverter_capacity = st.sidebar.number_input("Inverter Capacity (MW)", value=10.0)
    battery_capacity = st.sidebar.number_input("Battery Capacity (MWh, None for optimal)", value=0.0)
    battery_capacity = None if battery_capacity == 0.0 else battery_capacity

    max_export = st.sidebar.number_input("Max Export Limit (MW)", value=100.0)
    discount_rate = st.sidebar.number_input("Discount Rate", value=0.08)
    peak_price = st.sidebar.number_input("Peak Price ($/MWh)", value=30.0)
    offpeak_price = st.sidebar.number_input("Off-Peak Price ($/MWh)", value=30.0)

    latitude = st.sidebar.number_input("Latitude", value=28.6139)
    longitude = st.sidebar.number_input("Longitude", value=77.2090)

    api_token = st.sidebar.text_input("API Token", value="ec07a7a7ee0b18ae2f6f28fc237a58dfe4b52b5a", type="password")

    start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
    end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("2023-12-31"))

    clip_threshold = st.sidebar.slider("Clip Threshold (fraction of solar capacity)", min_value=0.0, max_value=1.0, value=0.8)

    if st.button("Run Optimization"):
        with st.spinner("Running optimization..."):
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
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                clip_threshold=clip_threshold
            )

            # Solar generation
            generation_profile = app.solar_model.generation_profile
            st.subheader("Solar Generation Profile (2023)")
            st.metric("Total Annual Generation (MWh)", f"{generation_profile.sum():.2f}")
            st.metric("Average Daily Generation (MW)", f"{generation_profile.mean():.2f}")
            st.metric("Peak Generation (MW)", f"{generation_profile.max():.2f}")
            st.line_chart(generation_profile)

            # Price profile
            price_profile = app.grid_params.price_profile
            st.subheader("Price Profile (2023)")
            st.metric("Average Price ($/MWh)", f"{price_profile.mean():.2f}")
            st.metric("Max Price ($/MWh)", f"{price_profile.max():.2f}")
            st.metric("Min Price ($/MWh)", f"{price_profile.min():.2f}")
            st.line_chart(price_profile)

            results = app.run_optimization()
            summary = app.get_summary(results)

            st.subheader("Optimization Summary")
            st.json(summary)

            if 'clipping' in results:
                st.subheader("Clipping Results")
                st.metric("Clipping Threshold", f"{results['clipping']['threshold']:.2f}")
                st.metric("Clipped Energy (MWh)", f"{results['clipping']['clipped_energy']:.2f}")

            st.download_button("Download Generation Profile CSV", generation_profile.to_csv().encode(), file_name="generation_profile.csv")
            st.download_button("Download Price Profile CSV", price_profile.to_csv().encode(), file_name="price_profile.csv")

if __name__ == "__main__":
    main()
