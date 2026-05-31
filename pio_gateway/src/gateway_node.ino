/*
 * UrbanPulse — Gateway Node Firmware (Node 1)
 * FULL MODE — WiFi + FastAPI Backend + ESP-NOW Mesh
 * 
 * Compatible with:
 *   - ESP32 Arduino Core v2.x (Board: "ESP32 Dev Module")
 *   - arduinoFFT v1.6.x
 *
 * What this does:
 *   1. Reads its own MPU-6050 + Piezo sensors
 *   2. Receives ESP-NOW data from Node 2 and Node 3
 *   3. Sends ALL data to FastAPI server via HTTP POST
 *   4. Receives alert commands from server response
 *   5. Buzzer alert if ANY node gives a high reading
 *   6. Prints CSV to Serial for backup logging
 *
 * Libraries needed (install via Library Manager):
 *   - arduinoFFT by Enrique Condes
 *   - HTTPClient (built into ESP32 Arduino Core)
 *
 * Hardware:
 *   - ESP32 DevKit v1
 *   - MPU-6050 (GY-521) on I2C (SDA->21, SCL->22)
 *   - Piezo disc via LM358 on GPIO 34
 *   - Active buzzer on GPIO 18 (via 1k ohm resistor)
 */

#include <Wire.h>
#include <WiFi.h>
#include <esp_now.h>
#include <HTTPClient.h>
#include "arduinoFFT.h"

// ─── WiFi CONFIGURATION ──────────────────────────────
const char* WIFI_SSID     = "DaEL";
const char* WIFI_PASSWORD = "11228866";

// ─── FastAPI SERVER ───────────────────────────────────
const char* SERVER_URL = "http://172.20.10.3:8001/api/sensor-data";

// ─── PIN DEFINITIONS ───────────────────────────────────
#define MPU_SDA        21
#define MPU_SCL        22
#define PIEZO_ADC_PIN  34
#define BUZZER_PIN     18    // Active buzzer (via 1k ohm resistor per pin_connections.txt)
#define ONBOARD_LED    2

// ─── MPU-6050 ──────────────────────────────────────────
#define MPU_ADDR 0x68

// ─── FFT ───────────────────────────────────────────────
#define SAMPLES        512
#define SAMPLING_FREQ  1000
#define PIEZO_SAMPLING_FREQ 5000
#define NODE_ID        1

// ─── SIMPLE THRESHOLDS (adjust after testing) ─────────
#define MPU_RMS_WARNING_THRESHOLD    0.15
#define PIEZO_RMS_WARNING_THRESHOLD  0.5

// ─── DATA STRUCTURE (must match sensor_node) ──────────
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

// ─── GLOBALS ───────────────────────────────────────────

double vRealMPU[SAMPLES], vImagMPU[SAMPLES];
double vRealPiezo[SAMPLES], vImagPiezo[SAMPLES];

// arduinoFFT v1.x
arduinoFFT FFT_MPU = arduinoFFT(vRealMPU, vImagMPU, SAMPLES, SAMPLING_FREQ);
arduinoFFT FFT_Piezo = arduinoFFT(vRealPiezo, vImagPiezo, SAMPLES, PIEZO_SAMPLING_FREQ);

// Alert state
enum AlertLevel { NORMAL, WARNING, CRITICAL };
AlertLevel currentAlert = NORMAL;
unsigned long alertStartTime = 0;

// WiFi state
bool wifiConnected = false;
unsigned long lastWifiAttempt = 0;
#define WIFI_RETRY_INTERVAL 10000 // retry WiFi every 10s if disconnected

// HTTP state
unsigned long lastHTTPSend = 0;
bool httpBusy = false;  // Prevent re-entrant HTTP calls

// ESP-NOW incoming packet buffer
SensorPacket incomingPkt;
volatile bool hasIncomingPkt = false;

// ─── WiFi FUNCTIONS ───────────────────────────────────
void connectWiFi() {
  Serial.printf("# [WiFi] Connecting to %s", WIFI_SSID);
  
  // Set WiFi to STA mode — ESP-NOW requires this
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    Serial.printf("\n# [WiFi] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("# [WiFi] Channel: %d\n", WiFi.channel());
  } else {
    wifiConnected = false;
    Serial.println("\n# [WiFi] Connection failed! Will retry...");
    Serial.println("# [WiFi] ESP-NOW still works without WiFi");
  }
}

