// Copie para config.h e preencha com os dados da rede. O config.h não vai para o git.
#pragma once

const char* WIFI_SSID = "network-name";
const char* WIFI_PASSWORD = "network-password";

const char* DEVICE_ID = "esp32-rack01";

const char* MQTT_HOST = "broker.hivemq.com";
const char* MQTT_BACKUP_HOST = "broker.emqx.io";
const uint16_t MQTT_PORT = 1883;

const char* INTERNET_CHECK_HOST = "example.com";
