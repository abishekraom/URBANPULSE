from typing import Tuple, Optional

def classify_reading(payload: dict, config: dict) -> Tuple[str, Optional[str]]:
    mpu_peak_amp = payload.get("mpu", {}).get("peak_amp", 0)
    piezo_raw_adc = payload.get("piezo", {}).get("raw_adc", 0)
    
    thresholds = config.get("thresholds", {})
    mpu_thresh = thresholds.get("mpu", {})
    piezo_thresh = thresholds.get("piezo", {})
    
    # CRITICAL checks
    if mpu_peak_amp > mpu_thresh.get("critical_peak_amp_g", 0.8):
        return "CRITICAL", "mpu_peak_amp_critical"
    if piezo_raw_adc > piezo_thresh.get("critical_adc", 2000):
        return "CRITICAL", "piezo_adc_critical"
        
    # WARNING checks
    if mpu_peak_amp > mpu_thresh.get("warning_peak_amp_g", 0.3):
        return "WARNING", "mpu_peak_amp_warning"
    if piezo_raw_adc > piezo_thresh.get("warning_adc", 800):
        return "WARNING", "piezo_adc_warning"
        
    return "NORMAL", None
