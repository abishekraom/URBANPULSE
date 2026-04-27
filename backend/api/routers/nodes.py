from fastapi import APIRouter, Request, Query
from typing import List, Dict, Any
from db.queries import get_nodes, get_history, get_recent_readings

router = APIRouter(prefix="/api/nodes", tags=["Nodes"])

@router.get("")
async def list_nodes():
    return get_nodes()

@router.get("/{node_id}/data")
async def node_data(node_id: str, request: Request, limit: int = None):
    if limit is None:
        limit = request.app.state.config.get("api", {}).get("default_data_limit", 50)
    return get_recent_readings(node_id, limit)

@router.get("/{node_id}/history")
async def node_history(node_id: str, request: Request, minutes: int = None):
    if minutes is None:
        minutes = request.app.state.config.get("api", {}).get("default_history_minutes", 10)
    history = get_history(node_id, minutes)
    return [{"ts": ts, "score": score} for ts, score in history]
