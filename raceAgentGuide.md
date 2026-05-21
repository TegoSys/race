# Race Agent Guide

This guide provides a comprehensive overview of the configuration, architecture, and usage of the Auto Racing Agent system.

## 🏎️ Overview
The Auto Racing Agent is a Progressive Web App (PWA) designed for high-fidelity race telemetry analysis. It allows users to upload race data CSVs, extract key performance indicators, detect anomalies, and compare driver performance.

## 🏗️ System Architecture

### Frontend (The Cockpit)
- **Framework**: React 19 + TypeScript + Vite.
- **Styling**: Tailwind v4 with a custom **Apple Liquid Glass** theme (translucency, backdrop-blur, frosted glass).
- **Components**: shadcn/ui for high-quality, accessible UI elements.
- **PWA**: Fully installable on iOS and Android via `manifest.json` and a custom Service Worker for offline reliability.
- **State**: React Query for API synchronization and Zustand/Context for UI state.

### Backend (The Engine)
- **Framework**: FastAPI (Python 3.11+).
- **Data Processing**: Pandas for ETL, NumPy/SciPy for statistical analysis and correlation, and tslearn for time-series optimization.
- **API**: RESTful endpoints for file management, metadata extraction, and analytics processing.

### Persistence (The Garage)
- **Database**: PostgreSQL for structured storage of drivers, cars, races, and extracted analytics.
- **File Storage**: Raw CSV files are stored on the local filesystem.

---

## ⚙️ Configuration & Setup

### 1. Infrastructure
The system uses Docker Compose to manage the database:
- **PostgreSQL**: Runs in a container (`race_agent_db`).
- **Configuration**: Database credentials are managed via `.env` and `docker-compose.yml`.

**To start the DB:**
```bash
docker-compose up -d
```

### 2. Backend Setup
The backend requires a Python virtual environment:
```bash
# Create and activate venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r backend/requirements.txt

# Initialize database tables
python backend/setup_db.py
```

**To run the server:**
```bash
uvicorn backend.app.main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🛠️ Usage Guide

### Data Ingestion Flow
1. **Upload**: Use the "Upload" page in the UI to select a CSV file.
2. **Metadata Extraction**: Upon upload, the system automatically detects if the file is a **Simple CSV** or a **MoTeC Export**.
    - For MoTeC files, it extracts the header (Venue, Driver, Vehicle, etc.) and stores it as JSON.
3. **Processing**: Trigger the "Process" command. The system will:
    - Calculate Min/Max/Avg/Std for all numeric channels.
    - Extract units (e.g., RPM, mph, kPa) from the file.
    - Calculate correlations (e.g., Throttle vs. Manifold Pressure).
    - Store all results in the PostgreSQL database.
4. **Analysis**: View the processed statistics and correlations on the Dashboard.

### Supporting Different File Formats
The `DataProcessor` is designed to be adaptive:
- **MoTeC Format**: Handles 15-row headers, extracting column names from row 15 and units from row 16.
- **Simple Format**: Processes standard CSVs where the header is on the first row.

---

## 📱 Mobile Usage (PWA)
Because this is a PWA, you can install it on your mobile device:
- **iOS**: Open the app in Safari $\rightarrow$ Share $\rightarrow$ "Add to Home Screen".
- **Android**: Open in Chrome $\rightarrow$ "Install App" or "Add to Home Screen".

The app will then launch in a standalone window without the browser address bar, utilizing the full-screen "Liquid Glass" interface.
