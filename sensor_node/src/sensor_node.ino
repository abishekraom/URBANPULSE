/*
 * UrbanPulse — Sensor Node Firmware
 * Runs on Node 2 and Node 3 (sender nodes)
 * 
 * Compatible with:
 *   - ESP32 Arduino Core v2.x (Board: "ESP32 Dev Module")
 *   - arduinoFFT v1.6.x (Install from Library Manager)
 *
 * Hardware per node:
 *   - ESP32 DevKit v1
 *   - MPU-6050 (GY-521) on I2C
 *   - Piezoelectric disc via LM358 charge amplifier on ADC
 *   - LiPo 3.7V → TP4056 → MT3608 (5V) → ESP32 VIN (or USB for testing)
 *
 * Sends FFT features to Gateway (Node 1) via ESP-NOW
 */

#include <Wire.h>
#include <esp_now.h>
#include <WiFi.h>
#include "arduinoFFT.h"

// ─── PIN DEFINITIONS ───────────────────────────────────
#define MPU_SDA        21    // I2C SDA → MPU-6050 SDA
#define MPU_SCL        22    // I2C SCL → MPU-6050 SCL
#define PIEZO_ADC_PIN  34    // ADC input from LM358 output
#define ONBOARD_LED    2     // ESP32 onboard LED (status)

// ─── MPU-6050 I2C ADDRESS ──────────────────────────────
#define MPU_ADDR       0x68

// ─── FFT CONFIGURATION ────────────────────────────────
#define SAMPLES        512   // Must be power of 2
#define SAMPLING_FREQ  1000  // Hz — 1kHz for accelerometer
#define PIEZO_SAMPLING_FREQ 5000 // Hz — 5kHz for piezo (acoustic)

// ─── NODE IDENTITY ─────────────────────────────────────
// NODE_ID is supplied by PlatformIO build flags.
//   pio run -e node2 → NODE_ID=2
//   pio run -e node3 → NODE_ID=3
#ifndef NODE_ID
#define NODE_ID        2
#endif

// ─── WIFI (connect for ESP-NOW channel sync with gateway) ──
const char* SENSOR_WIFI_SSID     = "DaEL";
const char* SENSOR_WIFI_PASSWORD="11228866";

// ─── GATEWAY MAC ADDRESS ──────────────────────────────
// Gateway Node 1 MAC determined at runtime
uint8_t gatewayMAC[] = {0xC0, 0xCD, 0xD6, 0x84, 0x87, 0x10};

// ─── DATA STRUCTURES ──────────────────────────────────
typedef struct SensorPacket {
  uint8_t  nodeId;
  // MPU-6050 FFT features
  float    mpuDominantFreq;
  float    mpuPeakAmplitude;
  float    mpuSpectralCentroid;
  // Piezo FFT features
  float    piezoDominantFreq;
  float    piezoPeakAmplitude;
  float    piezoSpectralCentroid;
  // Raw RMS values
  float    mpuRMS;
  float    piezoRMS;
  uint32_t timestamp;
} SensorPacket;

// ─── FFT ARRAYS ────────────────────────────────────────
double vRealMPU[SAMPLES];
double vImagMPU[SAMPLES];
double vRealPiezo[SAMPLES];
double vImagPiezo[SAMPLES];

// arduinoFFT v1.x — no template, just use the class directly
arduinoFFT FFT_MPU = arduinoFFT(vRealMPU, vImagMPU, SAMPLES, SAMPLING_FREQ);
arduinoFFT FFT_Piezo = arduinoFFT(vRealPiezo, vImagPiezo, SAMPLES, PIEZO_SAMPLING_FREQ);

// ─── ESP-NOW CALLBACK ──────────────────────────────────
esp_now_peer_info_t peerInfo;
bool sendSuccess = false;

void onDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  sendSuccess = (status == ESP_NOW_SEND_SUCCESS);
  Serial.println(sendSuccess ? ">> Send OK" : ">> Send FAIL");
}

