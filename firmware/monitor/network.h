#pragma once
#include "sensors.h"
#include "state_machine.h"

typedef void (*CommandHandler)(const char* name, const char* payload);

void networkBegin(CommandHandler handler);
void networkLoop(unsigned long now);
bool mqttConnected();
void publishTelemetry(const Readings& readings, const char* state, const char* mode, bool fanOn,
                      const Limits& limits);
