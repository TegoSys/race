# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (FastAPI)
- **Virtual Environment**: `backend/raceAgeEnv/` (NOT `venv/`). Activate with `.\raceAgeEnv\Scripts\activate` (Windows) or `source raceAgeEnv/bin/activate` (Bash).
- Install: `pip install -r requirements.txt`
- Run: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload`
- Tests: `pytest`
- **Key dependency**: `pyyaml>=6.0` for the rules engine config

### Frontend (React + Vite)
- Install: `cd frontend && npm install`
- Run: `cd frontend && npm run dev`
- Build: `npm run build`
- Lint: `npm run lint`

### Database (Docker)
- Start: `docker-compose up -d` (PostgreSQL on port **5446**, volume `postgres_data_newRules`)
- Connect via `backend/.env` with `DB_PORT=5446`

## Architecture Overview

The system is a Progressive Web App (PWA) for race analytics, utilizing a decoupled Frontend/Backend architecture.

### Frontend
- **Stack**: React 19, TypeScript, Vite, Tailwind v4 (via PostCSS plugin), shadcn/ui.
- **Theme**: "Apple Liquid Glass" — translucent backgrounds, `backdrop-blur`, subtle borders, frosted-glass aesthetic.
- **State**: React Query for server-state; Auth Context for login; **state-based routing** (no React Router — uses `useState` in `App.tsx` to conditionally render pages).
- **Navigation refresh pattern**: Components are kept mounted across page switches. To force a refetch on navigation, `App.tsx` uses a `navCounter` state that increments on every page change, passed as `key={navCounter}` to each page component to trigger remount.
- **Diagnostics caching**: React Query caches diagnostics results. After running "Check Diagnostics", the `Analysis.tsx` invalidates the query cache via `queryClient.invalidateQueries({ queryKey: ['diagnostics', fileId] })` before navigating. `DiagnosticsView` shows a "Refreshing..." indicator using `isFetching`.

### Backend
- **Stack**: FastAPI, Python 3.11+, PostgreSQL (psycopg2).
- **Data Pipeline**: Raw CSVs stored on filesystem in `backend/data/raw_files/`. Pandas for ETL/stats, SciPy/NumPy for correlation, tslearn for time-series.
- **Persistence**: PostgreSQL stores race metadata, extracted analytics, and rule check summaries.
- **Auth**: OAuth2 Bearer token via `users.json` (username = token value).

---

## Configurable Rules Engine

### Overview

The rules engine is a modular, YAML-configurable system with 11 built-in rules for analyzing MoTeC telemetry CSVs. It follows a **plugin registry pattern** with auto-discovery.

### Directory Structure

```
backend/app/
├── rules_config.yaml              # YAML thresholds — editable via Rules page
├── rules_config.yaml.bak          # Auto-created backup for "Restore Defaults"
├── services/
│   ├── rules_wrapper.py           # RulesEngine class — bridges FastAPI + engine + DB
│   └── rules_engine/
│       ├── rules.py               # Rule ABC, Status enum, Result dataclass, registry
│       ├── checker.py             # RulesChecker — orchestrates rule execution
│       ├── loader.py             # MoTeC CSV loader, numeric coercion, downsample
│       ├── reporter.py            # Plain-text report writer
│       └── rules_impl/            # Rule modules — auto-discovered by pkgutil
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

### Key Components

| Component | Path | Purpose |
|-----------|------|---------|
| `Rule` ABC | `rules.py` | Abstract base class with `name`, `description`, `check(df, config)` |
| `@register_rule` | `rules.py` | Decorator that registers rule classes in a global registry at import time |
| `load_all_rules()` | `rules.py` | Uses `pkgutil.iter_modules()` to auto-discover and import all rule modules |
| `RulesChecker` | `checker.py` | Orchestrator — loads rules, loads YAML config, runs every rule against data |
| `RulesEngine` | `rules_wrapper.py` | Bridges FastAPI ↔ engine ↔ DB. Handles CSV loading, runs checks, maps to DB schema, enforces 2000-violation cap |
| `Result` dataclass | `rules.py` | Per-check result: `status`, `message`, `details`, `time_range`, `value`, `threshold` |

### How It Works

1. `RulesChecker._initialize()` calls `load_all_rules()` → auto-discovers all rule modules
2. Each rule's `check(df, config)` method receives a preprocessed DataFrame and the full YAML config
3. Rules return `list[Result]` — multiple results per rule are allowed
4. `RulesEngine.run_checks()` collects violations, maps status to severity (`FAIL` → `"critical"`, `WARN` → `"warning"`, `PASS` → `"info"`)
5. Results persist to `rule_check_summaries` and `rule_violations` tables (max 2000 violations)
6. Overall status: 0 violations → `PASSED`, any FAIL → `FAILED`, warnings only → `WARNING`

### Adding a New Rule