// ─── MPU-6050 FUNCTIONS ────────────────────────────────
void initMPU6050() {
  Wire.begin(MPU_SDA, MPU_SCL);
  Wire.setClock(400000); // 400kHz I2C fast mode

  // Wake up MPU-6050
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); // PWR_MGMT_1 register
  Wire.write(0x00); // Wake up (clear sleep bit)
  Wire.endTransmission(true);

  // Set accelerometer to ±4g range
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1C); // ACCEL_CONFIG register
  Wire.write(0x08); // ±4g
  Wire.endTransmission(true);

  // Set gyroscope to ±500°/s (optional, for extra data)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1B); // GYRO_CONFIG register
  Wire.write(0x08); // ±500°/s
  Wire.endTransmission(true);

  Serial.println("[MPU] Initialized at 0x68");
}

// Read all 3 acceleration axes, subtract gravity from Z, return vector magnitude
// This captures vibration in any direction without signal dilution
float readMPU_XYZ() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B); // ACCEL_XOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)MPU_ADDR, (size_t)6, true);

  int16_t rawX = (Wire.read() << 8) | Wire.read();
  int16_t rawY = (Wire.read() << 8) | Wire.read();
  int16_t rawZ = (Wire.read() << 8) | Wire.read();

  float x = rawX / 8192.0;        // g-force
  float y = rawY / 8192.0;        // g-force
  float z = rawZ / 8192.0 - 1.0;  // g-force, gravity removed

  // Vector magnitude of vibration-only components
  return sqrt(x*x + y*y + z*z);
}

// ─── SAMPLING & FFT ────────────────────────────────────
void sampleAndProcessMPU(SensorPacket &pkt) {
  unsigned long samplingPeriod_us = 1000000UL / SAMPLING_FREQ;

  // Collect samples
  for (int i = 0; i < SAMPLES; i++) {
    unsigned long t0 = micros();
    vRealMPU[i] = readMPU_XYZ();
    vImagMPU[i] = 0.0;
    while (micros() - t0 < samplingPeriod_us); // Wait for next sample
  }

  // Compute FFT (arduinoFFT v1.x method names)
  FFT_MPU.Windowing(FFT_WIN_TYP_HAMMING, FFT_FORWARD);
  FFT_MPU.Compute(FFT_FORWARD);
  FFT_MPU.ComplexToMagnitude();

  // Extract features from first half of spectrum (real frequencies)
  double maxAmp = 0;
  int maxIndex = 0;
  double weightedSum = 0;
  double totalAmp = 0;
  double sumSquares = 0;

  for (int i = 1; i < SAMPLES / 2; i++) { // Skip DC (index 0)
    double amp = vRealMPU[i];
    double freq = (i * 1.0 * SAMPLING_FREQ) / SAMPLES;

    if (amp > maxAmp) {
      maxAmp = amp;
      maxIndex = i;
    }
    weightedSum += freq * amp;
    totalAmp += amp;
    sumSquares += amp * amp;
  }

  pkt.mpuDominantFreq    = (maxIndex * 1.0 * SAMPLING_FREQ) / SAMPLES;
  pkt.mpuPeakAmplitude   = maxAmp;
  pkt.mpuSpectralCentroid = (totalAmp > 0) ? (weightedSum / totalAmp) : 0;
  pkt.mpuRMS = sqrt(sumSquares / (SAMPLES / 2));
}

