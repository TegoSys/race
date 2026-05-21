# Race Agent Data Model

The Race Agent system employs a hybrid data architecture designed to handle massive telemetry datasets while maintaining fast query performance for analytics.

## 🏗 Architecture Overview

The system splits data between a **relational database (PostgreSQL)** for structured metadata and analytics, and the **local filesystem** for raw telemetry data.

### 1. Relational Layer (PostgreSQL + SQLAlchemy)
The backend uses **SQLAlchemy ORM** to manage the database. This layer stores aggregated insights rather than raw data points to avoid database bloat.

#### Key Entities:
- **RaceFile**: Tracks uploaded files.
  - *Purpose*: Maps a unique `file_id` to the physical path on disk and basic file metadata.
- **ChannelStat**: Stores pre-computed statistics for every channel in a file.
  - *Fields*: `channel_name`, `min_val`, `max_val`, `avg_val`, `std_dev`.
  - *Purpose*: Allows the "File Summary" view to load instantly without re-scanning the CSV.
- **AnalysisResult**: Stores calculated relationships between channels.
  - *Fields*: `channel_pair` (e.g., "Throttle vs RPM"), `correlation_coefficient`.
  - *Purpose*: Powers the Correlation Insights visualization.

### 2. Raw Data Layer (Filesystem + Pandas)
Raw telemetry data is stored as CSV files in `backend/data/raw_files/`. 

- **Storage**: Files are kept in their original format (Standard CSV or MoTeC CSV).
- **Access**: The system uses **Pandas** for "Just-In-Time" (JIT) data retrieval. Instead of loading entire files into memory, it uses `usecols` to load only the channels requested by the user.
- **Performance**: To ensure the frontend remains responsive, the backend implements **downsampling** (via slicing: `df.iloc[::factor]`) before sending data over the API.

### 3. Validation Layer (Pydantic)
**Pydantic** is used as the bridge between the SQLAlchemy models and the FastAPI endpoints.
- **Schemas**: Define the strict structure of API requests and responses.
- **Serialization**: Converts SQLAlchemy ORM objects into JSON-compatible formats for the React frontend.

## 🔄 Data Lifecycle

1. **Ingestion**: 
   - File uploaded $\rightarrow$ Saved to disk $\rightarrow$ Entry created in `RaceFile` table.
2. **Processing (ETL)**: 
   - `DataProcessor` reads CSV $\rightarrow$ Calculates stats/correlations $\rightarrow$ Persists results to `ChannelStat` and `AnalysisResult` tables.
3. **Consumption**:
   - **Summary Request**: API fetches pre-computed stats from PostgreSQL $\rightarrow$ Returns JSON.
   - **Chart Request**: API reads specific columns from CSV on disk $\rightarrow$ Downsamples $\rightarrow$ Returns JSON.
