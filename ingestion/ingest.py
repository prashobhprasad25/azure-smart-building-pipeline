"""
ingest.py
----------
Handles ingestion of raw sensor data.

Locally: reads NDJSON files from data/raw and writes validated records
         to data/ingested as JSON.

Azure-ready: when AZURE_STORAGE_CONNECTION_STRING is set in environment,
             uploads ingested files to Azure Blob Storage (raw container).

This mirrors the ingestion layer of an Azure IoT / Event Hub pipeline.
"""

import json
import os
import glob
from datetime import datetime


REQUIRED_FIELDS = {"timestamp", "zone", "sensor_id", "readings"}
REQUIRED_METRICS = {"temperature_c", "humidity_pct", "co2_ppm", "occupancy_count", "energy_kwh"}

# --- Azure Blob Storage (optional, activated by env var) ---
try:
    from azure.storage.blob import BlobServiceClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False


def validate_record(record: dict) -> bool:
    """Basic schema validation for a sensor reading."""
    if not REQUIRED_FIELDS.issubset(record.keys()):
        return False
    if not REQUIRED_METRICS.issubset(record["readings"].keys()):
        return False
    return True


def ingest_file(filepath: str, output_dir: str = "data/ingested") -> list:
    """
    Read an NDJSON file, validate records, and write cleaned output.

    Args:
        filepath: Path to the raw NDJSON sensor file.
        output_dir: Directory for validated/ingested output.

    Returns:
        list: Successfully validated records.
    """
    os.makedirs(output_dir, exist_ok=True)
    valid_records = []
    skipped = 0

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if validate_record(record):
                    valid_records.append(record)
                else:
                    skipped += 1
            except json.JSONDecodeError:
                skipped += 1

    print(f"[Ingestion] {filepath}: {len(valid_records)} valid, {skipped} skipped.")

    # Write validated records locally
    out_filename = os.path.join(
        output_dir,
        f"ingested_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(out_filename, "w") as f:
        json.dump(valid_records, f, indent=2)

    # --- Azure Blob upload (if configured) ---
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if connection_string and AZURE_AVAILABLE:
        upload_to_blob(out_filename, connection_string, container="raw-sensor-data")
    elif connection_string and not AZURE_AVAILABLE:
        print("[Ingestion] WARNING: Azure connection string set but azure-storage-blob not installed.")

    return valid_records


def upload_to_blob(filepath: str, connection_string: str, container: str):
    """
    Upload a file to Azure Blob Storage.

    Args:
        filepath: Local file to upload.
        connection_string: Azure Storage connection string.
        container: Target blob container name.
    """
    try:
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service.get_container_client(container)

        blob_name = os.path.basename(filepath)
        with open(filepath, "rb") as data:
            container_client.upload_blob(name=blob_name, data=data, overwrite=True)

        print(f"[Azure] Uploaded {blob_name} to container '{container}'.")
    except Exception as e:
        print(f"[Azure] Upload failed: {e}")


def ingest_all(raw_dir: str = "data/raw", output_dir: str = "data/ingested"):
    """Ingest all NDJSON files in the raw data directory."""
    files = glob.glob(os.path.join(raw_dir, "*.ndjson"))
    if not files:
        print(f"[Ingestion] No files found in {raw_dir}.")
        return []

    all_records = []
    for f in files:
        records = ingest_file(f, output_dir)
        all_records.extend(records)

    print(f"[Ingestion] Total ingested: {len(all_records)} records from {len(files)} file(s).")
    return all_records


if __name__ == "__main__":
    ingest_all()