void sampleAndProcessPiezo(SensorPacket &pkt) {
  unsigned long samplingPeriod_us = 1000000UL / PIEZO_SAMPLING_FREQ;

  // Collect samples from ADC
  for (int i = 0; i < SAMPLES; i++) {
    unsigned long t0 = micros();
    vRealPiezo[i] = analogRead(PIEZO_ADC_PIN) * (3.3 / 4095.0); // Convert to volts
    vImagPiezo[i] = 0.0;
    while (micros() - t0 < samplingPeriod_us);
  }

  // Compute FFT (arduinoFFT v1.x method names)
  FFT_Piezo.Windowing(FFT_WIN_TYP_HAMMING, FFT_FORWARD);
  FFT_Piezo.Compute(FFT_FORWARD);
  FFT_Piezo.ComplexToMagnitude();

  // Extract features
  double maxAmp = 0;
  int maxIndex = 0;
  double weightedSum = 0;
  double totalAmp = 0;
  double sumSquares = 0;

  for (int i = 1; i < SAMPLES / 2; i++) {
    double amp = vRealPiezo[i];
    double freq = (i * 1.0 * PIEZO_SAMPLING_FREQ) / SAMPLES;

    if (amp > maxAmp) {
      maxAmp = amp;
      maxIndex = i;
    }
    weightedSum += freq * amp;
    totalAmp += amp;
    sumSquares += amp * amp;
  }

  pkt.piezoDominantFreq    = (maxIndex * 1.0 * PIEZO_SAMPLING_FREQ) / SAMPLES;
  pkt.piezoPeakAmplitude   = maxAmp;
  pkt.piezoSpectralCentroid = (totalAmp > 0) ? (weightedSum / totalAmp) : 0;
  pkt.piezoRMS = sqrt(sumSquares / (SAMPLES / 2));
}

// ─── SETUP ─────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.printf("\n[UrbanPulse] Sensor Node %d starting...\n", NODE_ID);

  pinMode(ONBOARD_LED, OUTPUT);
  pinMode(PIEZO_ADC_PIN, INPUT);
  analogReadResolution(12); // 12-bit ADC (0-4095)
  analogSetAttenuation(ADC_11db); // Full 0-3.3V range

  // Init MPU-6050
  initMPU6050();

  // Init WiFi in station mode and connect (for ESP-NOW channel sync)
  WiFi.mode(WIFI_STA);
  WiFi.begin(SENSOR_WIFI_SSID, SENSOR_WIFI_PASSWORD);
  Serial.printf("[WiFi] Connecting to %s", SENSOR_WIFI_SSID);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 10) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  Serial.println(WiFi.status() == WL_CONNECTED ? " OK" : " FAIL");
  Serial.printf("[WiFi] MAC: %s\n", WiFi.macAddress().c_str());

  // Init ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("[ESP-NOW] Init FAILED!");
    return;
  }
  esp_now_register_send_cb(onDataSent);

  // Register gateway peer
  memcpy(peerInfo.peer_addr, gatewayMAC, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("[ESP-NOW] Failed to add gateway peer!");
  }

  Serial.println("[UrbanPulse] Node ready. Sampling...\n");
}

// ─── MAIN LOOP ─────────────────────────────────────────
void loop() {
  SensorPacket pkt;
  pkt.nodeId = NODE_ID;
  pkt.timestamp = millis();

  // Blink LED during sampling
  digitalWrite(ONBOARD_LED, HIGH);

  // Sample & FFT for MPU-6050
  sampleAndProcessMPU(pkt);

  // Sample & FFT for Piezo
  sampleAndProcessPiezo(pkt);

  digitalWrite(ONBOARD_LED, LOW);

  // Print to Serial for debugging
  Serial.printf("[Node %d] MPU  -> Freq: %.1f Hz | Amp: %.4f | Centroid: %.1f Hz | RMS: %.4f\n",
    NODE_ID, pkt.mpuDominantFreq, pkt.mpuPeakAmplitude,
    pkt.mpuSpectralCentroid, pkt.mpuRMS);
  Serial.printf("[Node %d] Piezo-> Freq: %.1f Hz | Amp: %.4f | Centroid: %.1f Hz | RMS: %.4f\n",
    NODE_ID, pkt.piezoDominantFreq, pkt.piezoPeakAmplitude,
    pkt.piezoSpectralCentroid, pkt.piezoRMS);

  // Send via ESP-NOW
  esp_err_t result = esp_now_send(gatewayMAC, (uint8_t *)&pkt, sizeof(pkt));
  if (result != ESP_OK) {
    Serial.println("[ESP-NOW] Send error");
  }

  // Wait ~500ms between readings (adjust as needed)
  delay(500);
}
