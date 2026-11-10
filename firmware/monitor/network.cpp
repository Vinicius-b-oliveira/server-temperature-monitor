#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "config.h"
#include "network.h"

const unsigned long WIFI_RETRY_MS = 10000;
const unsigned long MQTT_RETRY_MS = 5000;
const uint16_t MQTT_BUFFER_SIZE = 512;
const size_t MAX_COMMAND_LENGTH = 128;

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
CommandHandler commandHandler = nullptr;
char clientId[32];
bool wifiWasConnected = false;
unsigned long lastWifiAttemptMs = 0;
unsigned long lastMqttAttemptMs = 0;

String topic(const char* suffix) {
  return String(TOPIC_PREFIX) + suffix;
}

// Comandos chegam em <prefixo>cmd/<nome>. O broker é público: o conteúdo é validado em handleCommand
void onMessage(char* topicName, byte* payload, unsigned int length) {
  String name = topicName;
  String prefix = topic("cmd/");
  if (!name.startsWith(prefix)) {
    return;
  }
  if (length >= MAX_COMMAND_LENGTH) {
    Serial.println("command ignored: payload too long");
    return;
  }
  char text[MAX_COMMAND_LENGTH];
  memcpy(text, payload, length);
  text[length] = '\0';
  commandHandler(name.substring(prefix.length()).c_str(), text);
}

void networkBegin(CommandHandler handler) {
  commandHandler = handler;
  snprintf(clientId, sizeof(clientId), "%s-%04x", DEVICE_ID, (unsigned)(esp_random() & 0xffff));

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lastWifiAttemptMs = millis();

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setBufferSize(MQTT_BUFFER_SIZE);
  mqtt.setCallback(onMessage);
  // Sem broker, connect() trava o loop até o timeout
  mqtt.setSocketTimeout(2);
}

void connectMqtt() {
  String statusTopic = topic("status");
  // Last Will: o broker publica "offline" se a conexão cair sem aviso
  if (mqtt.connect(clientId, nullptr, nullptr, statusTopic.c_str(), 0, true, "offline")) {
    mqtt.publish(statusTopic.c_str(), "online", true);
    mqtt.subscribe(topic("cmd/#").c_str());
    Serial.printf("MQTT connected to %s as %s\n", MQTT_HOST, clientId);
  } else {
    Serial.printf("MQTT failed, state %d\n", mqtt.state());
  }
}

void networkLoop(unsigned long now) {
  if (WiFi.status() != WL_CONNECTED) {
    if (wifiWasConnected) {
      wifiWasConnected = false;
      Serial.println("Wi-Fi lost");
    }
    if (now - lastWifiAttemptMs >= WIFI_RETRY_MS) {
      lastWifiAttemptMs = now;
      Serial.println("Wi-Fi reconnecting");
      WiFi.disconnect();
      WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    }
    return;
  }
  if (!wifiWasConnected) {
    wifiWasConnected = true;
    Serial.printf("Wi-Fi connected, IP %s, RSSI %d dBm\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
  }

  if (!mqtt.connected()) {
    if (now - lastMqttAttemptMs >= MQTT_RETRY_MS) {
      lastMqttAttemptMs = now;
      connectMqtt();
    }
    return;
  }
  mqtt.loop();
}

bool mqttConnected() {
  return mqtt.connected();
}

// Leitura que falhou vai como null
void setReading(JsonDocument& doc, const char* key, float value, int decimals) {
  if (isnan(value)) {
    doc[key] = nullptr;
  } else {
    doc[key] = serialized(String(value, decimals));
  }
}

void publishTelemetry(const Readings& readings, const char* state, const char* mode, bool fanOn,
                      const Limits& limits) {
  if (!mqtt.connected()) {
    return;
  }
  JsonDocument doc;
  doc["device"] = DEVICE_ID;
  doc["uptime_s"] = millis() / 1000;
  setReading(doc, "temp_c", readings.tempC, 2);
  setReading(doc, "dht_temp_c", readings.dhtTempC, 1);
  setReading(doc, "humidity_pct", readings.humidity, 0);
  doc["lid_open"] = readings.lidOpen;
  doc["fan_on"] = fanOn;
  doc["state"] = state;
  doc["mode"] = mode;
  setReading(doc, "warning_c", limits.warning, 1);
  setReading(doc, "critical_c", limits.critical, 1);

  char buffer[MQTT_BUFFER_SIZE];
  serializeJson(doc, buffer, sizeof(buffer));
  mqtt.publish(topic("telemetry").c_str(), buffer);
}
