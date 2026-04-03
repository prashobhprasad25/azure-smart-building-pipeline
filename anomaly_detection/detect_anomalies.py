"""
detect_anomalies.py
--------------------
Unsupervised anomaly detection on building sensor data using
Isolation Forest — a tree-based algorithm well-suited to multivariate
time-series data with unknown anomaly distributions.

Use case in Digital Twins:
  Detect early signs of equipment degradation, HVAC faults, unusual
  occupancy patterns, or energy overconsumption without needing
  labelled training data.

In Azure: this model can be serialised and served via Azure Functions
or Azure ML endpoints for real-time inference on incoming sensor streams.
"""

import os
import glob
import json
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib


FEATURE_COLS = ["temperature_c", "humidity_pct", "co2_ppm", "occupancy_count", "energy_kwh"]


def load_readings(transformed_dir: str = "data/transformed") -> pd.DataFrame:
    """Load the most recent transformed readings CSV."""
    files = sorted(glob.glob(os.path.join(transformed_dir, "readings_*.csv")))
    if not files:
        raise FileNotFoundError(f"No readings CSV found in {transformed_dir}")
    df = pd.read_csv(files[-1], parse_dates=["timestamp"])
    print(f"[Anomaly] Loaded {len(df)} rows from {files[-1]}")
    return df


def train_isolation_forest(df: pd.DataFrame, contamination: float = 0.05):
    """
    Train an Isolation Forest model on sensor readings.

    Args:
        df: Transformed sensor DataFrame with feature columns.
        contamination: Expected proportion of anomalies (default 5%).

    Returns:
        tuple: (trained model, fitted scaler, feature array)
    """
    features = df[FEATURE_COLS].dropna()

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features)

    model = IsolationForest(
        n_estimators=150,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_scaled)
    print(f"[Anomaly] Isolation Forest trained on {len(X_scaled)} samples.")
    return model, scaler, X_scaled


def detect_anomalies(df: pd.DataFrame, model, scaler) -> pd.DataFrame:
    """
    Apply trained model to label anomalies in the dataset.

    Isolation Forest returns:
      -1 = anomaly
       1 = normal

    Args:
        df: Sensor DataFrame.
        model: Fitted IsolationForest.
        scaler: Fitted StandardScaler.

    Returns:
        pd.DataFrame: DataFrame with anomaly labels and scores.
    """
    features = df[FEATURE_COLS].fillna(df[FEATURE_COLS].mean())
    X_scaled = scaler.transform(features)

    df = df.copy()
    df["anomaly_label"] = model.predict(X_scaled)
    df["anomaly_score"] = model.score_samples(X_scaled)  # lower = more anomalous
    df["is_anomaly"] = df["anomaly_label"] == -1
    return df


def save_results(df: pd.DataFrame, model, scaler, output_dir: str = "data/anomalies", model_dir: str = "models"):
    """Save flagged anomalies, full results, and serialised model."""
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save all results with anomaly labels
    all_path = os.path.join(output_dir, f"anomaly_results_{ts}.csv")
    df.to_csv(all_path, index=False)

    # Save only flagged anomalies
    anomalies = df[df["is_anomaly"]]
    flagged_path = os.path.join(output_dir, f"flagged_anomalies_{ts}.csv")
    anomalies.to_csv(flagged_path, index=False)

    # Serialise model and scaler for Azure ML / Azure Function deployment
    joblib.dump(model, os.path.join(model_dir, "isolation_forest.pkl"))
    joblib.dump(scaler, os.path.join(model_dir, "scaler.pkl"))

    print(f"[Anomaly] Results saved  → {all_path}")
    print(f"[Anomaly] Flagged        → {flagged_path} ({len(anomalies)} anomalies)")
    print(f"[Anomaly] Model saved    → {model_dir}/isolation_forest.pkl")

    return anomalies


def run_anomaly_detection(transformed_dir: str = "data/transformed"):
    """End-to-end anomaly detection pipeline."""
    df = load_readings(transformed_dir)
    model, scaler, _ = train_isolation_forest(df)
    df_labelled = detect_anomalies(df, model, scaler)
    anomalies = save_results(df_labelled, model, scaler)

    print(f"\n[Anomaly] Summary:")
    print(f"  Total readings : {len(df_labelled)}")
    print(f"  Anomalies found: {len(anomalies)} ({100 * len(anomalies) / len(df_labelled):.1f}%)")

    if not anomalies.empty:
        print("\n  Top anomalies by score (most extreme first):")
        top = anomalies.nsmallest(5, "anomaly_score")[
            ["timestamp", "zone", "sensor_id", "temperature_c", "co2_ppm", "energy_kwh", "anomaly_score"]
        ]
        print(top.to_string(index=False))

    return df_labelled, anomalies


if __name__ == "__main__":
    run_anomaly_detection()
