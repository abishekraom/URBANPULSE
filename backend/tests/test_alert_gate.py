import unittest

from core.alert_gate import AlertGate


class AlertGateTest(unittest.TestCase):
    def test_suppresses_duplicate_alerts_inside_cooldown_per_node_severity_reason(self):
        gate = AlertGate(cooldown_ms=5000)
        self.assertTrue(gate.should_emit('1', 'WARNING', 'mpu_peak_amp_warning', now_ms=10000))
        self.assertFalse(gate.should_emit('1', 'WARNING', 'mpu_peak_amp_warning', now_ms=12000))
        self.assertTrue(gate.should_emit('1', 'WARNING', 'mpu_peak_amp_warning', now_ms=15100))

    def test_allows_different_node_or_severity_or_reason_immediately(self):
        gate = AlertGate(cooldown_ms=5000)
        self.assertTrue(gate.should_emit('1', 'WARNING', 'mpu_peak_amp_warning', now_ms=10000))
        self.assertTrue(gate.should_emit('2', 'WARNING', 'mpu_peak_amp_warning', now_ms=10001))
        self.assertTrue(gate.should_emit('1', 'CRITICAL', 'mpu_peak_amp_warning', now_ms=10002))
        self.assertTrue(gate.should_emit('1', 'WARNING', 'piezo_peak_amp_warning', now_ms=10003))


if __name__ == '__main__':
    unittest.main()
