# Race Agent Software Architecture

Race Agent is a Progressive Web App (PWA) designed for advanced race telemetry analytics. It utilizes a decoupled architecture with a FastAPI backend for heavy data processing and a React frontend for data visualization and management.

## 1. High-Level Architecture

The system follows a client-server model:
- **Frontend**: A React-based single-page application (SPA) that handles user interaction, data visualization, and state management.
- **Backend**: A Python-based REST API that manages file uploads, performs ETL (Extract, Transform, Load) operations on telemetry CSVs, runs a rules engine for anomaly detection, and persists results in a PostgreSQL database.

---

## 2. Backend Architecture

### Components
- **API Server (FastAPI)**: Provides REST endpoints for authentication, file management, and triggering analytics.
- **Data Processor (`DataProcessor`)**: Handles the ingestion of MoTeC and generic CSV files. It performs downsampling and column mapping to normalize different telemetry formats.
- **Rules Engine (`RulesEngine`)**: A domain-specific logic layer that applies a series of technical checks (e.g., RPM limits, AFR windows, electrical stability) to identify anomalies in race data.
- **Database Layer**: A PostgreSQL instance used for persistent storage of metadata and analysis results.

### Data Pipeline
1. **Ingestion**: CSV files are uploaded via the API and stored on the local filesystem.
2. **ETL**: The `DataProcessor` parses the files, maps columns to standard identifiers, and calculates basic channel statistics.
3. **Analysis**: 
    - Correlation analysis is performed to identify relationships between telemetry channels.
    - The `RulesEngine` runs a suite of checks to identify violations.
4. **Persistence**: All metadata, stats, correlations, and rule violations are stored in PostgreSQL.

---

## 3. Frontend Architecture

### Tech Stack
- **Framework**: React 19 with TypeScript.
- **Build Tool**: Vite.
- **Styling**: Tailwind CSS v4.
- **UI Components**: shadcn/ui.
- **State Management**: 
    - `AuthContext`: Manages user authentication state.
    - Local `useState` for page routing and file selection.

### Design Language: "Apple Liquid Glass"
The UI is characterized by a frosted-glass aesthetic:
- Translucent backgrounds (`bg-white/5`, `bg-slate-900`).
- Backdrop blur and subtle borders (`border-white/10`).
- Gradient accents (Blue to Purple) for primary headings and buttons.

---

## 4. Database Schema

The system uses a PostgreSQL database with the following key tables:
- `drivers`, `cars`, `races`: Metadata for race entities.
- `race_files`: Tracks uploaded CSVs and their physical paths.
- `channel_stats`: Stores min/max/avg/std for every telemetry channel per file.
- `analysis_results`: Stores JSON-encoded correlation data.
- `rule_check_summaries`: High-level results of a rules engine run.
- `rule_violations`: Detailed entries for every individual rule breach.

---

## 5. Configuration & Setup

### Backend Setup
**Required Configuration**:
- Database credentials are managed in `backend/core/config.py`.

**Getting Started**:
1. Navigate to the backend directory.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows: .\venv\Scripts\activate
   # Unix: source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Initialize the database:
   ```bash
   python backend/setup_db.py
   ```
5. Start the server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup
**Required Configuration**:
- The frontend connects to the backend API via `frontend/src/lib/api.ts`.

**Getting Started**:
1. Navigate to the frontend directory.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

---

## 6. Main API Endpoints
- `POST /login`: Authenticates users.
- `POST /upload`: Uploads telemetry CSVs and triggers initial processing.
- `GET /stats`: Returns global system statistics.
- `GET /files`: Lists all uploaded race files.
- `GET /files/{id}/summary`: Retrieves metadata, stats, and correlations for a specific file.
- `POST /files/{id}/run-checks`: Triggers the Rules Engine for a specific file.
- `GET /rules`: Returns the current list of active rules and their descriptions.
