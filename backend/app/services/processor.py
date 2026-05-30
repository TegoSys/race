import pandas as pd
import numpy as np
import os
import csv
from typing import Dict, Any, List, Tuple, Optional
from itertools import islice


def _great_circle_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Approximate distance in meters between two GPS coordinates (Haversine)."""
    R = 6_371_000.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2 +
         np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2)
    return R * 2 * np.arcsin(np.sqrt(a))


def _gps_cluster_confirm(candidates: list, df_full: pd.DataFrame,
                         has_gps: bool) -> tuple:
    """Confirm duration-flagged pit-stop candidates by GPS coordinate clustering.

    Real pit stops share a common GPS coordinate (the pit box). Off-track
    incidents stop at random locations.  Candidates with >= 2 neighbours
    within PIT_BOX_RADIUS are confirmed as pit stops.

    Returns (confirmed_list, rejected_list).
    """
    PIT_BOX_RADIUS = 100.0   # metres
    SPEED_THRESHOLD = 15.0   # km/h — below this = car was stationary

    if not has_gps or len(candidates) < 2:
        return list(candidates), []

    stop_points = []
    for ls in candidates:
        region = df_full.loc[ls['start']:ls['end']]
        if 'GPS Speed' not in region.columns:
            continue
        min_speed_idx = region['GPS Speed'].idxmin()
        if region.loc[min_speed_idx, 'GPS Speed'] > SPEED_THRESHOLD:
            continue
        lat = region.loc[min_speed_idx, 'GPS Latitude']
        lon = region.loc[min_speed_idx, 'GPS Longitude']
        if abs(lat) < 1.0 or abs(lon) < 1.0:
            continue
        stop_points.append((ls, float(lat), float(lon)))

    if len(stop_points) < 2:
        return list(candidates), []

    n = len(stop_points)
    neighbor_counts = [0] * n
    for i in range(n):
        for j in range(i + 1, n):
            d = _great_circle_m(stop_points[i][1], stop_points[i][2],
                               stop_points[j][1], stop_points[j][2])
            if d < PIT_BOX_RADIUS:
                neighbor_counts[i] += 1
                neighbor_counts[j] += 1

    confirmed = [stop_points[i][0] for i in range(n) if neighbor_counts[i] >= 2]
    rejected = [stop_points[i][0] for i in range(n) if neighbor_counts[i] < 2]

    # Candidates that never slowed enough to stop → rejected
    for ls in candidates:
        if ls not in confirmed and ls not in rejected:
            rejected.append(ls)

    return confirmed, rejected


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

        Uses transition-based lap detection (Lap State filter + Lap Number changes
        + time gaps), hybrid pit stop detection (Lap State + duration + GPS clustering),
        and IQR-based lap classification (partial / slow / racing).

        Returns a dict with:
          - 'laps': list of 8-tuples (file_id, lap_number, duration, max_speed,
            avg_speed, min_speed, max_rpm, is_pit_stop)
          - 'session': dict of session-level summary stats (from racing laps only)
          - 'histogram': list of {bin_start, bin_end, count} dicts — racing laps only
        Returns {'laps': [], 'session': None, 'histogram': []} for non-MoTeC or
        missing columns.
        """
        if not self.is_motec_file(file_path):
            return {'laps': [], 'session': None, 'histogram': []}

        metadata, columns, units, start_row = self._parse_motec_header(file_path)

        # Require Lap Number and Lap State
        if 'Lap Number' not in columns or 'Lap State' not in columns:
            return {'laps': [], 'session': None, 'histogram': []}

        # Determine speed column
        speed_col = 'GPS Speed'
        if speed_col not in columns:
            speed_col = 'Vehicle Speed' if 'Vehicle Speed' in columns else None
        if speed_col is None:
            return {'laps': [], 'session': None, 'histogram': []}

        # Determine RPM column
        rpm_col = 'Engine Speed Reference Engine Speed'
        if rpm_col not in columns:
            rpm_col = ('Engine Speed Reference Instantaneous'
                       if 'Engine Speed Reference Instantaneous' in columns
                       else None)

        # GPS columns (optional — used for pit-stop confirmation)
        has_gps = ('GPS Latitude' in columns and 'GPS Longitude' in columns)

        # Build usecols
        load_cols = ['Lap State', 'Lap Number', speed_col]
        if rpm_col:
            load_cols.append(rpm_col)
        if has_gps:
            load_cols.extend(['GPS Latitude', 'GPS Longitude'])
        # 'GPS Speed' may differ from speed_col — add it if missing
        if 'GPS Speed' in columns and 'GPS Speed' not in load_cols:
            load_cols.append('GPS Speed')
        load_cols.append(columns[0])  # Time index

        df = pd.read_csv(file_path, skiprows=start_row, names=columns,
                         index_col=0, usecols=load_cols)
        df = df.apply(pd.to_numeric, errors='coerce')
        df = df.fillna(0)

        # Verify required columns made it through usecols
        if 'Lap Number' not in df.columns or 'Lap State' not in df.columns:
            return {'laps': [], 'session': None, 'histogram': []}

        # ---- Transition-based lap detection (within on-track racing data) ----
        racing = df[df['Lap State'] == 3].copy()
        if racing.empty:
            return {'laps': [], 'session': None, 'histogram': []}

        racing['lap_num_prev'] = racing['Lap Number'].shift(1)
        time_diff = racing.index.to_series().diff()
        gap_threshold = 0.05  # 5× sample interval (100 Hz → 0.01 s)
        has_time_gap = time_diff > gap_threshold
        racing['is_lap_start'] = (racing.index == racing.index[0]) | \
                                (racing['Lap Number'] != racing['lap_num_prev']) | \
                                has_time_gap
        racing['sequential_lap_id'] = racing['is_lap_start'].cumsum()

        # ---- Per-lap stats from racing segments ----
        lap_stats = []
        for lap_id, group in racing.groupby('sequential_lap_id'):
            start_time = float(group.index[0])
            end_time = float(group.index[-1])
            duration = end_time - start_time
            max_speed = float(group[speed_col].max())
            avg_speed = float(group[speed_col].mean())
            min_speed = float(group[speed_col].min())
            max_rpm = float(group[rpm_col].max()) if rpm_col else 0.0

            lap_stats.append({
                'lap': int(lap_id),
                'start': start_time,
                'end': end_time,
                'duration': duration,
                'max_speed': max_speed,
                'avg_speed': avg_speed,
                'min_speed': min_speed,
                'max_rpm': max_rpm,
                'category': 'racing',  # default — refined below
            })

        if not lap_stats:
            return {'laps': [], 'session': None, 'histogram': []}

        # ---- Hybrid pit-stop detection ----

        # Step 1: Lap State-based (practice-style — Lap State drops mid-lap)
        for ls in lap_stats:
            lap_region = df.loc[ls['start']:ls['end']]
            ls['is_pit_stop'] = bool(
                (lap_region['Lap State'] <= 1).any())
        ls_pit_stops = [ls for ls in lap_stats if ls['is_pit_stop']]

        # Step 2: Duration-based candidates (race-style — Lap State never drops)
        non_pit_remaining = [ls for ls in lap_stats if not ls['is_pit_stop']]
        if len(non_pit_remaining) >= 2:
            median_dur = float(np.median(
                [ls['duration'] for ls in non_pit_remaining]))
            pit_threshold = median_dur * 2
            dur_candidates = [ls for ls in non_pit_remaining
                             if ls['duration'] > pit_threshold]
            non_pit_remaining = [ls for ls in non_pit_remaining
                                if ls['duration'] <= pit_threshold]
        else:
            median_dur = 0.0
            pit_threshold = 0.0
            dur_candidates = []

        # Step 3: GPS pit-box confirmation for duration-flagged candidates
        gps_confirmed, gps_rejected = _gps_cluster_confirm(
            dur_candidates, df, has_gps)
        all_pit_stops = ls_pit_stops + gps_confirmed
        for ls in all_pit_stops:
            ls['category'] = 'pit_stop'
            ls['is_pit_stop'] = True

        # Merge GPS-rejected candidates back — they're slow, not pit stops
        non_pit_remaining.extend(gps_rejected)

        # ---- IQR-based classification of remaining laps ----
        if len(non_pit_remaining) >= 2:
            remaining_durations = [ls['duration'] for ls in non_pit_remaining]
            q1 = float(np.percentile(remaining_durations, 25))
            q3 = float(np.percentile(remaining_durations, 75))
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            partial_laps = [ls for ls in non_pit_remaining
                           if ls['duration'] < lower_bound]
            slow_laps = [ls for ls in non_pit_remaining
                        if ls['duration'] > upper_bound]
            racing_laps = [ls for ls in non_pit_remaining
                          if lower_bound <= ls['duration'] <= upper_bound]

            for ls in partial_laps:
                ls['category'] = 'partial'
            for ls in slow_laps:
                ls['category'] = 'slow'
        else:
            partial_laps = []
            slow_laps = []
            racing_laps = non_pit_remaining[:]

        # ---- Build lap tuples for DB (same 8-tuple schema) ----
        lap_tuples = []
        for ls in lap_stats:
            lap_tuples.append((
                file_id, ls['lap'], ls['duration'],
                ls['max_speed'], ls['avg_speed'], ls['min_speed'],
                ls['max_rpm'], ls['is_pit_stop']
            ))

        # ---- Session-level stats (racing laps only) ----
        session = {
            'total_laps': len(lap_stats),
            'top_speed': float(df[speed_col].max()),
            'peak_rpm': float(df[rpm_col].max()) if rpm_col else 0.0,
            'total_duration': float(df.index[-1]),
        }

        if racing_laps:
            racing_durations = [ls['duration'] for ls in racing_laps]
            fastest = min(racing_laps, key=lambda x: x['duration'])
            slowest = max(racing_laps, key=lambda x: x['duration'])
            session['fastest_lap_time'] = fastest['duration']
            session['fastest_lap_number'] = fastest['lap']
            session['slowest_lap_time'] = slowest['duration']
            session['slowest_lap_number'] = slowest['lap']
            session['average_lap_time'] = float(np.mean(racing_durations))
            session['standard_deviation'] = (
                float(np.std(racing_durations, ddof=1))
                if len(racing_durations) > 1 else 0.0)
            session['racing_lap_count'] = len(racing_laps)
        else:
            session['fastest_lap_time'] = 0.0
            session['fastest_lap_number'] = 0
            session['slowest_lap_time'] = 0.0
            session['slowest_lap_number'] = 0
            session['average_lap_time'] = 0.0
            session['standard_deviation'] = 0.0
            session['racing_lap_count'] = 0

        session['pit_stop_count'] = len(all_pit_stops)
        session['partial_lap_count'] = len(partial_laps)
        session['slow_lap_count'] = len(slow_laps)

        # ---- Histogram (racing laps only, 20 bins) ----
        if racing_laps:
            hist_durations = [ls['duration'] for ls in racing_laps]
        else:
            hist_durations = [ls['duration'] for ls in lap_stats]
        hist, bin_edges = np.histogram(hist_durations, bins=20)
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
