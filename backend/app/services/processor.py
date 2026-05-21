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
