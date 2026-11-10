#pragma once
#include "state_machine.h"

void actuatorsBegin();
void updateActuators(unsigned long now, State state, bool started, bool fanOn, bool buzzerOn);
