from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from .services.processor import DataProcessor
from .services.rules_wrapper import RulesEngine
from .core.config import STORAGE_PATH
from .core.db import db
import os
import json
import shutil
import numpy as np
from pathlib import Path
import yaml
app = FastAPI(title="Race Agent API")

# Auth Configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def load_users():
    # Path to users.json relative to the app directory
    path = os.path.join(os.path.dirname(__file__), "..", "users.json")
    with open(path, "r") as f:
        return json.load(f)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    users = load_users()
    if token not in users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token

@app.on_event("startup")
async def startup_event():

    # Ensure database schema is initialized on startup
    try:
        db.init_schema()
        print("Database schema verified/initialized successfully.")
    except Exception as e:
        print(f"Error initializing database schema: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RunChecksRequest(BaseModel):
    downsample_factor: int = 10


processor = DataProcessor(STORAGE_PATH)

# Path to rules_config.yaml (same directory as main.py)
RULES_CONFIG_PATH = Path(__file__).parent / "rules_config.yaml"
RULES_CONFIG_BACKUP_PATH = RULES_CONFIG_PATH.with_suffix(".yaml.bak")


def _read_rules_config():
    """Read and parse rules_config.yaml."""
    with open(RULES_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def _write_rules_config(data: dict):
    """Write data to rules_config.yaml, backing up the current file first."""
    if RULES_CONFIG_PATH.exists():
        shutil.copy2(str(RULES_CONFIG_PATH), str(RULES_CONFIG_BACKUP_PATH))
    with open(RULES_CONFIG_PATH, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

# MoTeC specific columns for correlation analysis to avoid OOM on large files
MOTEC_CORRELATION_COLUMNS = [
    "Engine Speed Reference Engine Speed",
    "Exhaust Lambda Bank 1 Diagnostic",
    "Exhaust Lambda Bank 2 Diagnostic",
    "Fuel Closed Loop Control Bank 1 Diagnostic",
    "Fuel Closed Loop Control Bank 2 Diagnostic",
    "Engine Oil Pressure Sensor Diagnostic",
    "Fuel Pressure",
    "Inlet Manifold Pressure",
    "Throttle Position",
    "Inlet Air Temperature",
    "Coolant Temperature",
    "GPS Speed",
    "ECU Battery Voltage",
    "Lap Distance",
    "GPS Latitude",
    "GPS Longitude"
]

def perform_processing(file_id: int, file_path: str):
    """Helper to calculate and save stats and correlations for a file."""
    extraction = processor.extract_metadata(file_path)
    metadata = extraction['metadata']
    stats = extraction['channel_stats']

    # Only calculate correlations for specific columns if it's a MoTeC file
    if processor.is_motec_file(file_path):
        correlations = processor.calculate_correlations(file_path, columns=MOTEC_CORRELATION_COLUMNS)
    else:
        correlations = processor.calculate_correlations(file_path)


    # Save stats to DB
    db.execute("DELETE FROM channel_stats WHERE file_id = %s", (file_id,))
    stats_list = []
    for channel, vals in stats.items():
        stats_list.append((file_id, channel, vals['unit'], vals['min'], vals['max'], vals['avg'], vals['std']))

    db.execute_many(
        "INSERT INTO channel_stats (file_id, channel_name, unit, min_val, max_val, avg_val, std_dev) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        stats_list
    )

    # Save correlations
    db.execute("DELETE FROM analysis_results WHERE file_id = %s AND analysis_type = 'correlation'", (file_id,))

    # Sanitize correlations to ensure no NaN/Inf values before JSON dumping
    sanitized_corrs = {}
    if correlations:
        for pair, val in correlations.items():
            if np.isfinite(val):
                sanitized_corrs[pair] = float(val)
            else:
                # Skip non-finite values
                continue

    db.execute(
        "INSERT INTO analysis_results (file_id, analysis_type, result_json) VALUES (%s, %s, %s)",
        (file_id, 'correlation', json.dumps(sanitized_corrs))
    )
    return metadata, stats, correlations

@app.get("/rules")
async def get_rules(user: str = Depends(get_current_user)):
    try:
        engine = RulesEngine(processor)
        return engine.get_active_rules()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rules/config")
async def get_rules_config(user: str = Depends(get_current_user)):
    try:
        return _read_rules_config()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="rules_config.yaml not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rules/config/defaults")
async def get_rules_config_defaults(user: str = Depends(get_current_user)):
    try:
        backup_path = RULES_CONFIG_BACKUP_PATH
        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="No defaults backup found")
        with open(backup_path, "r") as f:
            return yaml.safe_load(f)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rules/config")
async def save_rules_config(config_data: dict, user: str = Depends(get_current_user)):
    try:
        _write_rules_config(config_data)
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Welcome to the Race Agent API"}

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    users = load_users()
    password = users.get(form_data.username)
    if not password or form_data.password != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": form_data.username, "token_type": "bearer"}

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    driver_id: Optional[int] = None,
    car_id: Optional[int] = None,
    race_id: Optional[int] = None,
    user: str = Depends(get_current_user)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    content = await file.read()
    file_path = processor.save_file(content, file.filename)

    # Extract metadata for initial DB entry
    extraction = processor.extract_metadata(file_path)
    metadata = extraction.get("metadata", {})

    # Store in DB
    query = "INSERT INTO race_files (filename, file_path, driver_id, car_id, race_id, metadata_json) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id"
    res = db.execute(query, (file.filename, file_path, driver_id, car_id, race_id, json.dumps(metadata)))
    file_id = res[0]['id']

    # Automatically trigger processing to populate summary tab
    perform_processing(file_id, file_path)

    return {"file_id": file_id, "filename": file.filename, "path": file_path, "metadata": metadata}

@app.post("/process/{file_id}")
async def process_file(file_id: int, user: str = Depends(get_current_user)):
    # Get file path from DB
    res = db.execute("SELECT file_path FROM race_files WHERE id = %s", (file_id,))
    if not res:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = res[0]['file_path']

    # Run processing
    metadata, stats, correlations = perform_processing(file_id, file_path)

    return {"status": "processed", "metadata": metadata, "stats": stats, "correlations": correlations}

@app.get("/stats")
async def get_stats(user: str = Depends(get_current_user)):
    try:
        total_files = db.execute("SELECT COUNT(*) as count FROM race_files")[0]['count']
        active_drivers = db.execute("SELECT COUNT(DISTINCT metadata_json ->> 'Driver') as count FROM race_files WHERE metadata_json ->> 'Driver' IS NOT NULL")[0]['count']
        active_cars = db.execute("SELECT COUNT(DISTINCT metadata_json ->> 'Comment') as count FROM race_files WHERE metadata_json ->> 'Comment' IS NOT NULL")[0]['count']
        total_races = db.execute("SELECT COUNT(DISTINCT metadata_json ->> 'Venue') as count FROM race_files WHERE metadata_json ->> 'Venue' IS NOT NULL")[0]['count']

        return {
            "total_files": total_files,
            "active_drivers": active_drivers,
            "active_cars": active_cars,
            "total_races": total_races
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files")
async def list_files(user: str = Depends(get_current_user)):
    return db.execute("SELECT * FROM race_files")

@app.delete("/files/{file_id}")
async def delete_file(file_id: int, user: str = Depends(get_current_user)):
    # 1. Get file path from DB
    res = db.execute("SELECT file_path FROM race_files WHERE id = %s", (file_id,))
    if not res:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = res[0]['file_path']

    # 2. Delete physical file
    if not processor.delete_file(file_path):
        # We continue even if file is missing from disk to ensure DB is cleaned
        print(f"Warning: Physical file {file_path} not found on disk")

    # 3. Delete from DB (Cascade will handle stats and analysis)
    db.execute("DELETE FROM race_files WHERE id = %s", (file_id,))

    return {"status": "deleted", "file_id": file_id}

@app.get("/files/{file_id}/columns")

async def get_file_columns(file_id: int, user: str = Depends(get_current_user)):
    res = db.execute("SELECT file_path FROM race_files WHERE id = %s", (file_id,))
    if not res:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = res[0]['file_path']
    return processor.get_columns(file_path)

@app.get("/files/data")
async def get_file_data(file_id: int, columns: str, downsample_factor: int = 1, user: str = Depends(get_current_user)):
    res = db.execute("SELECT file_path FROM race_files WHERE id = %s", (file_id,))
    if not res:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = res[0]['file_path']
    column_list = columns.split(',')

    try:
        data = processor.get_downsampled_data(file_path, column_list, downsample_factor)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{file_id}/summary")
async def get_file_summary(file_id: int, user: str = Depends(get_current_user)):
    # 1. Metadata
    meta_res = db.execute("SELECT metadata_json FROM race_files WHERE id = %s", (file_id,))
    if not meta_res:
        raise HTTPException(status_code=404, detail="File not found")

    metadata = meta_res[0]['metadata_json']

    # 2. Channel Stats
    stats = db.execute("SELECT channel_name, unit, min_val, max_val, avg_val, std_dev FROM channel_stats WHERE file_id = %s", (file_id,))

    # 3. Correlations
    corr_res = db.execute("SELECT result_json FROM analysis_results WHERE file_id = %s AND analysis_type = 'correlation'", (file_id,))
    correlations = corr_res[0]['result_json'] if corr_res else {}

    return {
        "metadata": metadata,
        "stats": stats,
        "correlations": correlations
    }

@app.post("/files/{file_id}/run-checks")
async def run_checks(file_id: int, body: RunChecksRequest, user: str = Depends(get_current_user)):
    try:
        engine = RulesEngine(processor)
        summary_id = engine.run_checks(file_id, downsample_factor=body.downsample_factor)
        return {"status": "success", "summary_id": summary_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{file_id}/rules")
async def get_file_rules(file_id: int, user: str = Depends(get_current_user)):
    # Get most recent summary
    summary_res = db.execute(
        "SELECT * FROM rule_check_summaries WHERE file_id = %s ORDER BY checked_at DESC LIMIT 1",
        (file_id,)
    )
    if not summary_res:
        raise HTTPException(status_code=404, detail="No diagnostics run found for this file")

    summary = summary_res[0]
    summary_id = summary['id']

    # Get associated violations
    violations = db.execute(
        "SELECT rule_id, severity, description, timestamp, value, context_json FROM rule_violations WHERE summary_id = %s",
        (summary_id,)
    )

    return {
        "summary": summary,
        "violations": violations
    }

@app.get("/reports")
async def get_reports(
    file_id: Optional[int] = None,
    filename: Optional[str] = None,
    status: Optional[str] = None,
    min_date: Optional[str] = None,
    max_date: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    user: str = Depends(get_current_user)
):
    """List all reports with optional filtering and pagination."""
    conditions = []
    params = []

    if file_id:
        conditions.append("r.file_id = %s")
        params.append(file_id)
    if filename:
        conditions.append("f.filename = %s")
        params.append(filename)
    if status:
        conditions.append("r.status = %s")
        params.append(status)
    if min_date:
        conditions.append("r.checked_at >= %s")
        params.append(min_date)
    if max_date:
        conditions.append("r.checked_at <= %s")
        params.append(max_date)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""

    # Get total count for pagination
    count_query = f"""
        SELECT COUNT(*) as total
        FROM rule_check_summaries r
        JOIN race_files f ON r.file_id = f.id
        {where}
    """
    total = db.execute(count_query, params)[0]['total']

    params.extend([limit, offset])

    query = f"""
        SELECT r.id, r.file_id, r.checked_at, r.total_violations, r.status,
               f.filename, f.metadata_json
        FROM rule_check_summaries r
        JOIN race_files f ON r.file_id = f.id
        {where}
        ORDER BY r.checked_at DESC
        LIMIT %s OFFSET %s
    """

    reports = db.execute(query, params)

    # Extract venue/driver from metadata_json for each report
    for report in reports:
        meta = report.get('metadata_json') or {}
        if isinstance(meta, str):
            import json as json_mod
            meta = json_mod.loads(meta)
        venue = meta.get('Venue', '') or meta.get('venue', '') or ''
        report['venue'] = venue.split(',')[0].replace('"', '').strip() if venue else ''
        driver = meta.get('Driver', '') or meta.get('driver', '') or ''
        report['driver'] = driver.split(',')[0].replace('"', '').strip() if driver else ''
        del report['metadata_json']

    return {"reports": reports, "total": total}

@app.get("/reports/{summary_id}")
async def get_report(summary_id: int, user: str = Depends(get_current_user)):
    """Retrieve a specific historical report."""
    # Get summary
    summary_res = db.execute(
        "SELECT r.id, r.file_id, r.checked_at, r.total_violations, r.status, r.summary_json, r.rules_snapshot, f.filename FROM rule_check_summaries r JOIN race_files f ON r.file_id = f.id WHERE r.id = %s",
        (summary_id,)
    )
    if not summary_res:
        raise HTTPException(status_code=404, detail="Report not found")

    summary = summary_res[0]

    # Get venue/driver from race_files metadata
    file_res = db.execute(
        "SELECT metadata_json FROM race_files WHERE id = %s",
        (summary['file_id'],)
    )
    venue = ''
    driver = ''
    if file_res:
        meta = file_res[0].get('metadata_json') or {}
        if isinstance(meta, str):
            import json as json_mod
            meta = json_mod.loads(meta)
        v = meta.get('Venue', '') or meta.get('venue', '') or ''
        venue = v.split(',')[0].replace('"', '').strip() if v else ''
        d = meta.get('Driver', '') or meta.get('driver', '') or ''
        driver = d.split(',')[0].replace('"', '').strip() if d else ''

    summary['venue'] = venue
    summary['driver'] = driver

    # Get associated violations
    violations = db.execute(
        "SELECT rule_id, severity, description, timestamp, value, context_json FROM rule_violations WHERE summary_id = %s",
        (summary_id,)
    )

    return {
        "summary": summary,
        "violations": violations
    }
