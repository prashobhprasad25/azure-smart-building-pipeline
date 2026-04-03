"""
transform.py
-------------
Transforms validated raw sensor records into a flat, analysis-ready
DataFrame. Computes per-zone aggregates and flags threshold breaches.

In an Azure pipeline, this logic runs inside an Azure Function or
Azure Databricks job triggered by new blob arrivals.
"""

import json
import os
import glob
import pandas as pd
from datetime import datetime


# Operational thresholds (based on CIBSE Guidelines for commercial buildings)
THRESHOLDS = {
    "temperature_c": {"min": 18.0, "max": 26.0},
    "humidity_pct": {"min": 30.0, "max": 70.0},
    "co2_ppm": {"min": 0, "max": 1000},
    "occupancy_count": {"min": 0, "max": 50},
    "energy_kwh": {"min": 0, "max": 30.0},
}


def flatten_records(records: list) -> pd.DataFrame:
    """
    Flatten nested sensor JSON records into a tabular DataFrame.

    Args:
        records: List of validated sensor reading dicts.

    Returns:
        pd.DataFrame: Flat table with one row per sensor reading.
    """
    rows = []
    for rec in records:
        row = {
            "timestamp": pd.to_datetime(rec["timestamp"]),
            "zone": rec["zone"],
            "sensor_id": rec["sensor_id"],
        }
        for metric, payload in rec["readings"].items():
            row[metric] = payload["value"]
        rows.append(row)

    df = pd.DataFrame(rows)
    df.sort_values("timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def flag_threshold_breaches(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add boolean breach columns for each metric exceeding safe thresholds.

    Args:
        df: Flat sensor DataFrame.

    Returns:
        pd.DataFrame: DataFrame with added breach flag columns.
    """
    for metric, limits in THRESHOLDS.items():
        if metric in df.columns:
            df[f"{metric}_breach"] = (df[metric] < limits["min"]) | (df[metric] > limits["max"])

    breach_cols = [c for c in df.columns if c.endswith("_breach")]
    df["any_breach"] = df[breach_cols].any(axis=1)
    return df


def compute_zone_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-zone aggregated statistics.

    Args:
        df: Flat sensor DataFrame (with breach flags).

    Returns:
        pd.DataFrame: Zone-level summary table.
    """
    metrics = list(THRESHOLDS.keys())
    agg_dict = {m: ["mean", "min", "max", "std"] for m in metrics if m in df.columns}
    agg_dict["any_breach"] = "sum"

    summary = df.groupby("zone").agg(agg_dict)
    summary.columns = ["_".join(c).strip() for c in summary.columns]
    summary.rename(columns={"any_breach_sum": "total_breaches"}, inplace=True)
    summary.reset_index(inplace=True)
    return summary


def transform_and_save(ingested_dir: str = "data/ingested", output_dir: str = "data/transformed"):
    """
    Load ingested JSON files, transform, and save as CSV.

    Args:
        ingested_dir: Directory with ingested JSON files.
        output_dir: Directory for transformed CSV output.
    """
    os.makedirs(output_dir, exist_ok=True)
    files = glob.glob(os.path.join(ingested_dir, "*.json"))

    if not files:
        print(f"[Transform] No ingested files found in {ingested_dir}.")
        return None, None

    all_records = []
    for f in files:
        with open(f) as fh:
            all_records.extend(json.load(fh))

    print(f"[Transform] Processing {len(all_records)} records...")

    df = flatten_records(all_records)
    df = flag_threshold_breaches(df)
    summary = compute_zone_summary(df)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    readings_path = os.path.join(output_dir, f"readings_{ts}.csv")
    summary_path = os.path.join(output_dir, f"zone_summary_{ts}.csv")

    df.to_csv(readings_path, index=False)
    summary.to_csv(summary_path, index=False)

    print(f"[Transform] Saved readings   → {readings_path}")
    print(f"[Transform] Saved summary    → {summary_path}")

    return df, summary


if __name__ == "__main__":
    df, summary = transform_and_save()
    if summary is not None:
        print("\nZone Summary:")
        print(summary.to_string(index=False))
