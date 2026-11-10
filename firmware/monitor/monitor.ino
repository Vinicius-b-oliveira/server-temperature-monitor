// Monitor de temperatura do rack: sensores, estados e atuadores
#include "config.h"
#include "pins.h"
#include "sensors.h"
#include "state_machine.h"
#include "actuators.h"

enum Mode { MODE_AUTO, MODE_MANUAL };

const unsigned long STATUS_INTERVAL_MS = 1000;
const unsigned long DEBOUNCE_MS = 50;

Readings readings = {NAN, NAN, NAN, NAN, 0, false};
StateMachine machine;
Limits limits = {DEFAULT_WARNING_C, DEFAULT_CRITICAL_C};
Mode mode = MODE_AUTO;
bool manualFanOn = false;
bool silenced = false;
bool fanOn = false;
bool buzzerOn = false;

bool buttonReading = false;
bool buttonPressed = false;
unsigned long buttonChangedMs = 0;
unsigned long lastStatusMs = 0;

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
  Serial.printf("temp_c=%.2f dht_temp_c=%.1f humidity=%.0f ldr=%d lid=%s state=%s mode=%s fan=%s buzzer=%s\n",
                readings.tempC, readings.dhtTempC, readings.humidity, readings.ldrRaw,
                readings.lidOpen ? "open" : "closed", machine.started ? stateName(machine.state) : "starting",
                mode == MODE_AUTO ? "auto" : "manual", fanOn ? "on" : "off", buzzerOn ? "on" : "off");
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  actuatorsBegin();
  sensorsBegin();
  Serial.printf("monitor started, primary sensor: %s\n",
                PRIMARY_SENSOR == SENSOR_DS18B20 ? "DS18B20" : "DHT");
}

void loop() {
  unsigned long now = millis();

  checkButton(now);

  // Estado
  if (sensorsUpdate(now, readings)) {
    State previous = machine.state;
    bool wasStarted = machine.started;
    if (updateState(machine, readings.tempC, limits)) {
      // O alarme volta a tocar quando o estado muda
      silenced = false;
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

  if (now - lastStatusMs >= STATUS_INTERVAL_MS) {
    lastStatusMs = now;
    printStatus();
  }
}
