import time
from fastapi import APIRouter, Request

router = APIRouter(prefix="/api", tags=["System"])

START_TIME = time.time()

@router.get("/health")
async def get_health():
    uptime_s = int(time.time() - START_TIME)
    return {
        "uptime_s": uptime_s,
        "total_packets": 0, # Placeholder, can be updated if we track it globally
        "last_packet_age_ms": 0, # Placeholder
        "status": "healthy"
    }

@router.get("/config/thresholds")
async def get_thresholds(request: Request):
    config = request.app.state.config
    return config.get("thresholds", {})
