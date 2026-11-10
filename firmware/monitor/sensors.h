#pragma once

struct Readings {
  float tempC;       // sensor principal, NAN se falhou
  float dsTempC;
  float dhtTempC;
  float humidity;
  int ldrRaw;
  bool lidOpen;
};

void sensorsBegin();
// Devolve true quando há leitura nova do sensor principal
bool sensorsUpdate(unsigned long now, Readings& readings);
