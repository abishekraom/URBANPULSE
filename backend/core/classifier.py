from typing import Tuple, Optional

from core.thresholds import thresholds_for_node


def classify_reading(payload: dict, config: dict) -> Tuple[str, Optional[str]]:
    node_id = payload.get("node_id", "")
    mpu_peak_amp = payload.get("mpu", {}).get("peak_amp", 0)
    piezo_raw_adc = payload.get("piezo", {}).get("raw_adc", 0)
    piezo_peak_amp = payload.get("piezo", {}).get("peak_amp", 0)

    thresholds = thresholds_for_node(config, node_id)
    mpu_thresh = thresholds.get("mpu", {})
    piezo_thresh = thresholds.get("piezo", {})

    # ── MPU checks (always in g-force) ──────────────────────────────────
    if mpu_peak_amp > mpu_thresh.get("critical_peak_amp_g", 0.8):
        return "CRITICAL", "mpu_peak_amp_critical"
    if mpu_peak_amp > mpu_thresh.get("warning_peak_amp_g", 0.3):
        return "WARNING", "mpu_peak_amp_warning"

    # ── Piezo checks ────────────────────────────────────────────────────
    # Two paths depending on data source:
    #   MQTT mock sends raw_adc (ADC units 0-4095)
    #   Firmware HTTP sends peak_amp (FFT magnitude in volts 0-3.3)

    # Path 1: raw_adc available (MQTT mock publisher)
    if piezo_raw_adc > 0:
        if piezo_raw_adc > piezo_thresh.get("critical_adc", 2000):
            return "CRITICAL", "piezo_adc_critical"
        if piezo_raw_adc > piezo_thresh.get("warning_adc", 800):
            return "WARNING", "piezo_adc_warning"

    # Path 2: piezo_peak_amp available in volts (firmware HTTP)
    if piezo_peak_amp > 0:
        critical_v = piezo_thresh.get("critical_peak_amp_v", 2.0)
        warning_v = piezo_thresh.get("warning_peak_amp_v", 0.8)
        if piezo_peak_amp > critical_v:
            return "CRITICAL", "piezo_peak_amp_critical"
        if piezo_peak_amp > warning_v:
            return "WARNING", "piezo_peak_amp_warning"

    return "NORMAL", None
