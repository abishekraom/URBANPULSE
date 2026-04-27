def compute_health_score(payload: dict, config: dict, baseline_freq: float = None) -> int:
    score = 100
    
    mpu_peak_amp = payload.get("mpu", {}).get("peak_amp", 0)
    piezo_raw_adc = payload.get("piezo", {}).get("raw_adc", 0)
    mpu_dom_freq = payload.get("mpu", {}).get("dom_freq", 0)
    
    thresholds = config.get("thresholds", {})
    health_config = config.get("health_score", {})
    
    mpu_thresh = thresholds.get("mpu", {})
    piezo_thresh = thresholds.get("piezo", {})
    
    # MPU penalty
    if mpu_peak_amp > mpu_thresh.get("critical_peak_amp_g", 0.8):
        score -= health_config.get("mpu_critical_penalty", 60)
    elif mpu_peak_amp > mpu_thresh.get("warning_peak_amp_g", 0.3):
        score -= health_config.get("mpu_warning_penalty", 30)
        
    # Piezo penalty
    if piezo_raw_adc > piezo_thresh.get("critical_adc", 2000):
        score -= health_config.get("piezo_critical_penalty", 60)
    elif piezo_raw_adc > piezo_thresh.get("warning_adc", 800):
        score -= health_config.get("piezo_warning_penalty", 30)
        
    # Frequency deviation penalty
    if baseline_freq and baseline_freq > 0:
        dev_pct = abs(mpu_dom_freq - baseline_freq) / baseline_freq * 100
        if dev_pct > thresholds.get("frequency_deviation_pct", 20):
            score -= health_config.get("freq_deviation_penalty", 10)
            
    return max(0, int(score))
