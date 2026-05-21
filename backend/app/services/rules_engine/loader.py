"""Load and preprocess MoTeC CSV telemetry files."""
import csv
import io

import pandas as pd


def load_csv(filepath: str, downsample: int = 10) -> tuple[pd.DataFrame, dict]:
    """Load a MoTeC CSV file, preprocess, and downsample.

    MoTeC CSV format:
    - Rows 1-12: metadata key/value pairs
    - Rows 13-14: blank
    - Row 15: column names
    - Row 16: units
    - Rows 17-18: blank
    - Row 19+: data rows (100Hz samples)

    Returns (DataFrame, metadata_dict).
    """
    metadata = _read_metadata(filepath)
    df, units_dict = _read_data(filepath)
    df = _preprocess(df)
    df = _downsample(df, downsample)
    metadata.update(units_dict)
    return df, metadata


def _read_metadata(filepath: str) -> dict:
    """Read MoTeC CSV metadata lines as key/value pairs."""
    metadata = {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[:14]:
            reader = csv.reader(io.StringIO(line))
            for row in reader:
                cells = [c.strip().strip('"') for c in row if c.strip()]
                for i in range(0, len(cells) - 1, 2):
                    if cells[i] and cells[i + 1]:
                        metadata[cells[i]] = cells[i + 1]
    except Exception:
        pass
    return metadata


def _read_data(filepath: str) -> tuple[pd.DataFrame, dict]:
    """Read the data portion of a MoTeC CSV, skipping header metadata.

    Returns (DataFrame, units_dict).
    """
    with open(filepath, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()

    if "MoTeC CSV File" in first_line:
        # Read column names from line 15 (0-indexed: 14)
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        reader = csv.reader(io.StringIO(lines[14]))
        columns = next(reader)

        # Read units from line 16 (0-indexed: 15)
        reader = csv.reader(io.StringIO(lines[15]))
        units = next(reader)
        units_dict = dict(zip(columns, units))

        # Read data from line 19+ (0-indexed: 18), using extracted columns
        data_text = "".join(lines[18:])
        df = pd.read_csv(io.StringIO(data_text), header=None, names=columns,
                         low_memory=False)
        # Drop columns that are entirely empty
        df = df.loc[:, (df != "").any(axis=0)]
    else:
        # Assume simple CSV with header row
        df = pd.read_csv(filepath, low_memory=False)
        units_dict = {}

    return df, units_dict


def _preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce all columns to numeric, fill NaN with 0."""
    df = df.apply(lambda col: pd.to_numeric(col, errors="coerce"))
    df = df.fillna(0)
    return df


def _downsample(df: pd.DataFrame, factor: int) -> pd.DataFrame:
    """Downsample by taking every nth row."""
    if factor <= 1:
        return df
    return df.iloc[::factor].reset_index(drop=True)
