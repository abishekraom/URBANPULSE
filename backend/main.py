"""
UrbanPulse Backend — main.py

Entry point for the FastAPI application. Handles:
- Config loading from config.json
- Broker connectivity check on startup
- FastAPI app + CORS middleware
- Lifespan hook (startup / shutdown)
"""
import asyncio
import json
import logging
import socket
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mqtt.ingester import MQTTIngester
from mqtt.publisher import MQTTPublisher
from core.pipeline import process_queue
from core.heartbeat import heartbeat_monitor

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("urbanpulse")

# ── Config ───────────────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


config = load_config()


# ── Broker connectivity check ─────────────────────────────────────────────────
def check_broker(host: str, port: int) -> bool:
    """Return True if Mosquitto is reachable on host:port."""
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("  UrbanPulse Backend Starting")
    logger.info("=" * 60)

    broker_host = config["broker"]["host"]
    broker_port = config["broker"]["port"]

    broker_ok = check_broker(broker_host, broker_port)

    if broker_ok:
        logger.info("✓ MQTT broker reachable at %s:%d", broker_host, broker_port)
    else:
        logger.error("✗ MQTT broker NOT reachable at %s:%d", broker_host, broker_port)
        logger.error("  ► Start Mosquitto first:")
        logger.error(
            "    mosquitto.exe -c backend\\mosquitto.conf -v"
        )
        logger.warning("  Backend is running but MQTT ingestion is INACTIVE.")

    logger.info("✓ Configuration loaded from config.json")
    logger.info("✓ FastAPI ready — http://localhost:8000")
    logger.info("  Docs: http://localhost:8000/docs")
    logger.info("=" * 60)

    # Expose shared state
    app.state.config = config
    app.state.broker_ok = broker_ok
    app.state.queue = asyncio.Queue(maxsize=1000)
    
    app.state.ingester = MQTTIngester(config, app.state.queue, asyncio.get_event_loop())
    app.state.publisher = MQTTPublisher(config)

    if broker_ok:
        app.state.ingester.start()
        app.state.publisher.connect()
        app.state.pipeline_task = asyncio.create_task(process_queue(app.state))
        app.state.heartbeat_task = asyncio.create_task(heartbeat_monitor(app.state))

    yield  # ← application runs here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("UrbanPulse Backend shutting down...")
    if app.state.ingester is not None:
        app.state.ingester.stop()
    if app.state.publisher is not None:
        app.state.publisher.disconnect()
        
    if hasattr(app.state, "pipeline_task"):
        app.state.pipeline_task.cancel()
    if hasattr(app.state, "heartbeat_task"):
        app.state.heartbeat_task.cancel()
    
    logger.info("Goodbye.")


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="UrbanPulse API",
    description="Structural Health Monitoring Backend — rule-based, offline-first",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config["api"]["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from api.routers import nodes, alerts, system, ws

app.include_router(nodes.router)
app.include_router(alerts.router)
app.include_router(system.router)
app.include_router(ws.router)

# ── Root endpoint ─────────────────────────────────────────────────────────────
@app.get("/", tags=["System"])
async def root():
    """Health ping — confirms backend is running."""
    return {
        "service": "UrbanPulse",
        "status": "running",
        "version": "1.0.0",
    }
