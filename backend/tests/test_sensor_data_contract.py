import unittest
from fastapi.testclient import TestClient

from main import app


class SensorDataContractTest(unittest.TestCase):
    def test_invalid_json_returns_400(self):
        with TestClient(app) as client:
            resp = client.post('/api/sensor-data', data='not-json', headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['status'], 'error')

    def test_missing_node_id_returns_422(self):
        payload = {
            'timestamp': 123,
            'mpu_dominant_freq': 12.0,
            'mpu_peak_amplitude': 1.0,
            'mpu_spectral_centroid': 14.0,
            'mpu_rms': 0.5,
            'piezo_dominant_freq': 300.0,
            'piezo_peak_amplitude': 1.0,
            'piezo_spectral_centroid': 350.0,
            'piezo_rms': 0.5,
        }
        with TestClient(app) as client:
            resp = client.post('/api/sensor-data', json=payload)
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()['status'], 'error')


if __name__ == '__main__':
    unittest.main()
