"""
Single-Spool Turbojet Cycle Calculator
Version 1

Purpose:
- Reproduce the frozen turbojet design point.
- Compute compressor, combustor, turbine, and nozzle states.
- Check nozzle choking.
- Compute required exhaust area A9.
- Run sensitivity sweeps.

Units:
- Temperature: K
- Pressure: kPa
- cp: kJ/kg-K
- R: kJ/kg-K
- Work: kJ/kg
- Power: kW
- Area: m^2
- Velocity: m/s
- Thrust: N
"""

from dataclasses import dataclass
from typing import Optional
import math
import csv
from copy import deepcopy


# ============================================================
# 1. INPUT BLOCK
#    Change design assumptions here.
# ============================================================

@dataclass
class CycleInputs:
    # Ambient / inlet
    T02: float = 288.0          # Compressor inlet total temperature [K]
    P02: float = 101.325       # Compressor inlet total pressure [kPa]

    # Main design point
    mdot_air: float = 1.8      # Air mass flow rate [kg/s]
    pressure_ratio_c: float = 3.0
    TIT_T04: float = 950.0     # Turbine inlet total temperature [K]

    # Efficiencies
    eta_c: float = 0.87046     # Compressor efficiency [-]
    eta_tt: float = 0.915      # Turbine total-to-total efficiency [-]
    eta_m: float = 0.93        # Mechanical efficiency [-]

    # Combustor
    combustor_pressure_loss: float = 0.10  # Fractional pressure loss, 0.10 = 10%

    # Nozzle
    Cv_nozzle: float = 1.00    # Velocity coefficient [-]
    P_ambient: float = 101.325 # Ambient pressure [kPa]

    # Gas properties, cold side
    gamma_cold: float = 1.40
    cp_cold: float = 1.005     # [kJ/kg-K]
    R_cold: float = 0.287      # [kJ/kg-K]

    # Gas properties, hot side
    gamma_hot: float = 1.333
    cp_hot: float = 1.148      # [kJ/kg-K]
    R_hot: float = 0.287       # [kJ/kg-K]

    # Fuel mass convention
    # 1.000 means ignore fuel mass in turbine/nozzle mass flow.
    # 1.017 would roughly model 1.8 kg/s air becoming about 1.83 kg/s gas.
    fuel_mass_factor: float = 1.000

    # Fixed geometry reference
    # If None, the design-point required A9 becomes the reference A9.
    fixed_A9: Optional[float] = None

    # Warning threshold for required area drift
    A9_drift_limit: float = 0.05  # 5%


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def compressor_exit_temperature(T_in, pressure_ratio, gamma, eta_c):
    """
    Computes real compressor outlet total temperature using compressor efficiency.

    Isentropic:
        T03s = T02 * PR^((gamma - 1)/gamma)

    Real:
        eta_c = (T03s - T02)/(T03 - T02)

    Therefore:
        T03 = T02 + (T03s - T02)/eta_c
    """
    T_out_s = T_in * pressure_ratio ** ((gamma - 1.0) / gamma)
    T_out = T_in + (T_out_s - T_in) / eta_c
    return T_out, T_out_s


def turbine_exit_pressure_from_efficiency(P04, T04, T05, gamma_hot, eta_tt):
    """
    Computes turbine exit pressure using total-to-total efficiency.

    For a turbine:
        eta_tt = (T04 - T05_actual)/(T04 - T05_isentropic)

    So:
        T05s = T04 - (T04 - T05_actual)/eta_tt

    Then:
        P05/P04 = (T05s/T04)^(gamma/(gamma-1))
    """
    actual_drop = T04 - T05
    ideal_drop = actual_drop / eta_tt
    T05s = T04 - ideal_drop

    pressure_ratio = (T05s / T04) ** (gamma_hot / (gamma_hot - 1.0))
    P05 = P04 * pressure_ratio

    return P05, T05s


def critical_pressure_ratio(gamma):
    """
    Critical NPR for choking in a converging nozzle.

    Choking occurs when:
        P0/P_ambient >= [(gamma + 1)/2]^(gamma/(gamma-1))

    For gamma = 1.333, this is about 1.85.
    """
    return ((gamma + 1.0) / 2.0) ** (gamma / (gamma - 1.0))


