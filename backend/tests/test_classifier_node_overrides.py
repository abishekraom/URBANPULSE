import unittest

from core.classifier import classify_reading
from core.health_score import compute_health_score


class NodeOverrideThresholdTest(unittest.TestCase):
    def test_classifier_uses_node_specific_piezo_thresholds_when_present(self):
        config = {
            "thresholds": {
                "mpu": {"warning_peak_amp_g": 1.8, "critical_peak_amp_g": 2.8},
                "piezo": {"warning_peak_amp_v": 0.3, "critical_peak_amp_v": 0.8},
                "node_overrides": {
                    "1": {
                        "piezo": {"warning_peak_amp_v": 0.12, "critical_peak_amp_v": 0.35}
                    }
                },
            }
        }
        payload = {
            "node_id": "1",
            "mpu": {"peak_amp": 0.5},
            "piezo": {"peak_amp": 0.16, "raw_adc": 0},
        }
        self.assertEqual(classify_reading(payload, config), ("WARNING", "piezo_peak_amp_warning"))

    def test_health_score_uses_node_specific_mpu_thresholds_when_present(self):
        config = {
            "thresholds": {
                "mpu": {"warning_peak_amp_g": 1.8, "critical_peak_amp_g": 2.8},
                "piezo": {"warning_peak_amp_v": 0.3, "critical_peak_amp_v": 0.8},
                "node_overrides": {
                    "2": {
                        "mpu": {"warning_peak_amp_g": 1.5, "critical_peak_amp_g": 2.5}
                    }
                },
            },
            "health_score": {
                "mpu_warning_penalty": 30,
                "mpu_critical_penalty": 60,
                "piezo_warning_penalty": 30,
                "piezo_critical_penalty": 60,
            },
        }
        payload = {
            "node_id": "2",
            "mpu": {"peak_amp": 1.6, "dom_freq": 2.0},
            "piezo": {"peak_amp": 0.2, "raw_adc": 0},
        }
        self.assertEqual(compute_health_score(payload, config), 70)


if __name__ == "__main__":
    unittest.main()
