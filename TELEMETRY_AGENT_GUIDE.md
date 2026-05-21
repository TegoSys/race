# TA2 Telemetry Agent User Guide

## Overview
The TA2 Telemetry Agent is a specialized diagnostic tool designed to analyze engine and vehicle telemetry data for TA2 race cars. It applies a set of domain-expert rules to identify mechanical issues, sensor faults, and performance bottlenecks.

## Core Functionality

### 1. Data Ingestion & Normalization
The agent processes CSV telemetry files (typically from Motec systems). It handles the specific Motec format (skipping unit rows) and normalizes various sensor names into a standardized internal schema to ensure consistency across different data logs.  It also handles simple csv format with column headers and data rows.

### 2. The Rules Engine
The heart of the agent is a modular rules engine that evaluates the telemetry against 10 diagnostic checks derived from domain expertise:

| Rule | Name | Description |
| :--- | :--- | :--- |
| **1** | **Sensor Validation** | Checks for logical values and identifies potential sensor faults (e.g., flatlines at 0). |
| **2** | **RPM Limit** | Flags engine speeds exceeding 6800 RPM for > 0.25s, distinguishing between mechanical over-revs and wheel spin using GPS speed. |
| **3** | **Fuel Trims** | Monitors Fuel Closed Loop Trims 1 & 2 to ensure they remain within the range of -20 to 20. |
| **4** | **Air-Fuel Ratio** | Ensures Exhaust Lambda remains between 0.88 and 0.89 during Wide Open Throttle (WOT). |
| **5** | **Manifold Pressure Ratio** | Calculates the ratio of ambient pressure to actual manifold pressure at WOT for inter-car comparison. |
| **6** | **Ram Effect** | Evaluates the efficiency of the air intake by comparing manifold pressure to vehicle/GPS speed. |
| **7** | **Fuel Consumption** | Analyzes fuel usage during WOT sections to identify discrepancies in fuel samples or ECU control. |
| **8** | **Top Speed Analysis** | Evaluates top speeds relative to the exit speed of the preceding corner. |
| **9** | **Electrical Stability** | Monitors ECU Battery Voltage for stability within the 13.4V–13.8V range. |
| **10** | **Temp & Pressure Stability** | Checks for wild fluctuations in air temperature and ensures constant fuel pressure across the RPM range. |

### 3. Output Reporting
The agent produces a comprehensive report stored in the database. The report is structured into four sections:
1.  **Rule Definitions**: A reference guide explaining what each rule checks.
2.  **Sensor Mapping**: A list of the normalized sensor names used in the analysis.
3.  **Telemetry Analysis Summary**: A table showing the total number of violations per rule and the "worst" value recorded.
4.  **Detailed Violation Log**: A chronological list of every violation, including the file name, timestamp, offending value, reason, and severity.

