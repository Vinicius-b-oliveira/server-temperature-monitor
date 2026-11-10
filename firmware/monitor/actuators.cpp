#include <Arduino.h>
#include "pins.h"
#include "actuators.h"

const unsigned long BLINK_MS = 500;
const unsigned long BEEP_ON_MS = 400;
const unsigned long BEEP_PERIOD_MS = 1000;
const unsigned int BEEP_HZ = 2000;

bool toneActive = false;

void actuatorsBegin() {
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_BLUE, OUTPUT);
  pinMode(PIN_FAN, OUTPUT);
  digitalWrite(PIN_FAN, LOW);
}

void setColor(bool red, bool green, bool blue) {
  digitalWrite(PIN_LED_RED, red ? HIGH : LOW);
  digitalWrite(PIN_LED_GREEN, green ? HIGH : LOW);
  digitalWrite(PIN_LED_BLUE, blue ? HIGH : LOW);
}

// LED RGB: azul até a primeira leitura
void showState(unsigned long now, State state, bool started) {
  if (!started) {
    setColor(false, false, true);
    return;
  }
  switch (state) {
    case STATE_NORMAL: setColor(false, true, false); break;
    case STATE_WARNING: setColor(true, true, false); break;
    case STATE_CRITICAL: setColor(true, false, false); break;
    case STATE_FAULT: setColor((now / BLINK_MS) % 2 == 0, false, false); break;
  }
}

// Buzzer passivo: tone() com duração não desliga no Wokwi, então liga e desliga por millis()
void updateBuzzer(unsigned long now, bool buzzerOn) {
  bool shouldSound = buzzerOn && now % BEEP_PERIOD_MS < BEEP_ON_MS;
  if (shouldSound && !toneActive) {
    tone(PIN_BUZZER, BEEP_HZ);
    toneActive = true;
  } else if (!shouldSound && toneActive) {
    noTone(PIN_BUZZER);
    toneActive = false;
  }
}

void updateActuators(unsigned long now, State state, bool started, bool fanOn, bool buzzerOn) {
  showState(now, state, started);
  digitalWrite(PIN_FAN, fanOn ? HIGH : LOW);
  updateBuzzer(now, buzzerOn);
}
