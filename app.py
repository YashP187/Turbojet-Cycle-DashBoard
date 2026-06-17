import streamlit as st
import pandas as pd

from cycle_model import CycleInputs, run_cycle, run_all_sweeps


st.set_page_config(
    page_title="Turbojet Cycle Calculator",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 Turbojet Cycle Dashboard")
st.caption("Single-spool Brayton-cycle calculator with thrust, nozzle, and sensitivity checks.")


# Sidebar inputs
st.sidebar.header("Engine Inputs")

mdot_air = st.sidebar.slider("Air mass flow ṁ [kg/s]", 1.0, 2.5, 1.8, 0.01)
pressure_ratio_c = st.sidebar.slider("Compressor pressure ratio PR", 1.5, 5.0, 3.0, 0.05)
TIT_T04 = st.sidebar.slider("Turbine inlet temperature T04 / TIT [K]", 700.0, 1200.0, 950.0, 5.0)

eta_c = st.sidebar.slider("Compressor efficiency ηc", 0.50, 0.95, 0.87046, 0.005)
eta_tt = st.sidebar.slider("Turbine total-to-total efficiency ηtt", 0.60, 0.95, 0.915, 0.005)
eta_m = st.sidebar.slider("Mechanical efficiency ηm", 0.80, 1.00, 0.93, 0.005)

combustor_pressure_loss = st.sidebar.slider("Combustor pressure loss", 0.00, 0.25, 0.10, 0.005)
Cv_nozzle = st.sidebar.slider("Nozzle velocity coefficient Cv", 0.85, 1.00, 1.00, 0.005)

T02 = st.sidebar.number_input("Compressor inlet temperature T02 [K]", value=288.0)
P02 = st.sidebar.number_input("Compressor inlet pressure P02 [kPa]", value=101.325)


# Run model
inputs = CycleInputs(
    T02=T02,
    P02=P02,
    mdot_air=mdot_air,
    pressure_ratio_c=pressure_ratio_c,
    TIT_T04=TIT_T04,
    eta_c=eta_c,
    eta_tt=eta_tt,
    eta_m=eta_m,
    combustor_pressure_loss=combustor_pressure_loss,
    Cv_nozzle=Cv_nozzle
)

results = run_cycle(inputs)


# Main results
st.subheader("Main Results")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Thrust [N]", f"{results['gross_thrust_N']:.1f}")
col2.metric("Jet velocity V9 [m/s]", f"{results['V9_m_per_s']:.1f}")
col3.metric("NPR", f"{results['NPR_P05_over_Pamb']:.3f}")
col4.metric("Nozzle state", results["nozzle_state"])

col5, col6, col7, col8 = st.columns(4)

col5.metric("T05 [K]", f"{results['T05_K']:.1f}")
col6.metric("P05 [kPa]", f"{results['P05_kPa']:.1f}")
col7.metric("Required A9 [cm²]", f"{results['A9_required_m2'] * 1e4:.2f}")
col8.metric("A9 drift [%]", f"{results['A9_drift_percent']:.2f}")


# Engineering checks
st.subheader("Engineering Checks")

if results["nozzle_state"] == "unchoked":
    st.success("Nozzle is unchoked.")
else:
    st.warning("Nozzle is choked. Choked-flow behavior is active.")

if results["A9_flag_over_limit"]:
    st.warning("Required A9 drift is greater than ±5%. Fixed nozzle geometry may need review.")
else:
    st.success("Required A9 is within the ±5% drift limit.")

if results["gross_thrust_N"] < 760:
    st.warning("Thrust is significantly below the 800 N target.")
elif results["gross_thrust_N"] > 840:
    st.info("Thrust is above the 800 N target.")
else:
    st.success("Thrust is close to the 800 N target.")


# Station table
st.subheader("Station Table")

station_data = [
    {
        "Station": "02",
        "Location": "Compressor inlet",
        "T0 [K]": results["T02_K"],
        "P0 [kPa]": results["P02_kPa"],
    },
    {
        "Station": "03",
        "Location": "Compressor exit / combustor inlet",
        "T0 [K]": results["T03_K"],
        "P0 [kPa]": results["P03_kPa"],
    },
    {
        "Station": "04",
        "Location": "Combustor exit / turbine inlet",
        "T0 [K]": results["T04_K"],
        "P0 [kPa]": results["P04_kPa"],
    },
    {
        "Station": "05",
        "Location": "Turbine exit / nozzle inlet",
        "T0 [K]": results["T05_K"],
        "P0 [kPa]": results["P05_kPa"],
    },
    {
        "Station": "09",
        "Location": "Nozzle exit",
        "T0 [K]": results["T9_K"],
        "P0 [kPa]": results["P9_kPa"],
    },
]

station_df = pd.DataFrame(station_data)
st.dataframe(station_df, use_container_width=True)


# Work balance table
st.subheader("Work Balance")

work_data = [
    {
        "Quantity": "Compressor specific work",
        "Value": results["compressor_specific_work_kJ_per_kg"],
        "Units": "kJ/kg",
    },
    {
        "Quantity": "Compressor power demand",
        "Value": results["compressor_power_kW"],
        "Units": "kW",
    },
    {
        "Quantity": "Required turbine specific work",
        "Value": results["required_turbine_specific_work_kJ_per_kg"],
        "Units": "kJ/kg",
    },
    {
        "Quantity": "Required turbine power",
        "Value": results["required_turbine_power_kW"],
        "Units": "kW",
    },
    {
        "Quantity": "Turbine expansion ratio P04/P05",
        "Value": results["turbine_expansion_ratio_P04_over_P05"],
        "Units": "-",
    },
]

work_df = pd.DataFrame(work_data)
st.dataframe(work_df, use_container_width=True)


# Sensitivity sweeps
st.subheader("Sensitivity Sweeps")

if st.button("Run Sensitivity Sweeps"):
    fixed_A9 = results["A9_required_m2"]
    sweep_rows = run_all_sweeps(inputs, fixed_A9)
    sweep_df = pd.DataFrame(sweep_rows)

    st.dataframe(sweep_df, use_container_width=True)

    st.download_button(
        label="Download sensitivity_sweeps.csv",
        data=sweep_df.to_csv(index=False),
        file_name="sensitivity_sweeps.csv",
        mime="text/csv"
    )

    st.subheader("Thrust by Sweep Case")
    st.bar_chart(sweep_df, x="swept_variable", y="thrust_N")


# Assumptions
st.subheader("Model Assumptions")

st.markdown(
    """
    - 1D Brayton-cycle model.
    - Cold-side gas properties are used before the combustor.
    - Hot-side gas properties are used after the combustor.
    - Constant cp and gamma are assumed.
    - Compressor map and surge margin are not included yet.
    - Detailed combustor chemistry is not included yet.
    - Detailed turbine blade-loss modeling is not included yet.
    - Rotor dynamics and bearing thermal analysis are not included yet.
    """
)
