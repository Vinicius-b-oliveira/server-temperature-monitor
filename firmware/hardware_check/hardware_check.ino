// Teste de hardware sem rede: lê cada sensor e aciona cada atuador.
#include <OneWire.h>
#include <DallasTemperature.h>
#include <DHT.h>
#include "pins.h"

// DHT22 no Wokwi, DHT11 na bancada
const uint8_t DHT_TYPE = DHT22;

const unsigned long STATUS_INTERVAL_MS = 1000;
const unsigned long DHT_INTERVAL_MS = 2000;
const unsigned long COLOR_INTERVAL_MS = 2000;
const unsigned int BEEP_HZ = 2000;
const unsigned long BEEP_MS = 200;

const char* COLOR_NAMES[] = {"green", "yellow", "red", "blue"};
const int COLOR_COUNT = 4;

OneWire oneWire(PIN_DS18B20);
DallasTemperature ds18b20(&oneWire);
DHT dht(PIN_DHT, DHT_TYPE);

float tempC = NAN;
float dhtTempC = NAN;
float humidity = NAN;
int colorIndex = 0;
bool buttonWasPressed = false;
bool beeping = false;
unsigned long beepStartMs = 0;
unsigned long lastStatusMs = 0;
unsigned long lastDhtMs = 0;
unsigned long lastColorMs = 0;

// Amarelo é vermelho com verde. O LED da ventoinha acende junto com o vermelho
void showColor(int index) {
  const char* name = COLOR_NAMES[index];
  bool red = strcmp(name, "red") == 0 || strcmp(name, "yellow") == 0;
  bool green = strcmp(name, "green") == 0 || strcmp(name, "yellow") == 0;
  bool blue = strcmp(name, "blue") == 0;
  digitalWrite(PIN_LED_RED, red ? HIGH : LOW);
  digitalWrite(PIN_LED_GREEN, green ? HIGH : LOW);
  digitalWrite(PIN_LED_BLUE, blue ? HIGH : LOW);
  digitalWrite(PIN_FAN, strcmp(name, "red") == 0 ? HIGH : LOW);
}

// Lê o resultado da conversão anterior e já pede a próxima, sem esperar
float readDs18b20() {
  float value = ds18b20.getTempCByIndex(0);
  ds18b20.requestTemperatures();
  // -127 é sensor sem resposta e 85 é o valor de antes da primeira conversão
  if (value == DEVICE_DISCONNECTED_C || value == 85.0) {
    return NAN;
  }
  return value;
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_BLUE, OUTPUT);
  pinMode(PIN_FAN, OUTPUT);
  pinMode(PIN_BUTTON, INPUT_PULLUP);

  ds18b20.begin();
  ds18b20.setWaitForConversion(false);
  ds18b20.requestTemperatures();
  dht.begin();

  Serial.printf("hardware_check started, DS18B20 devices: %d\n", ds18b20.getDeviceCount());
  showColor(colorIndex);
}

void loop() {
  unsigned long now = millis();

  bool buttonPressed = digitalRead(PIN_BUTTON) == LOW;
  if (buttonPressed && !buttonWasPressed) {
    tone(PIN_BUZZER, BEEP_HZ);
    beeping = true;
    beepStartMs = now;
  }
  buttonWasPressed = buttonPressed;

  // Desliga o bipe depois de BEEP_MS sem travar o loop
  if (beeping && now - beepStartMs >= BEEP_MS) {
    noTone(PIN_BUZZER);
    beeping = false;
  }

  if (now - lastColorMs >= COLOR_INTERVAL_MS) {
    lastColorMs = now;
    colorIndex = (colorIndex + 1) % COLOR_COUNT;
    showColor(colorIndex);
  }

  if (now - lastDhtMs >= DHT_INTERVAL_MS) {
    lastDhtMs = now;
    dhtTempC = dht.readTemperature();
    humidity = dht.readHumidity();
  }

  if (now - lastStatusMs >= STATUS_INTERVAL_MS) {
    lastStatusMs = now;
    tempC = readDs18b20();
    Serial.printf("temp_c=%.2f dht_temp_c=%.1f humidity=%.1f ldr_raw=%d button=%s rgb=%s\n",
                  tempC, dhtTempC, humidity, analogRead(PIN_LDR),
                  buttonPressed ? "pressed" : "released", COLOR_NAMES[colorIndex]);
  }
}