void checkWiFi() {
  if (WiFi.status() != WL_CONNECTED) {
    wifiConnected = false;
    if (millis() - lastWifiAttempt > WIFI_RETRY_INTERVAL) {
      lastWifiAttempt = millis();
      Serial.println("# [WiFi] Reconnecting...");
      WiFi.reconnect();
      delay(2000);
      if (WiFi.status() == WL_CONNECTED) {
        wifiConnected = true;
        Serial.println("# [WiFi] Reconnected!");
      }
    }
  } else {
    wifiConnected = true;
  }
}

// ─── HTTP POST TO SERVER ──────────────────────────────
void sendToServer(SensorPacket &pkt) {
  if (!wifiConnected) return;
  if (httpBusy) {
    Serial.println("# [HTTP] Skipped — busy");
    return;
  }
  httpBusy = true;
  
  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(2000); // 2 second timeout — don't block too long
  
  // Build JSON manually (avoids needing ArduinoJson library)
  char json[512];
  snprintf(json, sizeof(json),
    "{"
    "\"node_id\":%d,"
    "\"mpu_dominant_freq\":%.2f,"
    "\"mpu_peak_amplitude\":%.4f,"
    "\"mpu_spectral_centroid\":%.2f,"
    "\"piezo_dominant_freq\":%.2f,"
    "\"piezo_peak_amplitude\":%.4f,"
    "\"piezo_spectral_centroid\":%.2f,"
    "\"mpu_rms\":%.4f,"
    "\"piezo_rms\":%.4f,"
    "\"timestamp\":%lu"
    "}",
    pkt.nodeId,
    pkt.mpuDominantFreq,
    pkt.mpuPeakAmplitude,
    pkt.mpuSpectralCentroid,
    pkt.piezoDominantFreq,
    pkt.piezoPeakAmplitude,
    pkt.piezoSpectralCentroid,
    pkt.mpuRMS,
    pkt.piezoRMS,
    pkt.timestamp
  );
  
  int httpCode = http.POST(json);
  
  if (httpCode > 0) {
    String response = http.getString();
    
    // Parse alert level from server response
    // Server returns: {"status":"ok","alert":"NORMAL"} or "WARNING" or "CRITICAL"
    if (response.indexOf("\"CRITICAL\"") >= 0) {
      if (currentAlert != CRITICAL) {
        triggerAlert(CRITICAL);
      }
    } else if (response.indexOf("\"WARNING\"") >= 0) {
      if (currentAlert < WARNING) {
        triggerAlert(WARNING);
      }
    }
    // NORMAL doesn't override — let the timeout handle de-escalation
    
  } else {
    Serial.printf("# [HTTP] POST failed: %s\n", http.errorToString(httpCode).c_str());
    httpBusy = false;
  }
  
  http.end();
  httpBusy = false;
}

// ─── ESP-NOW RECEIVE CALLBACK ──────────────────────────
void onDataReceived(const uint8_t *mac_addr, const uint8_t *data, int len) {
  if (len == sizeof(SensorPacket)) {
    // Buffer the packet — don't HTTP POST from interrupt context
    memcpy(&incomingPkt, data, sizeof(incomingPkt));
    hasIncomingPkt = true;
  }
}

// ─── DATA LOGGING (CSV format to Serial) ──────────────
void printDataCSV(SensorPacket &pkt) {
  // CSV format: timestamp, nodeId, mpuFreq, mpuAmp, mpuCentroid, mpuRMS, piezoFreq, piezoAmp, piezoCentroid, piezoRMS
  Serial.printf("%lu,%d,%.2f,%.4f,%.2f,%.4f,%.2f,%.4f,%.2f,%.4f\n",
    pkt.timestamp,
    pkt.nodeId,
    pkt.mpuDominantFreq,
    pkt.mpuPeakAmplitude,
    pkt.mpuSpectralCentroid,
    pkt.mpuRMS,
    pkt.piezoDominantFreq,
    pkt.piezoPeakAmplitude,
    pkt.piezoSpectralCentroid,
    pkt.piezoRMS
  );
}

