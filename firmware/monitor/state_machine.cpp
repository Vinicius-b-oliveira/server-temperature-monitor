#include <Arduino.h>
#include "config.h"
#include "state_machine.h"

// Sem histerese: usado na partida e na saída da falha
State stateFromTemp(float tempC, const Limits& limits) {
  if (tempC >= limits.critical) {
    return STATE_CRITICAL;
  }
  if (tempC >= limits.warning) {
    return STATE_WARNING;
  }
  return STATE_NORMAL;
}

State nextState(State current, float tempC, const Limits& limits) {
  switch (current) {
    case STATE_NORMAL:
      return stateFromTemp(tempC, limits);
    case STATE_WARNING:
      if (tempC >= limits.critical) {
        return STATE_CRITICAL;
      }
      if (tempC <= limits.warning - HYSTERESIS_C) {
        return STATE_NORMAL;
      }
      return STATE_WARNING;
    case STATE_CRITICAL:
      if (tempC <= limits.critical - HYSTERESIS_C) {
        return STATE_WARNING;
      }
      return STATE_CRITICAL;
    default:
      return stateFromTemp(tempC, limits);
  }
}

bool updateState(StateMachine& machine, float tempC, const Limits& limits) {
  State previous = machine.state;

  if (isnan(tempC)) {
    machine.invalidReadings++;
    // Uma leitura ruim isolada não muda o estado
    if (machine.invalidReadings >= FAULT_READINGS) {
      machine.state = STATE_FAULT;
      machine.started = true;
    }
    return machine.state != previous;
  }

  machine.invalidReadings = 0;
  if (!machine.started) {
    machine.state = stateFromTemp(tempC, limits);
    machine.started = true;
    return true;
  }
  machine.state = nextState(machine.state, tempC, limits);
  return machine.state != previous;
}

// A folga mínima mantém a histerese funcionando entre os dois limites
bool limitsValid(float warning, float critical) {
  return warning >= LIMIT_MIN_C && critical <= LIMIT_MAX_C &&
         critical - warning >= LIMIT_MIN_GAP_C;
}

const char* stateName(State state) {
  switch (state) {
    case STATE_NORMAL: return "normal";
    case STATE_WARNING: return "warning";
    case STATE_CRITICAL: return "critical";
    default: return "fault";
  }
}
