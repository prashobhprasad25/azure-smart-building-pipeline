"""
simulate_sensors.py
--------------------
Generates realistic simulated BMS sensor readings for a smart building.
Sensors modelled: temperature, humidity, CO2, occupancy, energy consumption.

In production, this module is replaced by live BMS/IoT data feeds
ingested via Azure IoT Hub or Event Hub.
"""

import random
import json
import time
import os
from datetime import datetime, timezone


ZONES = ["Zone_A_GroundFloor", "Zone_B_FirstFloor", "Zone_C_Roof"]

SENSOR_PROFILES = {
    "temperature_c": {"base": 21.0, "noise": 1.5, "unit": "°C"},
    "humidity_pct": {"base": 45.0, "noise": 5.0, "unit": "%"},
    "co2_ppm": {"base": 600, "noise": 80, "unit": "ppm"},
    "occupancy_count": {"base": 15, "noise": 8, "unit": "people"},
    "energy_kwh": {"base": 12.5, "noise": 3.0, "unit": "kWh"},
}


def generate_reading(zone: str, inject_anomaly: bool = False) -> dict:
    """
    Generate a single sensor reading for a given building zone.

    Args:
        zone: The building zone identifier.
        inject_anomaly: If True, injects an out-of-range anomaly into the reading.

    Returns:
        dict: A sensor reading payload.
    """
    reading = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "zone": zone,
        "sensor_id": f"{zone}_SENSOR_{random.randint(1, 5):02d}",
        "readings": {},
    }

    for metric, profile in SENSOR_PROFILES.items():
        value = round(profile["base"] + random.uniform(-profile["noise"], profile["noise"]), 2)

        # Inject anomaly: spike temperature or CO2
        if inject_anomaly and metric in ("temperature_c", "co2_ppm"):
            value = round(value * random.uniform(1.8, 2.5), 2)

        reading["readings"][metric] = {
            "value": value,
            "unit": profile["unit"],
        }

    return reading


def stream_readings(output_dir: str = "data/raw", n: int = 100, interval_ms: int = 0):
    """
    Simulate a stream of sensor readings and write to NDJSON files.

    Args:
        output_dir: Directory to write raw sensor data.
        n: Number of readings to generate.
        interval_ms: Delay between readings in ms (0 = batch mode).
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"sensors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ndjson")

    print(f"[Simulator] Writing {n} readings to {filename}")

    with open(filename, "w") as f:
        for i in range(n):
            zone = random.choice(ZONES)
            anomaly = random.random() < 0.05  # 5% anomaly injection rate
            reading = generate_reading(zone, inject_anomaly=anomaly)
            f.write(json.dumps(reading) + "\n")

            if interval_ms > 0:
                time.sleep(interval_ms / 1000)

    print(f"[Simulator] Done. {n} readings written.")
    return filename


if __name__ == "__main__":
    stream_readings(output_dir="data/raw", n=200)