// ─── SIMPLE THRESHOLD ALERTS (replaces ML) ────────────
void checkThresholds(SensorPacket &pkt) {
  AlertLevel level = NORMAL;

  // Check MPU RMS (vibration intensity)
  if (pkt.mpuRMS > MPU_RMS_WARNING_THRESHOLD * 2) {
    level = CRITICAL;
  } else if (pkt.mpuRMS > MPU_RMS_WARNING_THRESHOLD) {
    level = WARNING;
  }

  // Check Piezo RMS (acoustic intensity)
  if (pkt.piezoRMS > PIEZO_RMS_WARNING_THRESHOLD * 2) {
    level = CRITICAL;
  } else if (pkt.piezoRMS > PIEZO_RMS_WARNING_THRESHOLD && level < WARNING) {
    level = WARNING;
  }

  // Only update alert if severity increased
  if (level > currentAlert) {
    triggerAlert(level);
  }
}

// ─── ALERT SYSTEM (Buzzer Only) ────────────────────────
void triggerAlert(AlertLevel level) {
  currentAlert = level;
  alertStartTime = millis();

  switch (level) {
    case CRITICAL:
      Serial.println("# ALERT: CRITICAL - BUZZER");
      buzzPattern(3, 200);       // 3 short pulses
      break;
    case WARNING:
      Serial.println("# ALERT: WARNING - BUZZER");
      buzzPattern(1, 500);         // 1 long pulse
      break;
    case NORMAL:
      Serial.println("# ALERT: NORMAL");
      break;
  }
}

void buzzPattern(int pulses, int durationMs) {
  for (int i = 0; i < pulses; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(durationMs);
    digitalWrite(BUZZER_PIN, LOW);
    if (i < pulses - 1) delay(150);
  }
}

// ─── MPU-6050 ──────────────────────────────────────────
void initMPU6050() {
  Wire.begin(MPU_SDA, MPU_SCL);
  Wire.setClock(400000);

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);
  Wire.write(0x00);
  Wire.endTransmission(true);

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1C);
  Wire.write(0x08); // +/-4g
  Wire.endTransmission(true);

  Serial.println("# [MPU] Initialized");
}

// Read all 3 acceleration axes, subtract gravity from Z, return vector magnitude
float readMPU_XYZ() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 6, true);

  int16_t rawX = (Wire.read() << 8) | Wire.read();
  int16_t rawY = (Wire.read() << 8) | Wire.read();
  int16_t rawZ = (Wire.read() << 8) | Wire.read();

  float x = rawX / 8192.0;
  float y = rawY / 8192.0;
  float z = rawZ / 8192.0 - 1.0;

  return sqrt(x*x + y*y + z*z);
}