def nozzle_unchoked(P05, T05, P_ambient, gamma, cp, R, Cv, mdot_gas):
    """
    Subsonic nozzle model.

    Assumption:
    - Nozzle fully expands to ambient pressure.
    - P9 = P_ambient.
    - Velocity comes from total-to-static temperature drop.
    """
    P9 = P_ambient
    T9_ideal = T05 * (P9 / P05) ** ((gamma - 1.0) / gamma)

    V9_ideal = math.sqrt(2.0 * cp * 1000.0 * (T05 - T9_ideal))
    V9 = Cv * V9_ideal

    a9 = math.sqrt(gamma * R * 1000.0 * T9_ideal)
    M9 = V9 / a9

    rho9 = P9 / (R * T9_ideal)
    A9_required = mdot_gas / (rho9 * V9)

    pressure_thrust = 0.0
    gross_thrust = mdot_gas * V9 + pressure_thrust

    return {
    "nozzle_state": "unchoked",
    "P9_kPa": P9,
    "T9_K": T9_ideal,
    "V9_m_per_s": V9,
    "M9": M9,
    "rho9_kg_per_m3": rho9,
    "A9_required_m2": A9_required,
    "pressure_thrust_N": pressure_thrust,
    "gross_thrust_N": gross_thrust,
}


def nozzle_choked(P05, T05, P_ambient, gamma, cp, R, Cv, mdot_gas):
    """
    Choked converging nozzle model.

    Assumption:
    - Exit/throat Mach number is 1.
    - Static exit pressure is critical pressure.
    - If P9 > P_ambient, pressure thrust exists.
    """
    T9 = T05 * (2.0 / (gamma + 1.0))
    P9 = P05 * (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))

    a9 = math.sqrt(gamma * R * 1000.0 * T9)
    V9_ideal = a9
    V9 = Cv * V9_ideal

    M9 = 1.0
    rho9 = P9 / (R * T9)
    A9_required = mdot_gas / (rho9 * V9)

    # Convert kPa to Pa for pressure thrust:
    pressure_thrust = (P9 - P_ambient) * 1000.0 * A9_required
    gross_thrust = mdot_gas * V9 + pressure_thrust

    return {
    "nozzle_state": "choked",
    "P9_kPa": P9,
    "T9_K": T9,
    "V9_m_per_s": V9,
    "M9": M9,
    "rho9_kg_per_m3": rho9,
    "A9_required_m2": A9_required,
    "pressure_thrust_N": pressure_thrust,
    "gross_thrust_N": gross_thrust,
}


# ============================================================
# 3. MAIN CYCLE FUNCTION
# ============================================================

def run_cycle(inputs: CycleInputs):
    """
    Runs the full turbojet cycle front-to-back.

    Stations:
    02: compressor inlet
    03: compressor exit / combustor inlet
    04: combustor exit / turbine inlet
    05: turbine exit / nozzle inlet
    09: nozzle exit
    """

    # -------------------------------
    # Compressor: 02 -> 03
    # -------------------------------
    T03, T03s = compressor_exit_temperature(
        T_in=inputs.T02,
        pressure_ratio=inputs.pressure_ratio_c,
        gamma=inputs.gamma_cold,
        eta_c=inputs.eta_c
    )

    P03 = inputs.P02 * inputs.pressure_ratio_c

    compressor_specific_work = inputs.cp_cold * (T03 - inputs.T02)  # [kJ/kg]
    compressor_power = inputs.mdot_air * compressor_specific_work   # [kW]

    # -------------------------------
    # Combustor: 03 -> 04
    # -------------------------------
    T04 = inputs.TIT_T04
    P04 = P03 * (1.0 - inputs.combustor_pressure_loss)

    heat_added = inputs.cp_hot * (T04 - T03)  # simplified [kJ/kg]

    # -------------------------------
    # Turbine: 04 -> 05
    # -------------------------------
    mdot_gas = inputs.mdot_air * inputs.fuel_mass_factor

    # Turbine must provide compressor work through mechanical losses.
    # If fuel mass is included, more hot gas mass flow shares the turbine work.
    required_turbine_specific_work = compressor_specific_work / (
        inputs.eta_m * inputs.fuel_mass_factor
    )

    required_turbine_power = compressor_power / inputs.eta_m

    T05 = T04 - required_turbine_specific_work / inputs.cp_hot

    P05, T05s = turbine_exit_pressure_from_efficiency(
        P04=P04,
        T04=T04,
        T05=T05,
        gamma_hot=inputs.gamma_hot,
        eta_tt=inputs.eta_tt
    )

    turbine_expansion_ratio = P04 / P05

    # -------------------------------
    # Nozzle: 05 -> 09
    # -------------------------------
    NPR = P05 / inputs.P_ambient
    NPR_crit = critical_pressure_ratio(inputs.gamma_hot)

    if NPR >= NPR_crit:
        nozzle = nozzle_choked(
            P05=P05,
            T05=T05,
            P_ambient=inputs.P_ambient,
            gamma=inputs.gamma_hot,
            cp=inputs.cp_hot,
            R=inputs.R_hot,
            Cv=inputs.Cv_nozzle,
            mdot_gas=mdot_gas
        )
    else:
        nozzle = nozzle_unchoked(
            P05=P05,
            T05=T05,
            P_ambient=inputs.P_ambient,
            gamma=inputs.gamma_hot,
            cp=inputs.cp_hot,
            R=inputs.R_hot,
            Cv=inputs.Cv_nozzle,
            mdot_gas=mdot_gas
        )

    # -------------------------------
    # Area drift flag
    # -------------------------------
    A9_required = nozzle["A9_required_m2"]

    if inputs.fixed_A9 is None:
        fixed_A9 = A9_required
    else:
        fixed_A9 = inputs.fixed_A9

    A9_drift = (A9_required - fixed_A9) / fixed_A9
    A9_flag = abs(A9_drift) > inputs.A9_drift_limit

    # -------------------------------
    # Output dictionary
    # -------------------------------
    results = {
        # Main inputs copied for traceability
        "mdot_air_kg_per_s": inputs.mdot_air,
        "mdot_gas_kg_per_s": mdot_gas,
        "pressure_ratio_c": inputs.pressure_ratio_c,
        "eta_c": inputs.eta_c,
        "eta_tt": inputs.eta_tt,
        "eta_m": inputs.eta_m,
        "TIT_T04_K": inputs.TIT_T04,
        "combustor_pressure_loss": inputs.combustor_pressure_loss,
        "Cv_nozzle": inputs.Cv_nozzle,

        # Compressor
        "T02_K": inputs.T02,
        "P02_kPa": inputs.P02,
        "T03s_K": T03s,
        "T03_K": T03,
        "P03_kPa": P03,
        "compressor_specific_work_kJ_per_kg": compressor_specific_work,
        "compressor_power_kW": compressor_power,

        # Combustor
        "T04_K": T04,
        "P04_kPa": P04,
        "heat_added_kJ_per_kg": heat_added,

        # Turbine
        "required_turbine_specific_work_kJ_per_kg": required_turbine_specific_work,
        "required_turbine_power_kW": required_turbine_power,
        "T05_K": T05,
        "T05s_K": T05s,
        "P05_kPa": P05,
        "turbine_expansion_ratio_P04_over_P05": turbine_expansion_ratio,

        # Nozzle
        "NPR_P05_over_Pamb": NPR,
        "NPR_critical": NPR_crit,
        **nozzle,

        # Geometry matching
        "fixed_A9_m2": fixed_A9,
        "A9_drift_fraction": A9_drift,
        "A9_drift_percent": A9_drift * 100.0,
        "A9_flag_over_limit": A9_flag,
    }

    return results


