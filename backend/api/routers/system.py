import time
from fastapi import APIRouter, Request

router = APIRouter(prefix="/api", tags=["System"])

START_TIME = time.time()

@router.get("/health")
async def get_health(request: Request):
    uptime_s = int(time.time() - START_TIME)
    stats = getattr(request.app.state, "stats", None)
    if stats:
        total_packets = stats["total_packets"]
        last_packet_age_ms = int(time.time() * 1000) - stats["last_packet_ts"] if stats["last_packet_ts"] > 0 else 0
    else:
        total_packets = 0
        last_packet_age_ms = 0
    return {
        "uptime_s": uptime_s,
        "total_packets": total_packets,
        "last_packet_age_ms": last_packet_age_ms,
        "status": "healthy"
    }

@router.get("/config/thresholds")
async def get_thresholds(request: Request):
    config = request.app.state.config
    return config.get("thresholds", {})
