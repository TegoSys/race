# Race Agent — Rules Engine

A modular, YAML-configurable rules engine for analyzing MoTeC telemetry CSV files in a FastAPI + React Progressive Web App. Rules are defined as Python plugins, thresholds live in `rules_config.yaml`, and all results persist to PostgreSQL.

## Table of Contents

- [Architecture](#architecture)
- [Setup](#setup)
- [Current Rules](#current-rules)
- [API Endpoints](#api-endpoints)
- [Adding a New Rule](#adding-a-new-rule)
- [Configuration](#configuration)
- [How the Engine Works](#how-the-engine-works)
- [Database Schema](#database-schema)

---

## Architecture

```
backend/app/
├── rules_config.yaml                      # YAML thresholds for all rules
├── services/
│   ├── rules_wrapper.py                   # RulesEngine class — DB persistence layer
│   └── rules_engine/                      # Core engine package
│       ├── __init__.py
│       ├── rules.py                       # Rule ABC, Status enum, Result dataclass, registry
│       ├── checker.py                     # RulesChecker — orchestrator
│       ├── loader.py                      # MoTeC CSV loader + numeric coercion + downsample
│       ├── reporter.py                    # Plain-text report writer (future use)
│       └── rules_impl/                    # Rule implementations (auto-discovered)
│           ├── __init__.py
│           ├── sensor_fault.py
│           ├── rev_limit.py
│           ├── fuel_trim.py
│           ├── lambda_check.py
│           ├── manifold_ratio.py
│           ├── ram_effect.py
│           ├── fuel_consumption.py
│           ├── top_speed.py
│           ├── battery_voltage.py
│           ├── air_temp.py
│           └── fuel_pressure.py
```

The engine follows a **plugin registry pattern**:

1. **`Rule`** — Abstract base class with `name`, `description`, and `check(df, config)` method.
2. **`@register_rule`** — Decorator that adds the class to a global registry at import time.
3. **`load_all_rules()`** — Uses `pkgutil.iter_modules()` to auto-discover every `.py` file in `rules_impl/` and import it. No manual registration needed.
4. **`RulesChecker`** — Orchestrator. Loads all rules, loads the YAML config, and runs every rule against the data.
5. **`RulesEngine`** (wrapper) — Sits between FastAPI and the engine. Handles CSV loading, runs checks, maps results to the DB schema, and enforces the 2000-violation cap.

## Setup

### Database

```bash
docker-compose up -d
```

Spins up PostgreSQL on port **5446** (container port 5432 mapped to 5446). The app connects via `backend/.env` (`DB_PORT=5446`).

### Dependencies

```bash
pip install -r requirements.txt
```

Key dependency added for the rules engine: **`pyyaml>=6.0`** (for `rules_config.yaml` parsing).

### Start Backend

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Current Rules

| # | Rule | YAML Key | Description |
|---|------|----------|-------------|
| 1 | Sensor Fault Detection | `sensor_fault` | Detects sensors stuck at max/min sentinel values for consecutive samples |
| 2 | Rev Limit (TA2 6800 RPM) | `rev_limit` | Engine speed must not exceed 6800 RPM with performance advantage |
| 3 | Fuel Closed Loop Trim | `fuel_trim` | Fuel trim values must stay within firmware PID limits (±20) |
| 4 | Exhaust Lambda (WOT) | `lambda_check` | Lambda banks should be 0.88–0.89 during wide-open throttle |
| 5 | Manifold Pressure Ratio | `manifold_ratio` | Ambient/manifold pressure ratio during WOT should be consistent |
| 6 | RAM Effect (High Speed) | `ram_effect` | Manifold pressure vs GPS speed at high velocity |
| 7 | Fuel Consumption (WOT) | `fuel_consumption` | Exhaust mass flow per lap during WOT should be consistent |
| 8 | Top Speed (Lap Comparison) | `top_speed` | Peak GPS speed per lap should be consistent lap-to-lap |
| 9 | ECU Battery Voltage | `battery_voltage` | Voltage should stay within 13.4–13.8V, critical below 11V |
| 10 | Inlet Air Temperature | `air_temp` | Temperature should not change more than 10°C within 5 seconds |
| 11 | Fuel Pressure vs RPM | `fuel_pressure` | Fuel pressure should stay constant across engine speed range |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/rules` | Returns list of rules with name, description, and YAML threshold values |
| `POST` | `/files/{file_id}/run-checks` | Runs all rules against a file. Body: `{"downsample_factor": 10}` |
| `GET` | `/files/{file_id}/rules` | Returns the most recent diagnostics summary and violations for a file |

### Run Checks Request Body

```json
{
  "downsample_factor": 100
}
```

- **`downsample_factor`** (int, optional, default 10): How aggressively to downsample the 100Hz telemetry. At factor 10, each row represents ~10 samples of original data. Slider in Analysis UI ranges 1–200, default 100.

### Run Checks Response

```json
{
  "status": "success",
  "summary_id": 42
}
```

### Rules Response (from `GET /rules`)

```json
[
  {
    "id": "revlimit",
    "name": "Rev Limit (TA2 6800 RPM)",
    "description": "Engine speed must not exceed 6800 RPM for >0.25s with performance advantage",
    "thresholds": {
      "max_rpm": 6800,
      "max_duration_samples": 3,
      "speed_advantage_mph": 5.5
    }
  }
]
```

## Adding a New Rule

Adding a rule requires **three steps**: a Python module, a YAML config section, and an optional mapping entry.

### Step 1 — Create the Python module

Create `backend/app/services/rules_engine/rules_impl/my_new_rule.py`:

```python
import pandas as pd
from app.services.rules_engine.rules import Rule, Status, Result, register_rule, get_channel


@register_rule
class MyNewRule(Rule):
    @property
    def name(self):
        return "My New Rule"

    @property
    def description(self):
        return "Describes what this rule checks and why it matters"

    @property
    def supports_multi(self):
        return False  # Set True if this rule can compare across multiple files

    def check(self, df: pd.DataFrame, config: dict) -> list[Result]:
        results = []

        # Read thresholds from YAML config
        rc = config.get("my_new_rule", {})
        warn_threshold = rc.get("warn_threshold", 100)
        fail_threshold = rc.get("fail_threshold", 200)

        # Get a channel from the DataFrame (exact or case-insensitive partial match)
        channel = get_channel(df, "Channel Name I Care About")
        if channel is None:
            return [Result(Status.WARN, "Missing required channel")]

        # Find violations
        over_warn = (channel > warn_threshold)
        over_fail = (channel > fail_threshold)

        if over_fail.any():
            count = int(over_fail.sum())
            results.append(Result(
                Status.FAIL,
                f"Channel exceeded fail threshold ({fail_threshold}) in {count} samples",
            ))
        elif over_warn.any():
            count = int(over_warn.sum())
            results.append(Result(
                Status.WARN,
                f"Channel exceeded warn threshold ({warn_threshold}) in {count} samples",
            ))
        else:
            results.append(Result(
                Status.PASS,
                f"Channel within acceptable limits (max {float(channel.max()):.1f})",
            ))

        return results
```

Key points:
- Use `@register_rule` decorator — no other registration needed.
- The class name becomes the rule's internal ID (lowercased: `mynewrule`).
- Use `get_channel(df, "name")` to safely look up columns. It falls back to case-insensitive partial matching.
- Return a `list[Result]` — multiple results per rule are allowed.
- Each `Result` has: `status` (PASS/WARN/FAIL), `message`, optional `details`, and optional `time_range` (tuple of start/end seconds).
- The `df` is preprocessed: all columns coerced to numeric, NaN filled with 0, downsampled.

### Step 2 — Add YAML config

Add a section to `backend/app/rules_config.yaml`:

```yaml
my_new_rule:
  warn_threshold: 100
  fail_threshold: 200
```

### Step 3 — Add config key mapping (optional but recommended)

Add the class-to-YAML-key mapping in `backend/app/services/rules_wrapper.py` inside `_config_key_for_rule()`:

```python
"MyNewRule": "my_new_rule",
```

Without this, thresholds won't display on the Rules page. The fallback is `class_name.lower()`, which works but may not match a snake_case YAML key.

### That's It

The rule is auto-discovered on next engine load. No restart required in development mode (uvicorn `--reload`).

## Configuration

All thresholds live in `backend/app/rules_config.yaml`:

```yaml
rev_limit:
  max_rpm: 6800
  max_duration_samples: 3
  speed_advantage_mph: 5.5

fuel_trim:
  warn_limit: 15
  fail_limit: 20
  sustain_seconds: 15

lambda_check:
  target_low: 0.88
  target_high: 0.89
  warn_low: 0.85
  warn_high: 0.92
  fail_low: 0.80
  fail_high: 0.95

# ... (all 11 sections)
```

Every rule reads its section via `config.get("section_key", {})` with `.get("field", default)` fallbacks. Changing thresholds does not require a code change or server restart.

## How the Engine Works

### Data Pipeline

1. User selects a file and clicks **Check Diagnostics** in the Analysis screen.
2. Frontend sends `POST /files/{file_id}/run-checks` with `{downsample_factor: 100}`.
3. `RulesEngine.run_checks()` loads the CSV via `loader.load_csv()` — handles MoTeC multi-row headers, numeric coercion, and `fillna(0)`.
4. Data is downsampled by the user-configured factor (e.g., every 100th row at 100Hz = one sample per second).
5. `RulesChecker.run_all()` executes every registered rule sequentially.
6. Results are mapped to the DB schema and persisted (capped at 2000 violations).
7. Frontend navigates to Diagnostics View, which fetches results via `GET /files/{file_id}/rules`.

### Result Status Mapping

| Engine Status | DB Severity | Summary Status |
|---|---|---|
| `FAIL` | `"critical"` | Contributes to `FAILED` |
| `WARN` | `"warning"` | Contributes to `WARNING` |
| `PASS` | `"info"` | Skipped — not stored |

**Overall status logic:** 0 violations → `PASSED`, any FAIL → `FAILED`, warnings only → `WARNING`.

### Violation Cap

`MAX_VIOLATIONS = 2000` — if a file produces more than 2000 violations across all rules, processing stops at the cap. This prevents database bloat on files with widespread issues.

## Database Schema

**`rule_check_summaries`**
| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | Summary identifier |
| `file_id` | INT → race_files | File that was checked |
| `checked_at` | TIMESTAMP | When checks ran |
| `total_violations` | INT | Count of non-PASS violations |
| `status` | VARCHAR | `PASSED` / `WARNING` / `FAILED` |
| `summary_json` | JSONB | Per-rule status and violation counts |

**`rule_violations`**
| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | Violation identifier |
| `summary_id` | INT → rule_check_summaries | Parent summary |
| `file_id` | INT → race_files | File that was checked |
| `rule_id` | VARCHAR | Human-readable rule name |
| `severity` | VARCHAR | `critical` / `warning` / `info` |
| `description` | TEXT | What was found |
| `timestamp` | FLOAT | Start time in seconds (if available) |
| `value` | FLOAT | Reserved for future use |
| `context_json` | JSONB | Rule details, time range, etc. |