# ============================================================
# 4. PRINTING FUNCTIONS
# ============================================================

def print_design_point(results):
    """
    Prints a clean design point summary.
    """

    print("\n" + "=" * 70)
    print("SINGLE-SPOOL TURBOJET DESIGN POINT")
    print("=" * 70)

    print("\n--- Station Table ---")
    print(f"Station 02: T02 = {results['T02_K']:.2f} K, "
          f"P02 = {results['P02_kPa']:.3f} kPa")

    print(f"Station 03: T03 = {results['T03_K']:.2f} K, "
          f"P03 = {results['P03_kPa']:.3f} kPa")

    print(f"Station 04: T04 = {results['T04_K']:.2f} K, "
          f"P04 = {results['P04_kPa']:.3f} kPa")

    print(f"Station 05: T05 = {results['T05_K']:.2f} K, "
          f"P05 = {results['P05_kPa']:.3f} kPa")

    print(f"Station 09: T9  = {results['T9_K']:.2f} K, "
          f"P9  = {results['P9_kPa']:.3f} kPa, "
          f"M9 = {results['M9']:.3f}")

    print("\n--- Work Balance ---")
    print(f"Compressor specific work: "
          f"{results['compressor_specific_work_kJ_per_kg']:.2f} kJ/kg")

    print(f"Compressor power demand: "
          f"{results['compressor_power_kW']:.2f} kW")

    print(f"Required turbine specific work: "
          f"{results['required_turbine_specific_work_kJ_per_kg']:.2f} kJ/kg")

    print(f"Required turbine power: "
          f"{results['required_turbine_power_kW']:.2f} kW")

    print("\n--- Nozzle / Thrust ---")
    print(f"Nozzle state: {results['nozzle_state']}")
    print(f"NPR: {results['NPR_P05_over_Pamb']:.3f}")
    print(f"Critical NPR: {results['NPR_critical']:.3f}")
    print(f"Jet velocity V9: {results['V9_m_per_s']:.2f} m/s")
    print(f"Required A9: {results['A9_required_m2']:.6f} m^2 "
          f"= {results['A9_required_m2'] * 1e4:.2f} cm^2")
    print(f"Pressure thrust: {results['pressure_thrust_N']:.2f} N")
    print(f"Gross thrust: {results['gross_thrust_N']:.2f} N")

    print("\n--- Geometry Flag ---")
    print(f"A9 drift: {results['A9_drift_percent']:.2f}%")
    print(f"A9 flag over limit?: {results['A9_flag_over_limit']}")


