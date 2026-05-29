import pandas as pd
import numpy as np
import os
import csv
from typing import Dict, Any, List, Tuple, Optional
from itertools import islice
class DataProcessor:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path

    def save_file(self, file_content: bytes, filename: str) -> str:
        file_path = os.path.join(self.storage_path, filename)
        with open(file_path, "wb") as f:
            f.write(file_content)
        return file_path

    def delete_file(self, file_path: str) -> bool:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False


    def _parse_motec_header(self, file_path: str) -> Tuple[Dict[str, Any], List[str], List[str], int]:
        """
        Parses MoTeC CSV header and returns:
        (metadata, column_names, units, data_start_row)
        """
        print(f"DEBUG: [Processor] Parsing MoTeC header for: {file_path}")
        metadata = {}
        #with open(file_path, 'r', encoding='utf-8') as f:
            #lines = f.readlines()
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = list(islice(f, 25))
            print(f"DEBUG: [Processor] Read first 25 lines for header extraction")
            # Extract metadata from first 12 lines
            for i in range(min(12, len(lines))):
                line = lines[i].strip()
                if not line: continue
                parts = line.split(',', 1)
                if len(parts) == 2:
                    key = parts[0].strip('"')
                    val = parts[1].strip().strip('"')
                    metadata[key] = val

            # Row 15: Column names (index 14)
            columns = []
            if len(lines) > 14:
                columns = [c.strip('"') for c in lines[14].split(',')]

            # Row 16: Units (index 15)
            units = []
            if len(lines) > 15:
                units = [u.strip('"') for u in lines[15].split(',')]

            print(f"DEBUG: [Processor] Header extraction complete. Found {len(columns)} columns.")
            # Data starts at row 19 (index 18)
            return metadata, columns, units, 18

    def is_motec_file(self, file_path: str) -> bool:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            return '"Format","MoTeC CSV File"' in first_line

    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        if self.is_motec_file(file_path):
            metadata, columns, units, start_row = self._parse_motec_header(file_path)
            # Read data starting from start_row
            df = pd.read_csv(file_path, skiprows=start_row, names=columns, low_memory=False,index_col=0)
            df = df.apply(pd.to_numeric,errors='coerce')
            df = df.fillna(0)
            # We can also extract some data-based metadata here
        else:
            # Simple CSV: assume header is on row 0
            df = pd.read_csv(file_path, index_col=0)
            metadata = {"format": "simple_csv"}
            columns = list(df.columns)
            units = ["unknown"] * len(columns)

        stats = {}
        for i, col in enumerate(df.columns):
            unit = units[i] if i < len(units) else "unknown"
            if pd.api.types.is_numeric_dtype(df[col]):
                stats[col] = {
                    "unit": unit,
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "avg": float(df[col].mean()),
                    "std": float(df[col].std())
                }

        return {
            "filename": os.path.basename(file_path),
            "columns": columns,
            "row_count": len(df),
            "metadata": metadata,
            "channel_stats": stats
        }

    def get_columns(self, file_path: str) -> List[str]:
        if self.is_motec_file(file_path):
            _, columns, _, _ = self._parse_motec_header(file_path)
            return columns
        else:
            df = pd.read_csv(file_path, nrows=0)
            return df.columns.tolist()

    def get_downsampled_data(self, file_path: str, columns: List[str], downsample_factor: int) -> List[Dict[str, Any]]:
        if self.is_motec_file(file_path):
            _, cols_all, _, start_row = self._parse_motec_header(file_path)
            indices = [cols_all.index(c) for c in columns if c in cols_all]
            df = pd.read_csv(file_path, skiprows=start_row, low_memory=False,names=cols_all, usecols=indices)
            df = df.apply(pd.to_numeric,errors='coerce')
            df = df.fillna(0)
        else:
            df = pd.read_csv(file_path, usecols=columns)

        # Ensure all columns are numeric to avoid JSON compliance issues with NaNs/Infs
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.iloc[::downsample_factor]

        # Fill NaNs and Infs with 0.0 to ensure JSON compliance
        df = df.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        # Add index as a column to be included in the records
        df = df.reset_index().rename(columns={'index': 'index'})

        return df.to_dict(orient='records')

    def calculate_correlations(self, file_path: str, columns: Optional[List[str]] = None) -> Dict[str, float]:
        if self.is_motec_file(file_path):
            _, cols_all, _, start_row = self._parse_motec_header(file_path)
            if columns:
                valid_cols = [c for c in columns if c in cols_all]
                df = pd.read_csv(file_path, skiprows=start_row, names=cols_all, index_col=0, usecols=valid_cols + [cols_all[0]])
            else:
                df = pd.read_csv(file_path, skiprows=start_row, names=cols_all, index_col=0)
        else:
            if columns:
                df = pd.read_csv(file_path, index_col=0, usecols=columns + [0])
            else:
                df = pd.read_csv(file_path, index_col=0)

        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.empty:
            return {}

        corr_matrix = numeric_df.corr()

        # Find the strongest correlations (excluding self-correlation)
        corrs = []
        cols = corr_matrix.columns
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                val = corr_matrix.iloc[i, j]
                # Use np.isfinite to exclude NaN and Inf
                if np.isfinite(val):
                    corrs.append({
                        "pair": f"{cols[i]} vs {cols[j]}",
                        "value": float(val)
                    })
                else:
                    # Explicitly ignore non-finite values
                    continue

        # Sort by absolute value and take top 3
        corrs.sort(key=lambda x: abs(x["value"]), reverse=True)

        # Final sanitization to ensure no NaN/Inf slips into the final dict
        top_corrs = {}
        for c in corrs[:3]:
            val = c["value"]
            if np.isfinite(val):
                top_corrs[c["pair"]] = val
            else:
                # This should be unreachable due to the previous check, but just in case
                continue

        return top_corrs

    def extract_lap_data(self, file_path: str, file_id: int) -> Dict[str, Any]:
        """Extract per-lap statistics and session characterization from a MoTeC CSV.

        Returns a dict with:
          - 'laps': list of 8-tuples (file_id, lap_number, duration, max_speed, avg_speed, min_speed, max_rpm, is_pit_stop)
          - 'session': dict of session-level summary stats
          - 'histogram': list of {bin_start, bin_end, count} dicts (20 bins)
        Returns {'laps': [], 'session': None, 'histogram': []} for non-MoTeC or missing columns.
        """
        if not self.is_motec_file(file_path):
            return {'laps': [], 'session': None, 'histogram': []}

        metadata, columns, units, start_row = self._parse_motec_header(file_path)

        if 'Lap Number' not in columns:
            return {'laps': [], 'session': None, 'histogram': []}

        # Determine speed column
        speed_col = 'GPS Speed'
        if speed_col not in columns:
            speed_col = 'Vehicle Speed' if 'Vehicle Speed' in columns else None

        # Determine RPM column
        rpm_col = 'Engine Speed Reference Engine Speed'
        if rpm_col not in columns:
            rpm_col = 'Engine Speed Reference Instantaneous' if 'Engine Speed Reference Instantaneous' in columns else None

        if speed_col is None:
            return {'laps': [], 'session': None, 'histogram': []}

        lap_columns = ['Lap Number', speed_col]
        if rpm_col:
            lap_columns.append(rpm_col)

        df = pd.read_csv(file_path, skiprows=start_row, names=columns, index_col=0, usecols=lap_columns + [columns[0]])
        df = df.apply(pd.to_numeric, errors='coerce')
        df = df.fillna(0)

        max_lap = int(df['Lap Number'].max())
        lap_stats = []

        for lap_num in range(1, max_lap + 1):
            lap_mask = (df['Lap Number'] == lap_num)
            lap_data = df[lap_mask]
            if len(lap_data) == 0:
                continue

            start_time = float(lap_data.index[0])
            end_time = float(lap_data.index[-1])
            duration = end_time - start_time
            max_speed = float(lap_data[speed_col].max())
            avg_speed = float(lap_data[speed_col].mean())
            min_speed = float(lap_data[speed_col].min())

            max_rpm = float(lap_data[rpm_col].max()) if rpm_col is not None else 0.0

            lap_stats.append({
                'lap': lap_num,
                'duration': duration,
                'max_speed': max_speed,
                'avg_speed': avg_speed,
                'min_speed': min_speed,
                'max_rpm': max_rpm
            })

        if not lap_stats:
            return {'laps': [], 'session': None, 'histogram': []}

        # Pit-stop detection: flag laps > 2x median duration
        lap_durations = [ls['duration'] for ls in lap_stats]
        median_duration = np.median(lap_durations)
        pit_threshold = median_duration * 2

        # Build lap tuples
        lap_tuples = []
        for ls in lap_stats:
            is_pit = bool(ls['duration'] > pit_threshold)
            lap_tuples.append((
                file_id, ls['lap'], ls['duration'],
                ls['max_speed'], ls['avg_speed'], ls['min_speed'],
                ls['max_rpm'], is_pit
            ))

        # Filter racing laps (non-pit-stop)
        racing_laps = [ls for ls in lap_stats if ls['duration'] <= pit_threshold]
        pit_stops = [ls for ls in lap_stats if ls['duration'] > pit_threshold]

        # Session-level stats
        session = {
            'total_laps': len(lap_stats),
            'top_speed': float(df[speed_col].max()),
            'peak_rpm': float(df[rpm_col].max()) if rpm_col is not None else 0.0,
            'total_duration': float(df.index[-1])
        }

        if racing_laps:
            racing_durations = [ls['duration'] for ls in racing_laps]
            session['fastest_lap_time'] = min(racing_durations)
            session['fastest_lap_number'] = min(racing_laps, key=lambda x: x['duration'])['lap']
            session['slowest_lap_time'] = max(racing_durations)
            session['slowest_lap_number'] = max(racing_laps, key=lambda x: x['duration'])['lap']
            session['average_lap_time'] = float(np.mean(racing_durations))
            session['standard_deviation'] = float(np.std(racing_durations, ddof=1))
            session['racing_lap_count'] = len(racing_laps)
        else:
            session['fastest_lap_time'] = 0.0
            session['fastest_lap_number'] = 0
            session['slowest_lap_time'] = 0.0
            session['slowest_lap_number'] = 0
            session['average_lap_time'] = 0.0
            session['standard_deviation'] = 0.0
            session['racing_lap_count'] = 0

        session['pit_stop_count'] = len(pit_stops)

        # Histogram of all lap durations (20 bins)
        hist, bin_edges = np.histogram(lap_durations, bins=20)
        histogram = []
        for i in range(len(hist)):
            histogram.append({
                'bin_start': round(float(bin_edges[i]), 1),
                'bin_end': round(float(bin_edges[i + 1]), 1),
                'count': int(hist[i])
            })

        return {
            'laps': lap_tuples,
            'session': session,
            'histogram': histogram
        }
