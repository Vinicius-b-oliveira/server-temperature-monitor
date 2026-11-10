// Configuração usada no Wokwi (sem dados sensíveis)
#pragma once
#include <DHT.h>

// Rede. Em rede aberta, deixe a senha vazia. No Wokwi: "Wokwi-GUEST" sem senha
const char WIFI_SSID[] = "Wokwi-GUEST";
const char WIFI_PASSWORD[] = "";

// MQTT
const char DEVICE_ID[] = "esp32-rack01";
const char MQTT_HOST[] = "broker.hivemq.com";
const uint16_t MQTT_PORT = 1883;
const char TOPIC_PREFIX[] = "thermomon/g2-axr2adzj/rack01/";

// Sensores. Wokwi: DHT22. Bancada: DHT11
const uint8_t DHT_TYPE = DHT22;

// Sem o DS18B20, use SENSOR_DHT como principal
enum PrimarySensor { SENSOR_DS18B20, SENSOR_DHT };
const PrimarySensor PRIMARY_SENSOR = SENSOR_DS18B20;

// Leituras inválidas seguidas até entrar em falha
const int FAULT_READINGS = 3;

// Abaixo deste valor a tampa está aberta (mais luz, leitura menor). No Wokwi, 500 dá cerca de 1500 lux
const int LDR_OPEN_THRESHOLD = 500;

// Limites padrão e faixa aceita por comando
const float DEFAULT_WARNING_C = 27.0;
const float DEFAULT_CRITICAL_C = 32.0;
const float HYSTERESIS_C = 2.0;
const float LIMIT_MIN_C = 20.0;
const float LIMIT_MAX_C = 50.0;
const float LIMIT_MIN_GAP_C = 3.0;
