# Turbojet Cycle Dashboard

This project is a Streamlit-based 1D Brayton-cycle calculator for a single-spool inline turbojet engine.

## Purpose

The calculator estimates engine station conditions, compressor work, turbine work, nozzle behavior, required exhaust area, and static thrust. It is intended for preliminary design and sensitivity analysis for a student turbojet project.

## Features

- Compressor, combustor, turbine, and nozzle station calculations
- Compressor-turbine work balance
- Nozzle pressure ratio and choking check
- Jet velocity and thrust estimate
- Required exhaust area A9 calculation
- Fixed A9 geometry comparison
- Design-point comparison against frozen hand calculations
- Sensitivity sweeps for:
  - Compressor efficiency
  - Turbine efficiency
  - Mass flow
  - Turbine inlet temperature
  - Combustor pressure loss
  - Nozzle velocity coefficient
- Automatic sweep summary and warning flags

## Model Assumptions

This is a preliminary 1D cycle model.

It does not replace:

- CFD
- Compressor maps
- Turbine blade loss modeling
- Combustor chemistry
- Structural analysis
- Rotor dynamics
- Bearing thermal analysis
- Experimental validation

## Main Files

- `app.py` — Streamlit dashboard interface
- `cycle_model.py` — Brayton-cycle calculation model
- `requirements.txt` — Python package requirements

## Current Design Point

Approximate frozen design point:

| Quantity | Value |
|---|---:|
| Mass flow | 1.8 kg/s |
| Compressor pressure ratio | 3.0 |
| Turbine inlet temperature | 950 K |
| Thrust | ~790–800 N |
| Nozzle state | Unchoked |
| NPR | ~1.53 |
| Required A9 | ~87 cm² |

## Disclaimer

This calculator is for educational and preliminary design use only. Final turbojet design decisions should be supported by CFD, compressor/turbine matching, structural analysis, rotor dynamics, manufacturing review, and test data.
