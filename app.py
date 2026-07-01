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
st.warning(
    "This is a 1D cycle model for preliminary design and sensitivity analysis. "
    "It does not replace CFD, compressor maps, structural analysis, rotor dynamics, "
    "or experimental validation."
)

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
fixed_A9_cm2 = st.sidebar.number_input(
    "Fixed exhaust area A9 [cm²]",
    value=87.0,
    min_value=1.0,
    max_value=300.0,
    step=0.1
)

fixed_A9_m2 = fixed_A9_cm2 / 10000.0

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
    Cv_nozzle=Cv_nozzle,
    fixed_A9=fixed_A9_m2
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

# ============================================================
# Design Point Comparison
# ============================================================

st.subheader("Design-Point Comparison")

design_comparison_data = [
    {
        "Quantity": "Thrust",
        "Frozen Design": 790.0,
        "Current Model": results["gross_thrust_N"],
        "Units": "N",
    },
    {
        "Quantity": "T05",
        "Frozen Design": 834.7,
        "Current Model": results["T05_K"],
        "Units": "K",
    },
    {
        "Quantity": "P05",
        "Frozen Design": 154.8,
        "Current Model": results["P05_kPa"],
        "Units": "kPa",
    },
    {
        "Quantity": "NPR",
        "Frozen Design": 1.53,
        "Current Model": results["NPR_P05_over_Pamb"],
        "Units": "-",
    },
]

design_df = pd.DataFrame(design_comparison_data)

design_df["Difference"] = design_df["Current Model"] - design_df["Frozen Design"]
design_df["Difference [%]"] = (
    design_df["Difference"] / design_df["Frozen Design"] * 100.0
)

design_df["Frozen Design"] = design_df["Frozen Design"].round(3)
design_df["Current Model"] = design_df["Current Model"].round(3)
design_df["Difference"] = design_df["Difference"].round(3)
design_df["Difference [%]"] = design_df["Difference [%]"].round(2)

st.dataframe(design_df, use_container_width=True)
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
        "Temperature [K]": results["T02_K"],
        "Pressure [kPa]": results["P02_kPa"],
    },
    {
        "Station": "03",
        "Location": "Compressor exit / combustor inlet",
        "Temperature [K]": results["T03_K"],
        "Pressure [kPa]": results["P03_kPa"],
    },
    {
        "Station": "04",
        "Location": "Combustor exit / turbine inlet",
        "Temperature [K]": results["T04_K"],
        "Pressure [kPa]": results["P04_kPa"],
    },
    {
        "Station": "05",
        "Location": "Turbine exit / nozzle inlet",
        "Temperature [K]": results["T05_K"],
        "Pressure [kPa]": results["P05_kPa"],
    },
    {
        "Station": "09",
        "Location": "Nozzle exit",
        "Temperature [K]": results["T9_K"],
        "Pressure [kPa]": results["P9_kPa"],
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


# ============================================================
# Sensitivity Sweeps
# ============================================================

st.subheader("Sensitivity Sweeps")

if st.button("Run Sensitivity Sweeps"):
    fixed_A9 = fixed_A9_m2
    sweep_rows = run_all_sweeps(inputs, fixed_A9)
    sweep_df = pd.DataFrame(sweep_rows)

    # ============================================================
    # Automatic Sensitivity Summary
    # ============================================================

    worst_thrust_row = sweep_df.loc[sweep_df["thrust_N"].idxmin()]
    largest_A9_row = sweep_df.loc[sweep_df["A9_drift_percent"].abs().idxmax()]
    flag_count = int(sweep_df["A9_flag"].sum())

    st.markdown("### Automatic Sweep Summary")

    summary_col1, summary_col2, summary_col3 = st.columns(3)

    summary_col1.metric(
        "Worst Thrust Case",
        f"{worst_thrust_row['thrust_N']:.1f} N",
        f"{worst_thrust_row['swept_variable']} = {worst_thrust_row['swept_value']}"
    )

    summary_col2.metric(
        "Largest |A9 Drift|",
        f"{largest_A9_row['A9_drift_percent']:.2f}%",
        f"{largest_A9_row['swept_variable']} = {largest_A9_row['swept_value']}"
    )

    summary_col3.metric(
        "Flagged Cases",
        flag_count
    )

    st.markdown("### Sweep Conclusion")

    if flag_count > 0:
        st.warning(
            "Some sweep cases exceed the ±5% A9 drift limit. "
            "These cases should be reviewed before freezing nozzle, turbine, or combustor geometry."
        )
    else:
        st.success(
            "All sweep cases stayed within the ±5% A9 drift limit. "
            "Based on this 1D model, the fixed exhaust area appears robust across the tested uncertainty range."
        )

    if worst_thrust_row["thrust_N"] < 760:
        st.warning(
            "At least one sweep case produces thrust significantly below the 800 N target. "
            "The design is sensitive to one or more assumptions and should be reviewed."
        )
    else:
        st.success(
            "The lowest thrust case remains reasonably close to the 800 N target across the tested sweeps."
        )

    st.markdown("### Full Sensitivity Sweep Table")
    st.dataframe(sweep_df, use_container_width=True)

    st.download_button(
        label="Download sensitivity_sweeps.csv",
        data=sweep_df.to_csv(index=False),
        file_name="sensitivity_sweeps.csv",
        mime="text/csv"
    )

    st.markdown("---")
    st.markdown("### Sensitivity Plots")

    # Create filtered dataframes for each variable
    eta_c_df = sweep_df[sweep_df["swept_variable"] == "eta_c"].copy()
    eta_tt_df = sweep_df[sweep_df["swept_variable"] == "eta_tt"].copy()
    tit_df = sweep_df[sweep_df["swept_variable"] == "TIT_T04"].copy()
    combustor_loss_df = sweep_df[sweep_df["swept_variable"] == "combustor_pressure_loss"].copy()

    # Make sure numeric columns are actually numeric
    for df in [eta_c_df, eta_tt_df, tit_df, combustor_loss_df]:
        df["swept_value"] = pd.to_numeric(df["swept_value"])
        df["thrust_N"] = pd.to_numeric(df["thrust_N"])
        df["A9_drift_percent"] = pd.to_numeric(df["A9_drift_percent"])
        df["NPR"] = pd.to_numeric(df["NPR"])

    # Plot 1: Thrust vs Compressor Efficiency
    st.markdown("#### Thrust vs Compressor Efficiency")
    st.line_chart(
        eta_c_df,
        x="swept_value",
        y="thrust_N"
    )

    # Plot 2: Thrust vs Turbine Efficiency
    st.markdown("#### Thrust vs Turbine Efficiency")
    st.line_chart(
        eta_tt_df,
        x="swept_value",
        y="thrust_N"
    )

    # Plot 3: Thrust vs Turbine Inlet Temperature
    st.markdown("#### Thrust vs Turbine Inlet Temperature")
    st.line_chart(
        tit_df,
        x="swept_value",
        y="thrust_N"
    )

    # Plot 4: A9 Drift vs Compressor Efficiency
    st.markdown("#### A9 Drift vs Compressor Efficiency")
    st.line_chart(
        eta_c_df,
        x="swept_value",
        y="A9_drift_percent"
    )

    # Plot 5: NPR vs Combustor Pressure Loss
    st.markdown("#### NPR vs Combustor Pressure Loss")
    st.line_chart(
        combustor_loss_df,
        x="swept_value",
        y="NPR"
    )


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
