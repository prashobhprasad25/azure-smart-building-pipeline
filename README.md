# Azure Smart Building Pipeline — Digital Twin Data Infrastructure

A production-ready data pipeline simulating the ingestion, transformation, and anomaly detection layer of a **Smart Building Digital Twin** — built for facilities management use cases.

This project demonstrates the core data engineering and AI capabilities required for Digital Twin platforms in the built environment: sensor data integration, real-time ingestion via Azure Functions, cloud storage via Azure Blob, and unsupervised anomaly detection for predictive maintenance.

---

## Architecture

```
BMS / IoT Sensors
      │
      ▼
[Azure Functions]  ←── HTTP trigger (IngestSensorReading)
      │
      ▼
[Azure Blob Storage]  raw-sensor-data container
      │
      ▼
[Transformation Layer]  flatten · validate · threshold flagging
      │
      ▼
[Anomaly Detection]  Isolation Forest (unsupervised ML)
      │
      ▼
[Outputs]  zone summaries · flagged anomalies · serialised model
```

**Local mode** (this repo): the full pipeline runs locally with simulated BMS data.  
**Azure mode**: swap environment variable `AZURE_STORAGE_CONNECTION_STRING` to activate live Blob upload and deploy via `func azure functionapp publish`.

---

## Use Case

Commercial buildings generate continuous streams from:
- **BMS (Building Management Systems)** — HVAC, heating, ventilation
- **Environmental sensors** — temperature, humidity, CO₂
- **Energy meters** — kWh consumption per zone
- **Occupancy sensors** — people counts, motion

This pipeline ingests, validates, and analyses that data to support:
- **Predictive maintenance** — detect equipment degradation before failure
- **Energy optimisation** — flag anomalous consumption patterns
- **Operational insight** — zone-level performance dashboards
- **Digital Twin readiness** — structured data layer for BIM/DT integration

---

## Features

| Component | Description |
|---|---|
| `data_simulator/` | Generates realistic multi-zone BMS sensor streams (NDJSON) with 5% injected anomalies |
| `ingestion/` | Schema validation + Azure Blob Storage upload (activated by env var) |
| `transformation/` | Flattens nested JSON → tabular CSV; per-zone aggregates; CIBSE threshold breach flagging |
| `anomaly_detection/` | Isolation Forest anomaly detection; serialises model as `.pkl` for Azure ML deployment |
| `azure_functions/` | Azure Functions HTTP trigger (`IngestSensorReading`) — ready to deploy |

---

## Sensors Modelled

| Metric | Normal Range | Unit |
|---|---|---|
| Temperature | 18–26 | °C |
| Humidity | 30–70 | % |
| CO₂ | < 1000 | ppm |
| Occupancy | 0–50 | people |
| Energy consumption | 0–30 | kWh |

Thresholds based on **CIBSE Guidelines** for commercial buildings.

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/Nivedita-Saha/azure-smart-building-pipeline.git
cd azure-smart-building-pipeline
pip install -r requirements.txt
```

### 2. Run the full pipeline

```bash
python run_pipeline.py
```

This will:
- Generate 300 simulated sensor readings across 3 building zones
- Validate and ingest records
- Compute zone performance summaries
- Run Isolation Forest anomaly detection
- Output flagged anomalies and a serialised model to `models/`

### 3. Output directories

```
data/raw/           — raw NDJSON sensor files
data/ingested/      — validated JSON records
data/transformed/   — flat CSVs + zone summaries
data/anomalies/     — anomaly detection results + flagged records
models/             — isolation_forest.pkl + scaler.pkl
```

---

## Azure Deployment

### Blob Storage (ingestion)

Set your connection string:

```bash
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"
```

Re-run `python ingestion/ingest.py` — ingested files will be uploaded to the `raw-sensor-data` blob container automatically.

### Azure Functions (real-time ingestion endpoint)

```bash
cd azure_functions
func start                                          # local testing
func azure functionapp publish <your-app-name>     # deploy to Azure
```

The `IngestSensorReading` function exposes a POST endpoint:

```
POST /api/ingest/sensor
Content-Type: application/json

{
  "timestamp": "2025-04-01T10:00:00+00:00",
  "zone": "Zone_A_GroundFloor",
  "sensor_id": "Zone_A_GroundFloor_SENSOR_01",
  "readings": {
    "temperature_c": {"value": 22.4, "unit": "°C"},
    "humidity_pct": {"value": 48.0, "unit": "%"},
    "co2_ppm": {"value": 620, "unit": "ppm"},
    "occupancy_count": {"value": 12, "unit": "people"},
    "energy_kwh": {"value": 11.8, "unit": "kWh"}
  }
}
```

---

## Anomaly Detection

The pipeline uses **Isolation Forest** (sklearn) — an unsupervised algorithm that identifies readings that are statistically isolated from normal building behaviour. This is particularly effective for:

- Early HVAC degradation (temperature drift + energy spike)
- Air quality events (CO₂ spikes)
- Unusual occupancy/energy combinations

The trained model is serialised as `models/isolation_forest.pkl` and can be:
- Deployed to **Azure ML** as a real-time inference endpoint
- Packaged in a **Docker container** and deployed as an Azure Container Instance
- Embedded in an **Azure Function** for sub-second inference on incoming sensor streams

---

## Security Considerations

- No credentials are hardcoded. All Azure credentials are passed via environment variables.
- The Azure Function uses `authLevel: function` — requests require a function key.
- In production, data in transit is encrypted via HTTPS (Azure Blob enforces TLS 1.2+).
- Role-based access control (RBAC) should be applied to storage containers via Azure IAM.

---

## Digital Twin Integration Pathway

This pipeline forms the **data layer** of a broader Digital Twin architecture:

```
This repo (data layer)
        │
        ▼
Azure Digital Twins (ADT) — model physical assets as twins
        │
        ▼
Azure Time Series Insights — historical trend analysis
        │
        ▼
Power BI / Grafana — operational dashboards for estates teams
```

---

## Tech Stack

- **Python** 3.11+
- **Azure Functions** v4 (HTTP trigger)
- **Azure Blob Storage** SDK (`azure-storage-blob`)
- **scikit-learn** — Isolation Forest
- **pandas / numpy** — data transformation
- **joblib** — model serialisation

---

## Project Status

| Component | Status |
|---|---|
| Sensor simulator | ✅ Complete |
| Ingestion + validation | ✅ Complete |
| Azure Blob upload | ✅ Ready (requires connection string) |
| Transformation + zone summary | ✅ Complete |
| Anomaly detection (Isolation Forest) | ✅ Complete |
| Azure Functions deployment | ✅ Ready to deploy |
| Azure ML model endpoint | 🔜 Planned |
| Power BI dashboard integration | 🔜 Planned |

---

## Author

**Nivedita Saha**  
MSc Artificial Intelligence and Data Science (Distinction) — Keele University, 2025  
[nivsaha.com](https://nivsaha.com) · [GitHub](https://github.com/Nivedita-Saha)
