"""
UrbanPulse — Firmware HTTP POST Adapter

Converts the flat JSON payload from the ESP32 gateway's HTTP POST
into the nested format expected by the internal processing pipeline.

Key conversion: firmware sends FFT magnitude values, which need to be
converted back to physical units (g-force for MPU, volts for piezo).

FFT magnitude → physical amplitude formula:
  physical_amplitude = fft_magnitude / (SAMPLES/2 * window_coherent_gain)
                     = fft_magnitude / (256 * 0.54)
                     = fft_magnitude / 138.24

This matches the arduinoFFT library on ESP32 with 512 samples and
Hamming window (sensor_node.ino and gateway_node.ino).
"""
import time
import logging
from typing import Tuple, Optional

logger = logging.getLogger("urbanpulse.firmware_adapter")

# FFT conversion constant for ESP32 firmware
# SAMPLES=512, Hamming window coherent gain≈0.54
# FFT magnitude = physical_amplitude * SAMPLES/2 * window_gain
# physical_amplitude = FFT_magnitude / (SAMPLES/2 * window_gain)
FFT_TO_PHYSICAL = 138.24  # 256 * 0.54

# Field mapping: firmware field → (internal_sub_object, internal_field)
FIELD_MAP = {
    "mpu_dominant_freq":       ("mpu", "dom_freq"),
    "mpu_peak_amplitude":      ("mpu", "peak_amp"),     # FFT mag → convert to g-force
    "mpu_spectral_centroid":   ("mpu", "spectral_centroid"),
    "mpu_rms":                 ("mpu", "rms"),
    "piezo_dominant_freq":     ("piezo", "dom_freq"),
    "piezo_peak_amplitude":    ("piezo", "peak_amp"),   # FFT mag → convert to volts
    "piezo_spectral_centroid": ("piezo", "spectral_centroid"),
    "piezo_rms":               ("piezo", "rms"),
}


def firmware_to_internal(fw_payload: dict) -> Tuple[dict, Optional[str]]:
    """Convert firmware flat JSON to internal nested format.

    Converts FFT magnitude values back to physical units.
    Returns (internal_payload, error_message).
    """
    internal = {}

    # node_id: int → string
    raw_node = fw_payload.get("node_id")
    if raw_node is None:
        return None, "Missing 'node_id'"
    internal["node_id"] = str(raw_node)

    # timestamp → ts (use server time since ESP32 sends millis() not epoch)
    # Store the ESP32 millis as a separate field for reference
    raw_ts = fw_payload.get("timestamp")
    if raw_ts is not None:
        internal["firmware_timestamp"] = int(raw_ts)
    internal["ts"] = int(time.time() * 1000)

    # Map fields to nested structure
    internal["mpu"] = {}
    internal["piezo"] = {}

    for fw_field, (sub_obj, sub_field) in FIELD_MAP.items():
        value = fw_payload.get(fw_field)
        if value is not None:
            internal[sub_obj][sub_field] = value

    # Convert peak_amp and rms from FFT magnitude to physical units
    # MPU: g-force
    if "peak_amp" in internal.get("mpu", {}):
        internal["mpu"]["peak_amp"] = internal["mpu"]["peak_amp"] / FFT_TO_PHYSICAL
    if "rms" in internal.get("mpu", {}):
        internal["mpu"]["rms"] = internal["mpu"]["rms"] / FFT_TO_PHYSICAL
    # Piezo: volts  
    if "peak_amp" in internal.get("piezo", {}):
        internal["piezo"]["peak_amp"] = internal["piezo"]["peak_amp"] / FFT_TO_PHYSICAL
    if "rms" in internal.get("piezo", {}):
        internal["piezo"]["rms"] = internal["piezo"]["rms"] / FFT_TO_PHYSICAL

    # Set raw fields to 0 if not provided by firmware
    # (firmware sends RMS instead of raw x/y/z values)
    internal["mpu"].setdefault("raw_x", 0.0)
    internal["mpu"].setdefault("raw_y", 0.0)
    internal["mpu"].setdefault("raw_z", 0.0)
    internal["piezo"].setdefault("raw_adc", 0.0)

    return internal, None


def classify_severity_from_internal(internal: dict, config: dict) -> Tuple[str, Optional[str]]:
    """Run the same rule-based classifier on the converted payload.

    Returns (severity_label, reason).
    """
    from core.classifier import classify_reading
    return classify_reading(internal, config)
