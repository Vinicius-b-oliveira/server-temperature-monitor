// Monitor de temperatura do rack: sensores, estados, atuadores e MQTT
#include <ArduinoJson.h>
#include <Preferences.h>
#include "config.h"
#include "pins.h"
#include "sensors.h"
#include "state_machine.h"
#include "actuators.h"
#include "network.h"

enum Mode { MODE_AUTO, MODE_MANUAL };

const unsigned long STATUS_INTERVAL_MS = 1000;
const unsigned long DEBOUNCE_MS = 50;
const unsigned long TELEMETRY_INTERVAL_MS = 5000;

Readings readings = {NAN, NAN, NAN, NAN, 0, false};
StateMachine machine;
Limits limits = {DEFAULT_WARNING_C, DEFAULT_CRITICAL_C};
bool limitsChanged = false;
Preferences prefs;
Mode mode = MODE_AUTO;
bool manualFanOn = false;
bool silenced = false;
bool fanOn = false;
bool buzzerOn = false;

bool buttonReading = false;
bool buttonPressed = false;
unsigned long buttonChangedMs = 0;
unsigned long lastStatusMs = 0;
unsigned long lastTelemetryMs = 0;
bool publishNow = false;

// Em crítico e em falha a ventoinha liga mesmo no modo manual
bool decideFan() {
  if (!machine.started) {
    return false;
  }
  if (machine.state == STATE_CRITICAL || machine.state == STATE_FAULT) {
    return true;
  }
  if (mode == MODE_MANUAL) {
    return manualFanOn;
  }
  return machine.state == STATE_WARNING;
}

void silenceAlarm(const char* source) {
  silenced = true;
  Serial.printf("alarm silenced by %s\n", source);
}

// Limites aceitos por comando ficam na flash e voltam depois de reiniciar
void loadLimits() {
  prefs.begin("monitor", true);
  float warning = prefs.getFloat("warning", DEFAULT_WARNING_C);
  float critical = prefs.getFloat("critical", DEFAULT_CRITICAL_C);
  prefs.end();
  if (limitsValid(warning, critical)) {
    limits = {warning, critical};
  }
  Serial.printf("limits warning=%.1f critical=%.1f\n", limits.warning, limits.critical);
}

void saveLimits() {
  prefs.begin("monitor", false);
  prefs.putFloat("warning", limits.warning);
  prefs.putFloat("critical", limits.critical);
  prefs.end();
}

bool applyLimits(const char* payload) {
  JsonDocument doc;
  if (deserializeJson(doc, payload)) {
    return false;
  }
  if (!doc["warning"].is<float>() || !doc["critical"].is<float>()) {
    return false;
  }
  float warning = doc["warning"];
  float critical = doc["critical"];
  if (!limitsValid(warning, critical)) {
    return false;
  }
  limits = {warning, critical};
  limitsChanged = true;
  saveLimits();
  return true;
}

// Comandos remotos: só o conteúdo exato é aceito, o resto é ignorado
void handleCommand(const char* name, const char* payload) {
  bool accepted = true;
  if (strcmp(name, "mode") == 0 && strcmp(payload, "auto") == 0) {
    mode = MODE_AUTO;
  } else if (strcmp(name, "mode") == 0 && strcmp(payload, "manual") == 0) {
    mode = MODE_MANUAL;
  } else if (strcmp(name, "fan") == 0 && strcmp(payload, "on") == 0) {
    manualFanOn = true;
  } else if (strcmp(name, "fan") == 0 && strcmp(payload, "off") == 0) {
    manualFanOn = false;
  } else if (strcmp(name, "silence") == 0 && strcmp(payload, "1") == 0) {
    silenceAlarm("command");
  } else if (strcmp(name, "limits") == 0) {
    accepted = applyLimits(payload);
  } else {
    accepted = false;
  }
  if (accepted) {
    publishNow = true;
  }
  Serial.printf("command %s: %s=%s\n", accepted ? "accepted" : "ignored", name, payload);
}

// Botão
void checkButton(unsigned long now) {
  bool reading = digitalRead(PIN_BUTTON) == LOW;
  if (reading != buttonReading) {
    buttonReading = reading;
    buttonChangedMs = now;
  }
  if (now - buttonChangedMs >= DEBOUNCE_MS && reading != buttonPressed) {
    buttonPressed = reading;
    if (buttonPressed) {
      silenceAlarm("button");
    }
  }
}

void printStatus() {
  Serial.printf("temp_c=%.2f dht_temp_c=%.1f humidity=%.0f ldr=%d lid=%s state=%s mode=%s fan=%s buzzer=%s mqtt=%s\n",
                readings.tempC, readings.dhtTempC, readings.humidity, readings.ldrRaw,
                readings.lidOpen ? "open" : "closed", machine.started ? stateName(machine.state) : "starting",
                mode == MODE_AUTO ? "auto" : "manual", fanOn ? "on" : "off", buzzerOn ? "on" : "off",
                mqttConnected() ? "on" : "off");
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  actuatorsBegin();
  sensorsBegin();
  loadLimits();
  Serial.printf("monitor started, primary sensor: %s\n",
                PRIMARY_SENSOR == SENSOR_DS18B20 ? "DS18B20" : "DHT");
  networkBegin(handleCommand);
}

void loop() {
  unsigned long now = millis();

  // Rede primeiro, para um comando recebido valer nesta volta. O controle local segue mesmo sem Wi-Fi ou broker
  networkLoop(now);
  checkButton(now);

  // Estado
  if (sensorsUpdate(now, readings)) {
    State previous = machine.state;
    bool wasStarted = machine.started;
    updateState(machine, readings.tempC, limits);
    if (limitsChanged && !isnan(readings.tempC)) {
      limitsChanged = false;
      recalculateState(machine, readings.tempC, limits);
    }
    if (machine.state != previous || machine.started != wasStarted) {
      // O alarme volta a tocar quando o estado muda
      silenced = false;
      publishNow = true;
      if (wasStarted) {
        Serial.printf("state %s -> %s\n", stateName(previous), stateName(machine.state));
      } else {
        Serial.printf("initial state %s\n", stateName(machine.state));
      }
    }
  }

  fanOn = decideFan();
  buzzerOn = machine.state == STATE_CRITICAL && !silenced;
  updateActuators(now, machine.state, machine.started, fanOn, buzzerOn);

  // Telemetria: a cada 5 s, ou na hora quando o estado muda ou um comando é aceito
  if (machine.started && (publishNow || now - lastTelemetryMs >= TELEMETRY_INTERVAL_MS)) {
    publishNow = false;
    lastTelemetryMs = now;
    publishTelemetry(readings, stateName(machine.state), mode == MODE_AUTO ? "auto" : "manual", fanOn, limits);
  }

  if (now - lastStatusMs >= STATUS_INTERVAL_MS) {
    lastStatusMs = now;
    printStatus();
  }
}
