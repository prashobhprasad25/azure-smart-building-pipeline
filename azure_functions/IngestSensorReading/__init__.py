"""
__init__.py  —  Azure Function: IngestSensorReading
-----------------------------------------------------
HTTP-triggered Azure Function that receives a JSON sensor reading,
validates it, and writes it to Azure Blob Storage (raw-sensor-data container).

Deployment:
  func azure functionapp publish <your-app-name>

Local testing:
  func start  (requires Azure Functions Core Tools)

Environment variables required (set in Azure Portal → Configuration):
  AZURE_STORAGE_CONNECTION_STRING  — your storage account connection string
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

import azure.functions as func

# Optional: only imported when running in Azure
try:
    from azure.storage.blob import BlobServiceClient
    AZURE_BLOB_AVAILABLE = True
except ImportError:
    AZURE_BLOB_AVAILABLE = False

REQUIRED_FIELDS = {"timestamp", "zone", "sensor_id", "readings"}
REQUIRED_METRICS = {"temperature_c", "humidity_pct", "co2_ppm", "occupancy_count", "energy_kwh"}


def validate_payload(payload: dict) -> tuple[bool, str]:
    if not REQUIRED_FIELDS.issubset(payload.keys()):
        missing = REQUIRED_FIELDS - payload.keys()
        return False, f"Missing fields: {missing}"
    if not REQUIRED_METRICS.issubset(payload.get("readings", {}).keys()):
        missing = REQUIRED_METRICS - payload["readings"].keys()
        return False, f"Missing metrics: {missing}"
    return True, "OK"


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("IngestSensorReading: received request.")

    try:
        payload = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body."}),
            status_code=400,
            mimetype="application/json",
        )

    valid, msg = validate_payload(payload)
    if not valid:
        return func.HttpResponse(
            json.dumps({"error": msg}),
            status_code=422,
            mimetype="application/json",
        )

    # Write to Azure Blob Storage
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    blob_name = f"{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{uuid.uuid4()}.json"

    if connection_string and AZURE_BLOB_AVAILABLE:
        try:
            blob_service = BlobServiceClient.from_connection_string(connection_string)
            container_client = blob_service.get_container_client("raw-sensor-data")
            container_client.upload_blob(name=blob_name, data=json.dumps(payload), overwrite=True)
            logging.info(f"Uploaded blob: {blob_name}")
        except Exception as e:
            logging.error(f"Blob upload failed: {e}")
            return func.HttpResponse(
                json.dumps({"error": "Blob upload failed.", "detail": str(e)}),
                status_code=500,
                mimetype="application/json",
            )
    else:
        logging.warning("AZURE_STORAGE_CONNECTION_STRING not set — running in local/dry-run mode.")

    return func.HttpResponse(
        json.dumps({
            "status": "accepted",
            "blob_name": blob_name,
            "zone": payload.get("zone"),
            "sensor_id": payload.get("sensor_id"),
        }),
        status_code=202,
        mimetype="application/json",
    )
