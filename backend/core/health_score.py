from core.thresholds import thresholds_for_node


def compute_health_score(payload: dict, config: dict, baseline_freq: float = None) -> int:
    score = 100

    node_id = payload.get("node_id", "")
    mpu_peak_amp = payload.get("mpu", {}).get("peak_amp", 0)
    piezo_raw_adc = payload.get("piezo", {}).get("raw_adc", 0)
    piezo_peak_amp = payload.get("piezo", {}).get("peak_amp", 0)
    mpu_dom_freq = payload.get("mpu", {}).get("dom_freq", 0)

    thresholds = thresholds_for_node(config, node_id)
    health_config = config.get("health_score", {})

    mpu_thresh = thresholds.get("mpu", {})
    piezo_thresh = thresholds.get("piezo", {})

    # MPU penalty (always in g-force)
    if mpu_peak_amp > mpu_thresh.get("critical_peak_amp_g", 0.8):
        score -= health_config.get("mpu_critical_penalty", 60)
    elif mpu_peak_amp > mpu_thresh.get("warning_peak_amp_g", 0.3):
        score -= health_config.get("mpu_warning_penalty", 30)

    # Piezo penalty — two paths
    # Path 1: raw_adc (ADC units, MQTT mock)
    if piezo_raw_adc > 0:
        if piezo_raw_adc > piezo_thresh.get("critical_adc", 2000):
            score -= health_config.get("piezo_critical_penalty", 60)
        elif piezo_raw_adc > piezo_thresh.get("warning_adc", 800):
            score -= health_config.get("piezo_warning_penalty", 30)
    # Path 2: peak_amp in volts (firmware HTTP)
    elif piezo_peak_amp > 0:
        critical_v = piezo_thresh.get("critical_peak_amp_v", 2.0)
        warning_v = piezo_thresh.get("warning_peak_amp_v", 0.8)
        if piezo_peak_amp > critical_v:
            score -= health_config.get("piezo_critical_penalty", 60)
        elif piezo_peak_amp > warning_v:
            score -= health_config.get("piezo_warning_penalty", 30)

    # Frequency deviation penalty
    if baseline_freq and baseline_freq > 0:
        dev_pct = abs(mpu_dom_freq - baseline_freq) / baseline_freq * 100
        if dev_pct > thresholds.get("frequency_deviation_pct", 20):
            score -= health_config.get("freq_deviation_penalty", 10)

    return max(0, int(score))