# ============================================================
# 5. SENSITIVITY SWEEPS
# ============================================================

def sweep_one_variable(base_inputs, variable_name, values, fixed_A9):
    """
    Sweeps one input variable at a time.
    """

    rows = []

    for value in values:
        test_inputs = deepcopy(base_inputs)
        setattr(test_inputs, variable_name, value)
        test_inputs.fixed_A9 = fixed_A9

        result = run_cycle(test_inputs)

        row = {
            "swept_variable": variable_name,
            "swept_value": value,
            "NPR": result["NPR_P05_over_Pamb"],
            "turbine_expansion_ratio": result["turbine_expansion_ratio_P04_over_P05"],
            "T05_K": result["T05_K"],
            "P05_kPa": result["P05_kPa"],
            "A9_required_m2": result["A9_required_m2"],
            "A9_drift_percent": result["A9_drift_percent"],
            "A9_flag": result["A9_flag_over_limit"],
            "nozzle_state": result["nozzle_state"],
            "V9_m_per_s": result["V9_m_per_s"],
            "thrust_N": result["gross_thrust_N"],
        }

        rows.append(row)

    return rows


def run_all_sweeps(base_inputs, fixed_A9):
    """
    Runs the six sweeps requested in the Cycle Model document.
    """

    sweeps = []

    # Turbine efficiency: 0.80 to 0.92
    eta_tt_values = [0.80, 0.83, 0.86, 0.89, 0.92]
    sweeps += sweep_one_variable(base_inputs, "eta_tt", eta_tt_values, fixed_A9)

    # Compressor efficiency: 0.70 to 0.82
    eta_c_values = [0.70, 0.73, 0.76, 0.79, 0.82]
    sweeps += sweep_one_variable(base_inputs, "eta_c", eta_c_values, fixed_A9)

    # Mass flow: +/- 10%
    mdot_base = base_inputs.mdot_air
    mdot_values = [
        0.90 * mdot_base,
        0.95 * mdot_base,
        1.00 * mdot_base,
        1.05 * mdot_base,
        1.10 * mdot_base,
    ]
    sweeps += sweep_one_variable(base_inputs, "mdot_air", mdot_values, fixed_A9)

    # TIT: 900 to 1000 K
    TIT_values = [900, 925, 950, 975, 1000]
    sweeps += sweep_one_variable(base_inputs, "TIT_T04", TIT_values, fixed_A9)

    # Combustor pressure loss: 5% to 15%
    combustor_loss_values = [0.05, 0.075, 0.10, 0.125, 0.15]
    sweeps += sweep_one_variable(
        base_inputs,
        "combustor_pressure_loss",
        combustor_loss_values,
        fixed_A9
    )

    # Nozzle velocity coefficient: 0.95 to 0.99
    Cv_values = [0.95, 0.96, 0.97, 0.98, 0.99]
    sweeps += sweep_one_variable(base_inputs, "Cv_nozzle", Cv_values, fixed_A9)

    return sweeps


def save_sweeps_to_csv(rows, filename="sensitivity_sweeps.csv"):
    """
    Saves sensitivity sweep results to a CSV file.
    """

    if not rows:
        print("No rows to save.")
        return

    fieldnames = list(rows[0].keys())

    with open(filename, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved sensitivity sweep results to: {filename}")


def print_sweep_summary(rows):
    """
    Prints a compact summary of the sweep results.
    """

    print("\n" + "=" * 70)
    print("SENSITIVITY SWEEP SUMMARY")
    print("=" * 70)

    for row in rows:
        flag_text = "FLAG" if row["A9_flag"] else "OK"

        print(
            f"{row['swept_variable']:28s} = {row['swept_value']:8.4f} | "
            f"NPR = {row['NPR']:5.3f} | "
            f"T05 = {row['T05_K']:7.2f} K | "
            f"A9 drift = {row['A9_drift_percent']:7.2f}% | "
            f"Thrust = {row['thrust_N']:8.2f} N | "
            f"{row['nozzle_state']:8s} | "
            f"{flag_text}"
        )


# ============================================================
# 6. MAIN PROGRAM
# ============================================================

def main():
    # Create default design-point inputs
    inputs = CycleInputs()

    # Run design point
    design_results = run_cycle(inputs)

    # Print design point
    print_design_point(design_results)

    # Use design-point A9 as the fixed machined exhaust area
    fixed_A9 = design_results["A9_required_m2"]

    # Run sensitivity sweeps
    sweep_rows = run_all_sweeps(inputs, fixed_A9)

    # Print and save sweeps
    print_sweep_summary(sweep_rows)
    save_sweeps_to_csv(sweep_rows, filename="sensitivity_sweeps.csv")


if __name__ == "__main__":
    main()
