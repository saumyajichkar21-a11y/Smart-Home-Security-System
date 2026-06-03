/*
 * Sentinel ESP32-CAM Firmware
 * Streams video and reads sensor data
 */

#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <esp32cam.h>

// WiFi Credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Pin Definitions
#define PIR_PIN 13
#define MQ2_PIN 34
#define WINDOW_PIN 14
#define RELAY_PIN 12
#define BUZZER_PIN 15
#define LED_PIN 4

// Web Server
AsyncWebServer server(80);
AsyncWebSocket ws("/ws");

// Camera config
using namespace esp32cam;
Resolution resolution = Resolution::find(640, 480);

void setup() {
  Serial.begin(115200);

  // Initialize pins
  pinMode(PIR_PIN, INPUT);
  pinMode(MQ2_PIN, INPUT);
  pinMode(WINDOW_PIN, INPUT_PULLUP);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);

  // Connect WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected");
  Serial.println(WiFi.localIP());

  // Initialize camera
  CameraConfig cfg;
  cfg.setPins(pins::AiThinker);
  cfg.setResolution(resolution);
  cfg.setBufferCount(2);
  cfg.setJpeg(80);

  if (!Camera.begin(cfg)) {
    Serial.println("Camera init failed!");
    return;
  }

  // Setup WebSocket
  ws.onEvent(onWebSocketEvent);
  server.addHandler(&ws);

  // Setup HTTP endpoints
  server.on("/stream", HTTP_GET, handleStream);
  server.on("/telemetry", HTTP_GET, handleTelemetry);

  server.begin();
  Serial.println("Server started");
}

void loop() {
  // Read sensors
  int pirState = digitalRead(PIR_PIN);
  int gasValue = analogRead(MQ2_PIN);
  int windowState = digitalRead(WINDOW_PIN);

  // Convert gas to PPM (simplified)
  int gasPPM = map(gasValue, 0, 4095, 0, 1000);

  // Send telemetry via WebSocket
  String telemetry = "{";
  telemetry += ""timestamp":"" + String(millis()) + "",";
  telemetry += ""pir_motion":" + String(pirState) + ",";
  telemetry += ""mq2_gas_ppm":" + String(gasPPM) + ",";
  telemetry += ""window_intrusion":" + String(windowState == LOW ? 1 : 0);
  telemetry += "}";

  ws.textAll(telemetry);

  // Handle alerts
  if (windowState == LOW) {
    digitalWrite(BUZZER_PIN, HIGH);
    digitalWrite(LED_PIN, HIGH);
  }

  delay(500); // 2Hz update rate
}

void handleStream(AsyncWebServerRequest* request) {
  // MJPEG stream endpoint
}

void handleTelemetry(AsyncWebServerRequest* request) {
  String json = "{";
  json += ""pir":" + String(digitalRead(PIR_PIN)) + ",";
  json += ""gas":" + String(analogRead(MQ2_PIN)) + ",";
  json += ""window":" + String(digitalRead(WINDOW_PIN));
  json += "}";
  request->send(200, "application/json", json);
}

void onWebSocketEvent(AsyncWebSocket* server, AsyncWebSocketClient* client, 
                      AwsEventType type, void* arg, uint8_t* data, size_t len) {
  if (type == WS_EVT_DATA) {
    // Handle commands from server
    String msg = String((char*)data);
    if (msg.indexOf("arm") >= 0) {
      digitalWrite(RELAY_PIN, HIGH);
    } else if (msg.indexOf("disarm") >= 0) {
      digitalWrite(RELAY_PIN, LOW);
      digitalWrite(BUZZER_PIN, LOW);
      digitalWrite(LED_PIN, LOW);
    }
  }
}