// ─── OWN SENSOR SAMPLING ──────────────────────────────
void sampleOwnSensors() {
  SensorPacket pkt;
  pkt.nodeId = NODE_ID;
  pkt.timestamp = millis();

  // MPU FFT
  unsigned long period_us = 1000000UL / SAMPLING_FREQ;
  for (int i = 0; i < SAMPLES; i++) {
    unsigned long t0 = micros();
    vRealMPU[i] = readMPU_XYZ();
    vImagMPU[i] = 0.0;
    while (micros() - t0 < period_us);
  }
  FFT_MPU.Windowing(FFT_WIN_TYP_HAMMING, FFT_FORWARD);
  FFT_MPU.Compute(FFT_FORWARD);
  FFT_MPU.ComplexToMagnitude();

  double maxAmp = 0; int maxIdx = 0;
  double wSum = 0, tAmp = 0, sSq = 0;
  for (int i = 1; i < SAMPLES/2; i++) {
    double a = vRealMPU[i];
    double f = (i * 1.0 * SAMPLING_FREQ) / SAMPLES;
    if (a > maxAmp) { maxAmp = a; maxIdx = i; }
    wSum += f * a; tAmp += a; sSq += a * a;
  }
  pkt.mpuDominantFreq    = (maxIdx * 1.0 * SAMPLING_FREQ) / SAMPLES;
  pkt.mpuPeakAmplitude   = maxAmp;
  pkt.mpuSpectralCentroid = tAmp > 0 ? wSum / tAmp : 0;
  pkt.mpuRMS = sqrt(sSq / (SAMPLES/2));

  // Piezo FFT
  period_us = 1000000UL / PIEZO_SAMPLING_FREQ;
  for (int i = 0; i < SAMPLES; i++) {
    unsigned long t0 = micros();
    vRealPiezo[i] = analogRead(PIEZO_ADC_PIN) * (3.3 / 4095.0);
    vImagPiezo[i] = 0.0;
    while (micros() - t0 < period_us);
  }
  FFT_Piezo.Windowing(FFT_WIN_TYP_HAMMING, FFT_FORWARD);
  FFT_Piezo.Compute(FFT_FORWARD);
  FFT_Piezo.ComplexToMagnitude();

  maxAmp = 0; maxIdx = 0; wSum = 0; tAmp = 0; sSq = 0;
  for (int i = 1; i < SAMPLES/2; i++) {
    double a = vRealPiezo[i];
    double f = (i * 1.0 * PIEZO_SAMPLING_FREQ) / SAMPLES;
    if (a > maxAmp) { maxAmp = a; maxIdx = i; }
    wSum += f * a; tAmp += a; sSq += a * a;
  }
  pkt.piezoDominantFreq    = (maxIdx * 1.0 * PIEZO_SAMPLING_FREQ) / SAMPLES;
  pkt.piezoPeakAmplitude   = maxAmp;
  pkt.piezoSpectralCentroid = tAmp > 0 ? wSum / tAmp : 0;
  pkt.piezoRMS = sqrt(sSq / (SAMPLES/2));

  // Print own data
  printDataCSV(pkt);

  // Check own thresholds
  checkThresholds(pkt);
  
  // Send to server
  sendToServer(pkt);
}

// ─── SETUP ─────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(1000);

  // Print header
  Serial.println("# UrbanPulse Gateway — Full Mode (WiFi + FastAPI)");
  Serial.println("# timestamp,nodeId,mpuFreq,mpuAmp,mpuCentroid,mpuRMS,piezoFreq,piezoAmp,piezoCentroid,piezoRMS");

  // Pin setup
  pinMode(ONBOARD_LED, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(PIEZO_ADC_PIN, INPUT);
  digitalWrite(BUZZER_PIN, LOW);
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);

  // Init MPU-6050
  initMPU6050();

  // Connect to WiFi (also sets STA mode needed for ESP-NOW)
  connectWiFi();
  
  // Print MAC address (needed for sensor nodes)
  Serial.printf("# [WiFi] Gateway MAC: %s\n", WiFi.macAddress().c_str());

  // Init ESP-NOW (works alongside WiFi on the same channel)
  if (esp_now_init() != ESP_OK) {
    Serial.println("# [ESP-NOW] Init failed!");
    return;
  }
  esp_now_register_recv_cb(onDataReceived);
  Serial.println("# [ESP-NOW] Listening for sensor nodes...");

  Serial.println("# Gateway ready! Sending data to FastAPI server...\n");
}

// ─── MAIN LOOP ─────────────────────────────────────────
unsigned long lastOwnSample = 0;

void loop() {
  // Check WiFi connection
  checkWiFi();
  
  // Process any buffered ESP-NOW packets (not in interrupt context)
  if (hasIncomingPkt) {
    hasIncomingPkt = false;
    if (incomingPkt.nodeId >= 1 && incomingPkt.nodeId <= 3) {
      printDataCSV(incomingPkt);
      checkThresholds(incomingPkt);
      sendToServer(incomingPkt);
    }
  }
  
  // Sample own sensors every 500ms
  if (millis() - lastOwnSample > 500) {
    lastOwnSample = millis();
    
    // Blink LED during sampling
    digitalWrite(ONBOARD_LED, HIGH);
    sampleOwnSensors();
    digitalWrite(ONBOARD_LED, LOW);
  }

  // Auto-reset alert to NORMAL after 10 seconds
  if (currentAlert != NORMAL && millis() - alertStartTime > 10000) {
    triggerAlert(NORMAL);
  }

  delay(10);
}