Three steps — one Python module, one YAML section, one mapping entry:

**1. Create `backend/app/services/rules_engine/rules_impl/my_rule.py`:**

```python
import pandas as pd
from app.services.rules_engine.rules import Rule, Status, Result, register_rule, get_channel

@register_rule
class MyRule(Rule):
    @property
    def name(self):
        return "My Rule"

    @property
    def description(self):
        return "What this rule checks and why"

    def check(self, df: pd.DataFrame, config: dict) -> list[Result]:
        rc = config.get("my_rule", {})
        limit = rc.get("limit", 100)
        channel = get_channel(df, "Channel Name")
        if channel is None:
            return [Result(Status.WARN, "Missing channel")]

        if (channel > limit).any():
            peak = float(channel.max())
            return [Result(Status.FAIL, f"Exceeded {limit}", value=peak, threshold=limit)]
        return [Result(Status.PASS, f"Within limits")]
```

**2. Add YAML section to `backend/app/rules_config.yaml`:**
```yaml
my_rule:
  limit: 100
```

**3. Add mapping in `rules_wrapper.py` → `_config_key_for_rule()`:**
```python
"MyRule": "my_rule",
```

### Rules Page Editing (Frontend ↔ Backend)

The Rules page reads thresholds from `rules_config.yaml`, allows inline editing, and persists changes.

**Backend endpoints** (`main.py`):
- `GET /rules` — returns rule metadata with threshold values from YAML
- `GET /rules/config` — returns raw YAML config as JSON
- `GET /rules/config/defaults` — returns `.bak` backup for restore functionality
- `POST /rules/config` — writes new YAML config, creates `.bak` backup automatically

**Frontend** (`pages/Rules.tsx`):
- Edit/Save toggle for all rules at once
- Basic numeric validation on threshold inputs
- Restore Defaults button reads from `.bak` backup
- Uses `rule.config_key` (snake_case) to map to YAML sections

---

## Coding Standards
- **TypeScript**: Strict mode enabled. Functional components and hooks.
- **Python**: PEP 8. Type hints for all function signatures.
- **Styling**: Tailwind v4 utilities. Avoid custom CSS unless needed for Liquid Glass effects.
- **API**: RESTful endpoints following FastAPI best practices.
- **Virtual Environment**: Always use `raceAgeEnv/`, not `venv/`.

## Lessons Learned

### Frontend
- **State-based routing keeps components mounted**: Using `useState` + conditional rendering means `useEffect(..., [])` only fires on first mount, not on navigation back. Fix: increment a `navCounter` state and pass as `key` to force remounts.
- **React Query caching**: Mutations that insert new data don't automatically invalidate query caches. Use `queryClient.invalidateQueries()` after mutations that change fetched state.
- **Backend port mismatches**: Frontend's `config.ts` `API_BASE_URL` must match the backend port. Default is `http://127.0.0.1:8001`.
- **Windows port sockets**: Orphaned TCP listeners on Windows can prevent port reuse. Switch to a different port or use `--reload` to pick up code changes.
- **React Rules of Hooks — all hooks before early returns**: In components with `isLoading`/`error` guards like `if (isLoading) return <Loading />`, placing `useMemo` or `useCallback` after these guards causes a hook order mismatch. When `isLoading` flips from `true` to `false`, React sees hooks in different order and destroys the component — producing a silent blank screen with no console errors in production builds. Always declare all hooks before any conditional returns.
- **Service worker caching in dev mode**: The SW in `frontend/public/sw.js` caches all fetch responses including API calls. If the SW cache contains stale/broken data, even a dev server rebuild won't clear it. Bump the cache name version in `sw.js` AND add `?v=N` query param to the SW registration URL in `main.tsx` to force browser reload of the worker itself.

### Backend
- **Module vs package name conflicts**: A file `rules_engine.py` conflicts with a directory `rules_engine/`. Use a different wrapper name (e.g., `rules_wrapper.py`).
- **Config path resolution**: `rules_config.yaml` lives three levels up from `services/rules_engine/`. Use `Path(__file__).resolve().parent.parent.parent`.
- **YAML config key mapping**: Rule class names use camelCase but YAML uses snake_case. Maintain an explicit mapping in `_config_key_for_rule()` in the wrapper.
- **NaN/Inf in JSON**: NumPy floats can produce non-JSON-serializable NaN/Inf values. Sanitize with `_sanitize_for_json()` before database insertion.
- **Result value field**: The `Result` dataclass initially lacked `value`/`threshold` fields, causing the diagnostics value column to always show "—". Always include numeric fields that the frontend will display.

### Database
- **Volume naming**: When migrating databases, use unique volume names (e.g., `postgres_data_newRules`) to avoid conflicts with existing Docker volumes.
- **Port mapping**: Use non-standard host ports (5446 instead of 5432) to avoid conflicts with local PostgreSQL installations.
