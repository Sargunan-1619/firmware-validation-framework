# Firmware Validation Framework

[![Validation Status](https://img.shields.io/badge/Validation-37%20Passed%20%2F%200%20Failed-brightgreen)](reports/validation_report.json)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render%20Web%20Dashboard-46E3B7?logo=render)](https://firmware-validation-framework.onrender.com)
[![Docker Ready](https://img.shields.io/badge/Docker-Multi--Stage%20GCC%20%2B%20Python-2496ED?logo=docker)](Dockerfile)
[![Dependencies](https://img.shields.io/badge/Dependencies-Standard%20Library%20Only-success)]()
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

An automated, zero-dependency Python firmware verification and validation framework designed for safety-critical embedded C controllers. Built to validate the compiled executable of **[sensor-fault-controller (Project 1)](https://github.com/Sargunan-1619/sensor-fault-controller)** in read-only black-box mode without modifying any firmware source files.

---

## 🌐 Live Interactive Engineering Dashboard

Experience the complete verification platform running live:

👉 **[Launch Live Dashboard (Render)](https://firmware-validation-framework.onrender.com)** *(Replace with your deployed Render URL once published)*

> [!NOTE]
> **Real Executable Invocations:** The dashboard does **not** mock or simulate controller outputs in JavaScript. When you trigger validation runs or test simulated thermal inputs, the Python backend spawns the real compiled `sensor_controller` C binary in a sandboxed child process, capturing exact stdout, stderr, process exit codes, and latency in milliseconds.

### Key Visual & Verification Features
- **One-Click Automated Suite Execution:** Run all 37 test cases or filter by domain (`normal`, `warning`, `fault`, `boundary`, `invalid_input`, `sensor_error`) with real-time pass/fail streaming.
- **Live C Controller Hardware Demonstration:** Interactive telemetry console that executes the real compiled `sensor_controller` process in user space with simulated inputs, visualizing real-time thermal gauges, state machine transitions (`NORMAL`, `WARNING`, `FAULT`), active fault codes, exit codes, and latency.
- **Side-by-Side Expected vs. Actual Inspector:** Deep-dive cards showing parameter arrays, exact expected values vs actual binary outputs, execution duration, and failure diagnostics.
- **In-Browser JSON Report Viewer & Download:** Inspect the generated `validation_report.json` in an interactive modal or download it directly.
- **Zero External Dependencies:** Built with Python standard library (`http.server`, `subprocess`, `dataclasses`, `json`) and vanilla CSS/JS.

---

## Architecture & Concept Overview

```
                          +------------------------------------------------+
                          |      Firmware Validation Framework (Python)     |
                          +------------------------------------------------+
                                        |                      |
                   Web Dashboard Server (server.py)       CLI Runner (validate.py)
                                        \                      /
                                         v                    v
                                  +--------------------------------+
                                  |        ValidationRunner        |
                                  +--------------------------------+
                                                  |
                        +-------------------------+-------------------------+
                        |                                                   |
                        v                                                   v
          +---------------------------+                       +---------------------------+
          |     ControllerClient      |                       |      AssertionEngine      |
          |  (subprocess, timeouts,   |                       |  (exit code, state, fault,|
          |    stdout/stderr parsing) |                       |   temp, regex assertions) |
          +---------------------------+                       +---------------------------+
                        |                                                   |
                        | Invokes Child Process                             | Evaluates
                        v                                                   v
          +---------------------------+                       +---------------------------+
          |      sensor_controller    |---------------------->|     ValidationSummary     |
          |   (Compiled ISO C11)      |    Exit Code & STDOUT |    (JSON Report Output)   |
          +---------------------------+                       +---------------------------+
```

### Essential Python & Testing Concepts Applied

1. **Standard Library Zero-Dependency Design**:
   - Implemented entirely with Python built-in modules (`subprocess`, `dataclasses`, `enum`, `typing`, `json`, `argparse`, `time`, `pathlib`, `re`, `unittest`, `http.server`).
   - Requires no third-party packages; runs identically in local development, CI/CD runners, and Docker containers.

2. **Subprocess Management & Execution Isolation**:
   - Uses `subprocess.run` to spawn the compiled C controller as a decoupled child process.
   - Enforces strict execution timeouts (`subprocess.TimeoutExpired`) to prevent hung processes from blocking test pipelines.
   - Catches operating system failures (`FileNotFoundError`, `PermissionError`, `OSError`) gracefully without crashing the validation suite.

3. **Deterministic Output & Telemetry Parsing**:
   - Regular expression parsing extracts telemetry fields (`STATE`, `TEMP`, `FAULT`) from standard output.
   - Converts temperature strings to high-precision floating-point values while handling special tokens (`INVALID`, `NAN`, `INF`).

4. **Multi-Domain Assertion Engine**:
   - Compares expected vs. actual outcomes across 5 dimensions:
     1. **Process Exit Code**: `0` (Nominal/Warning), `2` (Critical Fault), `1` (CLI Syntax Error).
     2. **State Machine State**: `STATE_NORMAL`, `STATE_WARNING`, `STATE_FAULT`.
     3. **Active Fault Code**: `FAULT_NONE`, `FAULT_OVER_TEMP`, `FAULT_SENSOR_UNDER_RANGE`, etc.
     4. **Temperature Telemetry**: Floating-point tolerance comparison (`math.isclose` within ±0.02°C).
     5. **Pattern Matching**: Regex matching on `stderr` (e.g. usage messages on syntax errors).

5. **Multi-Platform Binary Resolution**:
   - `binary_resolver.py` dynamically locates either the Windows executable (`sensor_controller.exe`) or Linux binary (`sensor_controller`), checking local build paths, sibling Project 1 directories, and containerized deployment paths.

---

## Repository Structure

```text
firmware-validation-framework/
├── .github/workflows/
│   └── validate.yml               # Automated CI matrix for Python 3.10, 3.11, 3.12
├── .gitignore                     # Git ignore rules
├── LICENSE                        # MIT License
├── README.md                      # Comprehensive architecture and validation evidence
├── Dockerfile                     # Multi-stage Docker build for Render deployment
├── render.yaml                    # Infrastructure-as-code deployment specification
├── requirements.txt               # Documented zero-dependency manifest
├── server.py                      # Lightweight standard-library HTTP dashboard server
├── validate.py                    # Primary CLI runner entrypoint
├── dashboard/                     # Professional engineering web dashboard
│   ├── favicon.svg                # Dashboard icon
│   ├── index.html                 # Semantic HTML5 UI layout
│   ├── dashboard.css              # Dark-mode industrial engineering styles
│   └── dashboard.js               # Client-side telemetry and test viewer logic
├── framework/
│   ├── __init__.py                # Package metadata and version definition
│   ├── assertions.py              # Verification engine and failure diagnostics
│   ├── binary_resolver.py         # Cross-platform relative discovery for C executable
│   ├── controller_client.py       # Subprocess execution, timeouts, and output parsing
│   ├── models.py                  # Dataclasses and enums (TestCase, ExecutionResult, etc.)
│   ├── reporter.py                # ANSI console renderer and JSON report writer
│   ├── runner.py                  # Test orchestration and statistics aggregator
│   ├── test_definitions.py        # Curated catalog of 37 validation test cases
│   └── unittest_adapter.py        # Bridge to Python standard unittest discovery
├── tests/
│   ├── __init__.py                # Internal test suite initialization
│   ├── test_assertions.py         # Unit tests for the AssertionEngine
│   ├── test_controller_client.py  # Unit tests for telemetry parsing & timeouts
│   ├── test_reporter.py           # Unit tests for JSON report generation
│   └── test_runner.py             # Unit tests for execution orchestration
└── reports/
    └── validation_report.json     # Generated machine-readable validation report
```

---

## Test Inventory & Coverage (37 Test Cases)

| Test Category | Count | Scope & Physical Description | Expected Outcome |
| :--- | :---: | :--- | :--- |
| **Normal Operational** | 5 | Nominal temperatures (25°C, 0°C, -20°C, 45°C, 59.9°C) | `STATE_NORMAL`, `FAULT_NONE`, Exit `0` |
| **Warning Operational** | 4 | Elevated temperatures (60.0°C, 68.5°C, 75.0°C, 79.9°C) | `STATE_WARNING`, `FAULT_NONE`, Exit `0` |
| **Fault Operational** | 3 | Over-temperature trips (80.0°C, 88.5°C, 120.0°C) | `STATE_FAULT`, `FAULT_OVER_TEMP`, Exit `2` |
| **Boundary Conditions** | 10 | Min physical (-40.0°C / -40.1°C), Max physical (150.0°C / 150.1°C), Warn delta (59.99°C / 60.00°C), Fault delta (79.99°C / 80.00°C) | Strict threshold verification |
| **Invalid Inputs** | 7 | Tokens (`INVALID`, `NAN`, `INF`, `-INF`, `ERROR`), alphanumeric noise, zero CLI arguments | `STATE_FAULT` / Exit `2`, or Exit `1` on missing args |
| **Sensor Hardware Status** | 7 | Driver flags (`DISCONNECTED`, `COMM_TIMEOUT`, `OUT_OF_BOUNDS`, `INVALID`, case-insensitive strings) | Specific fault code latching |
| **Execution Robustness** | 1 | Missing executable detection and defensive error reporting | `TestStatus.PASSED` (clean error handled) |

---

## Local Getting Started

### Prerequisites
- **Python 3.10+** (tested on Python 3.14)
- Compiled Project 1 binary (`sensor_controller.exe` or Linux binary)

### Running the Web Dashboard Locally
```powershell
# Launch on localhost:8080
python server.py

# Optional: specify custom port or host
python server.py --port 8080 --host 127.0.0.1
```

Once launched, navigate to:
👉 **`http://127.0.0.1:8080`**

### Running All Validation Tests (CLI)
```bash
# Run full suite using dynamic binary discovery
python validate.py

# Specify custom controller binary path
python validate.py --target "path/to/sensor_controller.exe"
```

### Running Specific Test Suites
```bash
# Run only boundary condition tests
python validate.py --suite boundary

# Run only sensor hardware error tests
python validate.py --suite sensor_error

# Run only invalid input tests
python validate.py --suite invalid_input
```

Available suite filters: `all`, `normal`, `warning`, `fault`, `boundary`, `invalid_input`, `sensor_error`, `execution_failure`.

### Running via Standard `unittest`
```bash
# Run test catalog through unittest runner
python -m unittest framework/unittest_adapter.py

# Run framework internal unit tests (16/16 Passing)
python -m unittest discover tests
```

---

## Real Validation Results (37 / 37 Passing)

Actual console output executing against the compiled `sensor_controller.exe`:

```text
================================================================================
 FIRMWARE AUTOMATED VALIDATION FRAMEWORK 
================================================================================
 Target Executable : .../scratch/sensor_fault_controller/build/sensor_controller.exe
 Suite Filter      : ALL
--------------------------------------------------------------------------------
TEST ID        CATEGORY       STATUS     TIME (ms)  TEST NAME
--------------------------------------------------------------------------------
TC-NORM-01     normal         [PASS]        70.68  Nominal Ambient Temperature
TC-NORM-02     normal         [PASS]        60.79  Zero Degree Operating Point
TC-NORM-03     normal         [PASS]        58.06  Valid Sub-Zero Temperature
TC-NORM-04     normal         [PASS]        69.31  Elevated Nominal Temperature
TC-NORM-05     normal         [PASS]        58.45  Upper Normal Range Just Below Warning
TC-WARN-01     warning        [PASS]        56.37  Exact Warning Threshold
TC-WARN-02     warning        [PASS]        70.01  Mid Warning Temperature
TC-WARN-03     warning        [PASS]        82.09  Elevated Warning Temperature
TC-WARN-04     warning        [PASS]        72.91  High Warning Just Below Fault
TC-FLT-01      fault          [PASS]        69.86  Exact Fault Threshold
TC-FLT-02      fault          [PASS]        73.00  High Over-Temperature Trip
TC-FLT-03      fault          [PASS]        83.13  Extreme High Over-Temperature
TC-BND-01      boundary       [PASS]        86.49  Transducer Physical Minimum Boundary
TC-BND-02      boundary       [PASS]        88.69  Under-Range Infinitesimal Breach
TC-BND-03      boundary       [PASS]        88.13  Extreme Under-Range Temperature
TC-BND-04      boundary       [PASS]        88.52  Warning Boundary Delta Lower
TC-BND-05      boundary       [PASS]        91.32  Warning Boundary Delta Exact
TC-BND-06      boundary       [PASS]        94.53  Fault Boundary Delta Lower
TC-BND-07      boundary       [PASS]        75.65  Fault Boundary Delta Exact
TC-BND-08      boundary       [PASS]        62.34  Transducer Physical Maximum Boundary
TC-BND-09      boundary       [PASS]        69.88  Over-Range Infinitesimal Breach
TC-BND-10      boundary       [PASS]        53.52  Extreme Over-Range Temperature
TC-INV-01      invalid_input  [PASS]        67.64  Explicit INVALID Keyword
TC-INV-02      invalid_input  [PASS]        68.86  Explicit NAN Token
TC-INV-03      invalid_input  [PASS]        73.80  Explicit Positive Infinity Token
TC-INV-04      invalid_input  [PASS]        90.93  Explicit Negative Infinity Token
TC-INV-05      invalid_input  [PASS]        65.49  Explicit ERROR Token
TC-INV-06      invalid_input  [PASS]        50.35  Non-Numeric Garbage String
TC-INV-07      invalid_input  [PASS]        48.87  Missing CLI Arguments (Syntax Error)
TC-SNS-01      sensor_error   [PASS]        40.88  Sensor Disconnected Hardware Flag
TC-SNS-02      sensor_error   [PASS]        40.74  Communication Bus Timeout Flag
TC-SNS-03      sensor_error   [PASS]        46.03  Hardware Out of Bounds Lower Flag
TC-SNS-04      sensor_error   [PASS]        44.92  Hardware Out of Bounds Upper Flag
TC-SNS-05      sensor_error   [PASS]        64.03  Hardware Status Invalid Flag
TC-SNS-06      sensor_error   [PASS]        48.85  Case-Insensitive Disconnected Flag
TC-SNS-07      sensor_error   [PASS]        43.94  Explicit Healthy OK Status Flag
TC-EXEC-01     execution_failure [PASS]         5.05  Missing Executable Detection
--------------------------------------------------------------------------------
Result Status : ALL TESTS PASSED
Test Counts   : Total: 37 | Passed: 37 | Failed: 0 | Errors: 0 | Timeouts: 0
Pass Rate     : 100.0%
Duration      : 2438.61 ms
================================================================================
JSON validation report saved to: .../reports/validation_report.json
```

---

## Deploying to Render (Step-by-Step)

The project includes `Dockerfile` and `render.yaml` for zero-configuration container deployment on Render's Free Web Service tier:

```
Stage 1: GCC 13 Builder --> Compiles sensor_controller C binary for Linux x86_64
Stage 2: Python 3.12 Slim --> Packages server.py, dashboard, framework, and C binary
```

### Option A: Blueprint Auto-Deploy (Recommended)
1. Push your repository to GitHub: `https://github.com/Sargunan-1619/firmware-validation-framework`.
2. Log into [Render Dashboard](https://dashboard.render.com/).
3. Click **"New +"** -> **"Blueprint"**.
4. Connect the `firmware-validation-framework` repository.
5. Render detects `render.yaml` automatically, builds the Docker container, and launches the dashboard.

### Option B: Manual Web Service Setup
1. Log into [Render Dashboard](https://dashboard.render.com/).
2. Click **"New +"** -> **"Web Service"**.
3. Select **"Build and deploy from a Git repository"** and choose `firmware-validation-framework`.
4. Configure service settings:
   - **Environment:** `Docker`
   - **Instance Type:** `Free`
   - **Health Check Path:** `/api/health`
5. Click **"Create Web Service"**.

---

## Scope & Limitations of Host-Based Simulation

- **Host Environment Simulation:** This validation framework executes against a compiled desktop/container binary of the sensor controller. **All input readings, communication timeouts, and disconnection flags are software-injected simulated inputs.**
- **No Physical Hardware:** No physical microcontroller, ADC, or temperature sensor was utilized during this validation. In target hardware deployment, the framework would interface via UART, JTAG/SWD, or CAN bus.
- **Timing Dynamics:** Process invocation over OS subprocess introduces small process-spawn latencies (typically 30–80 ms) that do not reflect microcontroller ISR response times ($< 1\,\mu\text{s}$).

---

## License

MIT License. Designed and maintained for robust embedded firmware verification.
