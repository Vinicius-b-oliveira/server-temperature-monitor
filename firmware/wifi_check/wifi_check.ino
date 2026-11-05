// Teste de rede: conecta ao Wi-Fi e verifica se o broker MQTT responde na porta 1883.
#include <WiFi.h>
#include "config.h"

const unsigned long WIFI_TIMEOUT_MS = 20000;
const unsigned long TEST_INTERVAL_MS = 10000;
const int32_t TCP_TIMEOUT_MS = 5000;

unsigned long lastTestMs = 0;
int testCount = 0;

bool connectWifi() {
  Serial.println("Connecting to Wi-Fi");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_TIMEOUT_MS) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.printf("Wi-Fi failed, status %d\n", WiFi.status());
    return false;
  }
  Serial.printf("Wi-Fi connected in %lu ms\n", millis() - start);
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
  Serial.print("Gateway: ");
  Serial.println(WiFi.gatewayIP());
  return true;
}

// Resolve o nome e tenta abrir uma conexão TCP
bool testTcp(const char* host, uint16_t port) {
  IPAddress ip;
  if (!WiFi.hostByName(host, ip)) {
    Serial.printf("DNS %s failed\n", host);
    return false;
  }

  WiFiClient client;
  unsigned long start = millis();
  bool ok = client.connect(ip, port, TCP_TIMEOUT_MS);
  Serial.printf("TCP %s (%s):%u %s in %lu ms\n", host, ip.toString().c_str(), port,
                ok ? "OK" : "FAILED", millis() - start);
  client.stop();
  return ok;
}

void runTests() {
  testCount++;
  Serial.printf("\nTest %d, uptime %lu s\n", testCount, millis() / 1000);

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi lost, reconnecting");
    if (!connectWifi()) {
      return;
    }
  }
  Serial.printf("RSSI: %d dBm\n", WiFi.RSSI());

  bool primaryOk = testTcp(MQTT_HOST, MQTT_PORT);
  bool backupOk = testTcp(MQTT_BACKUP_HOST, MQTT_PORT);

  // Se nenhum broker responde, a porta 80 separa "1883 bloqueada" de "sem internet"
  if (primaryOk || backupOk) {
    Serial.println("Result: MQTT port reachable");
  } else if (testTcp(INTERNET_CHECK_HOST, 80)) {
    Serial.println("Result: internet OK, port 1883 blocked");
  } else {
    Serial.println("Result: no internet access");
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.print("\nwifi_check on ");
  Serial.println(DEVICE_ID);

  connectWifi();
  runTests();
  lastTestMs = millis();
}

void loop() {
  if (millis() - lastTestMs >= TEST_INTERVAL_MS) {
    lastTestMs = millis();
    runTests();
  }
}
