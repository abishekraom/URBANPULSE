# Firmware and Hardware Reference

## Firmware paths

| Path | Role | Current status |
|---|---|---|
| `sensor_node/src/sensor_node.ino` | PlatformIO firmware for sensor sender nodes 2/3 | Builds for `node2` and `node3`; `NODE_ID` now supplied by build flags. |
| `pio_gateway/src/gateway_node.ino` | PlatformIO gateway firmware, preferred current gateway | Builds; safer queued ESP-NOW receive; uses backend port `8001`. |
| `gateway_node/gateway_node.ino` | Root Arduino IDE gateway duplicate/legacy | Diverges from PlatformIO gateway. Treat as legacy unless explicitly synchronized. |
| `sensor_node/platformio.ini` | Sensor PlatformIO config | Envs: `node2`, `node3`, compatibility `esp32dev`. |
| `pio_gateway/platformio.ini` | Gateway PlatformIO config | Upload port `COM10`, Arduino ESP32, `arduinoFFT@1.6.0`. |
| `pin_connections.txt` | Wiring guide | Useful canonical pin map. |

## Build verification

Verified commands:

```bash
cd sensor_node
pio run -e node2
pio run -e node3

cd ../pio_gateway
pio run
```

Results:

```text
node2 SUCCESS
node3 SUCCESS
pio_gateway SUCCESS
```

Remaining warnings are from `arduinoFFT@1.6.0` deprecation warnings. The previous `Wire.requestFrom(...)` ambiguous overload warning was fixed by explicit casts.

## Hardware architecture

```text
Node 2 / Node 3
  ESP32 + MPU-6050 + piezo/LM358
  compute FFT features
  send SensorPacket via ESP-NOW
        │
        ▼
Gateway Node 1
  ESP32 + MPU-6050 + piezo/LM358 + buzzer
  reads own sensors
  receives Node 2/3 packets into ring buffer
  posts all readings to backend HTTP endpoint
  uses backend response alert to drive buzzer
```

## Pin map

| Function | ESP32 pin | Applies to | Notes |
|---|---:|---|---|
| MPU-6050 SDA | GPIO 21 | all nodes | I2C data |
| MPU-6050 SCL | GPIO 22 | all nodes | I2C clock |
| Piezo/LM358 ADC output | GPIO 34 | all nodes | input-only ADC pin |
| Active buzzer | GPIO 18 | gateway only | through 1k resistor |
| Onboard LED | GPIO 2 | all firmware | status blink |
| MPU I2C address | `0x68` | all nodes | AD0 to GND |
| Sensor power | 3.3V | all nodes | guide warns not to power MPU from 5V |
| Optional battery input | VIN | all nodes | via MT3608 set to 5.0V |

## Sensor node environments

`D:/URBANPULSE/sensor_node/platformio.ini` now has:

```ini
[env:node2]
upload_port = COM12
build_flags = -DNODE_ID=2

[env:node3]
upload_port = COM11
build_flags = -DNODE_ID=3

[env:esp32dev]
upload_port = COM12
build_flags = -DNODE_ID=2
```

Use `node2` and `node3` for explicit builds/flashes. The `esp32dev` env remains only for compatibility.

## Sensor processing

Firmware uses:

- `SAMPLES = 512`
- MPU sample rate: `1000 Hz`
- Piezo sample rate: `5000 Hz`
- Hamming window
- `arduinoFFT@1.6.0`

MPU vector vibration magnitude:

```cpp
x = rawX / 8192.0;
y = rawY / 8192.0;
z = rawZ / 8192.0 - 1.0;
mag = sqrt(x*x + y*y + z*z);
```

Piezo voltage:

```cpp
voltage = analogRead(GPIO34) * (3.3 / 4095.0);
```

## ESP-NOW packet contract

Defined in both sender and gateway firmware:

```cpp
typedef struct SensorPacket {
  uint8_t  nodeId;
  float    mpuDominantFreq;
  float    mpuPeakAmplitude;
  float    mpuSpectralCentroid;
  float    piezoDominantFreq;
  float    piezoPeakAmplitude;
  float    piezoSpectralCentroid;
  float    mpuRMS;
  float    piezoRMS;
  uint32_t timestamp;
} SensorPacket;
```

## Gateway queue behavior

`pio_gateway/src/gateway_node.ino` now uses a small ESP-NOW receive ring buffer:

```cpp
#define INCOMING_QUEUE_SIZE 8
```

The receive callback only copies packets into the queue. HTTP posting happens later in `loop()`. This avoids doing network work inside the ESP-NOW callback and reduces overwrite loss when Node 2 and Node 3 report while the gateway is sampling/posting.

The loop processes up to 3 queued packets per cycle and logs dropped packets if the queue overflows.

## HTTP payload contract

Gateway posts flat JSON to backend:

```json
{
  "node_id": 1,
  "mpu_dominant_freq": 12.34,
  "mpu_peak_amplitude": 0.0321,
  "mpu_spectral_centroid": 18.75,
  "piezo_dominant_freq": 340.2,
  "piezo_peak_amplitude": 1.24,
  "piezo_spectral_centroid": 410.5,
  "mpu_rms": 0.1234,
  "piezo_rms": 0.5678,
  "timestamp": 123456
}
```

Backend returns:

```json
{
  "status": "ok",
  "alert": "NORMAL"
}
```

Gateway buzzer mapping:

- `NORMAL`: silence
- `WARNING`: one long ~500ms pulse
- `CRITICAL`: three short ~200ms pulses

## Hardcoded values to watch

- Gateway node `NODE_ID` is `1`.
- Gateway MAC in sensor firmware: `C0:CD:D6:84:87:10`.
- Firmware WiFi credentials are hardcoded.
- `pio_gateway/src/gateway_node.ino` posts to `http://172.20.10.3:8001/api/sensor-data`.
- Root `gateway_node/gateway_node.ino` is legacy and may still point to `:8000`.

## Firmware risks

1. **Real hardware not tested in this pass:** builds pass, but flashing/serial/live sensor values still need physical verification.
2. **Duplicate gateway code:** `pio_gateway/` and root `gateway_node/` differ. Treat `pio_gateway` as canonical.
3. **Effective sampling interval:** comments say ~500ms, but 512 MPU samples + 512 piezo samples + HTTP can exceed that under real conditions.
4. **Calibration risk:** backend divides FFT magnitudes/RMS by `138.24`; thresholds must be calibrated against real hardware output.
5. **Credential safety:** WiFi credentials/IP/MAC are hardcoded; avoid exposing publicly.
