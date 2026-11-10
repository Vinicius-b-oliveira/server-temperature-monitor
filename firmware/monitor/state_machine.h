#pragma once

enum State { STATE_NORMAL, STATE_WARNING, STATE_CRITICAL, STATE_FAULT };

struct Limits {
  float warning;
  float critical;
};

struct StateMachine {
  State state = STATE_NORMAL;
  bool started = false;
  int invalidReadings = 0;
};

// Devolve true se o estado mudou
bool updateState(StateMachine& machine, float tempC, const Limits& limits);
bool limitsValid(float warning, float critical);
const char* stateName(State state);
