import csv
import io
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from db.queries import get_alerts, get_all_alerts

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

@router.get("")
async def list_alerts(request: Request, limit: int = None):
    if limit is None:
        limit = request.app.state.config.get("api", {}).get("default_alert_limit", 20)
    return get_alerts(limit)

@router.get("/export")
async def export_alerts():
    alerts = get_all_alerts()
    
    # We yield chunks of the CSV text
    def iter_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        # write header
        writer.writerow(["id", "node_id", "severity", "reason", "ts"])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        
        for alert in alerts:
            writer.writerow([alert["id"], alert["node_id"], alert["severity"], alert["reason"], alert["ts"]])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    headers = {
        "Content-Disposition": "attachment; filename=alerts.csv"
    }
    return StreamingResponse(iter_csv(), media_type="text/csv", headers=headers)
