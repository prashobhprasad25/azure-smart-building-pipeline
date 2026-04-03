"""
run_pipeline.py
----------------
End-to-end local pipeline runner.

Steps:
  1. Simulate BMS sensor data
  2. Ingest and validate records
  3. Transform and compute zone summaries
  4. Run anomaly detection (Isolation Forest)
  5. Print summary report

Run:
  python run_pipeline.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from data_simulator.simulate_sensors import stream_readings
from ingestion.ingest import ingest_all
from transformation.transform import transform_and_save
from anomaly_detection.detect_anomalies import run_anomaly_detection


def run():
    print("=" * 60)
    print("  SMART BUILDING DIGITAL TWIN — DATA PIPELINE")
    print("=" * 60)

    print("\n[1/4] Simulating sensor data...")
    stream_readings(output_dir="data/raw", n=300)

    print("\n[2/4] Ingesting and validating records...")
    records = ingest_all(raw_dir="data/raw", output_dir="data/ingested")
    print(f"      {len(records)} records ingested.")

    print("\n[3/4] Transforming data and computing zone summaries...")
    df, summary = transform_and_save(ingested_dir="data/ingested", output_dir="data/transformed")
    if summary is not None:
        print("\n  Zone Performance Summary:")
        print(summary[["zone", "temperature_c_mean", "co2_ppm_mean", "energy_kwh_mean", "total_breaches"]].to_string(index=False))

    print("\n[4/4] Running anomaly detection...")
    df_labelled, anomalies = run_anomaly_detection(transformed_dir="data/transformed")

    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Total readings processed : {len(df_labelled)}")
    print(f"  Threshold breaches       : {df_labelled['any_breach'].sum()}")
    print(f"  Anomalies detected       : {len(anomalies)}")
    print(f"\n  Output directories:")
    print(f"    data/raw/          — raw simulated sensor files")
    print(f"    data/ingested/     — validated JSON records")
    print(f"    data/transformed/  — flat CSVs + zone summaries")
    print(f"    data/anomalies/    — anomaly detection results")
    print(f"    models/            — serialised Isolation Forest model")
    print("=" * 60)


if __name__ == "__main__":
    run()
