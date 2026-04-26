# UrbanPulse Backend

This is the backend data ingestion, processing, and API layer for the UrbanPulse project. It connects to an MQTT broker to receive telemetry from ESP32 nodes, processes the data through a continuous asynchronous pipeline, computes health scores based on Fast Fourier Transform (FFT) features, detects anomalies, and exposes REST and WebSocket APIs for front-end dashboards.

## Architecture

- **FastAPI**: Core API framework with `asyncio`.
- **Paho-MQTT**: Non-blocking background thread mapped to an asyncio queue for ingesting sensor data.
- **SQLite (WAL)**: High-performance local storage for telemetry time series, nodes, and alerts.
- **WebSocket Hub**: Real-time broadcast engine that pushes new readings and alerts to the frontend with sub-second latency.

## Prerequisites

- Python 3.10+
- An MQTT broker (e.g., Eclipse Mosquitto) running locally on port 1883.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure the system (optional):
   Modify `config.json` to tune anomaly thresholds, health scoring weights, and heartbeat timeouts.

## Running the Server

1. Ensure your Mosquitto broker is running. If you have Mosquitto installed locally, you can run:
   ```bash
   mosquitto -c mosquitto.conf
   ```

2. Start the FastAPI application:
   ```bash
   uvicorn main:app --host 0.0.0.1 --port 8000 --reload
   ```

3. The server will initialize its SQLite database automatically on startup (`urbanpulse.db`).

## Mock Testing

If you don't have ESP32 hardware connected, you can simulate network traffic:

1. In a new terminal, run the mock publisher in `normal` mode to simulate healthy nodes:
   ```bash
   python mock_publisher.py --mode normal
   ```

2. Run the mock publisher in `fault` mode to simulate a CRITICAL anomaly on a specific node (e.g., Node B):
   ```bash
   python mock_publisher.py --mode fault --node "Node B"
   ```

## Endpoints

- **REST API Docs**: `http://localhost:8000/docs`
- **WebSocket Hub**: `ws://localhost:8000/ws`
