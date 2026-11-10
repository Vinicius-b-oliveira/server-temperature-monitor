#include <Arduino.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <DHT.h>
#include "config.h"
#include "pins.h"
#include "sensors.h"

const unsigned long DS18B20_INTERVAL_MS = 1000;
const unsigned long DHT_INTERVAL_MS = 2000;

OneWire oneWire(PIN_DS18B20);
DallasTemperature ds18b20(&oneWire);
DHT dht(PIN_DHT, DHT_TYPE);

unsigned long lastDsMs = 0;
unsigned long lastDhtMs = 0;

void sensorsBegin() {
  ds18b20.begin();
  ds18b20.setWaitForConversion(false);
  ds18b20.requestTemperatures();
  dht.begin();
  lastDsMs = millis();
}

// DS18B20: lê a conversão pedida no ciclo anterior e já pede a próxima
float readDs18b20() {
  float value = ds18b20.getTempCByIndex(0);
  ds18b20.requestTemperatures();
  // -127: sem resposta. 85: antes da primeira conversão
  if (value == DEVICE_DISCONNECTED_C || value == 85.0) {
    return NAN;
  }
  return value;
}

bool sensorsUpdate(unsigned long now, Readings& readings) {
  bool fresh = false;

  if (now - lastDsMs >= DS18B20_INTERVAL_MS) {
    lastDsMs = now;
    readings.dsTempC = readDs18b20();
    readings.ldrRaw = analogRead(PIN_LDR);
    readings.lidOpen = readings.ldrRaw < LDR_OPEN_THRESHOLD;
    if (PRIMARY_SENSOR == SENSOR_DS18B20) {
      readings.tempC = readings.dsTempC;
      fresh = true;
    }
  }

  // DHT: no mínimo 2 s entre leituras
  if (now - lastDhtMs >= DHT_INTERVAL_MS) {
    lastDhtMs = now;
    readings.dhtTempC = dht.readTemperature();
    readings.humidity = dht.readHumidity();
    if (PRIMARY_SENSOR == SENSOR_DHT) {
      readings.tempC = readings.dhtTempC;
      fresh = true;
    }
  }

  return fresh;
}
