"""
UrbanPulse — MQTT Contract Validator

Validates inbound payloads against the SPEC-defined MQTT contract.
When the real ESP32 hardware connects for the first time, any format
mismatch is caught here with clear log messages instead of silent failures.

Reference: .gsd/SPEC.md § MQTT Contract
"""
import logging
from typing import Tuple, Optional

logger = logging.getLogger("urbanpulse.contract")

# Required fields for a data reading payload
DATA_REQUIRED_TOP = ["node_id", "ts", "mpu", "piezo"]
DATA_REQUIRED_MPU = ["dom_freq", "peak_amp", "spectral_centroid", "raw_x", "raw_y", "raw_z"]
DATA_REQUIRED_PIEZO = ["dom_freq", "peak_amp", "spectral_centroid", "raw_adc"]

# Required fields for a heartbeat payload
HEARTBEAT_REQUIRED = ["node_id", "ts"]


def validate_data_payload(payload: dict) -> Tuple[bool, Optional[str]]:
    """Validate a sensor data payload against the MQTT contract.

    Returns (is_valid, error_reason). If is_valid is False, the caller
    should log the reason and drop the message.
    """
    if not isinstance(payload, dict):
        return False, "Payload is not a JSON object"

    # Check top-level fields
    for field in DATA_REQUIRED_TOP:
        if field not in payload:
            return False, f"Missing top-level field: '{field}'"
        if field == "node_id" and not isinstance(payload["node_id"], str):
            return False, f"'{field}' must be a string, got {type(payload[field]).__name__}"
        if field == "ts" and not isinstance(payload["ts"], (int, float)):
            return False, f"'{field}' must be numeric, got {type(payload[field]).__name__}"

    # Validate mpu sub-object
    mpu = payload.get("mpu", {})
    if not isinstance(mpu, dict):
        return False, "'mpu' must be a JSON object"
    for field in DATA_REQUIRED_MPU:
        if field not in mpu:
            return False, f"Missing field in mpu: '{field}'"

    # Validate piezo sub-object
    piezo = payload.get("piezo", {})
    if not isinstance(piezo, dict):
        return False, "'piezo' must be a JSON object"
    for field in DATA_REQUIRED_PIEZO:
        if field not in piezo:
            return False, f"Missing field in piezo: '{field}'"

    return True, None


def validate_heartbeat_payload(payload: dict) -> Tuple[bool, Optional[str]]:
    """Validate a heartbeat payload against the MQTT contract."""
    if not isinstance(payload, dict):
        return False, "Payload is not a JSON object"

    for field in HEARTBEAT_REQUIRED:
        if field not in payload:
            return False, f"Missing heartbeat field: '{field}'"
        if field == "node_id" and not isinstance(payload["node_id"], str):
            return False, f"Heartbeat '{field}' must be a string"
        if field == "ts" and not isinstance(payload["ts"], (int, float)):
            return False, f"Heartbeat '{field}' must be numeric"

    return True, None
