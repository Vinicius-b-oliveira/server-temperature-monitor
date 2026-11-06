# Circuito no Wokwi

Projeto: https://wokwi.com/projects/479892496574303233

O circuito usa os mesmos GPIOs da bancada. A ESP32 fica entre duas meias protoboards. Os pinos de um lado entram na protoboard de cima (LDR, LED RGB e botão) e os do outro lado na de baixo (DS18B20, DHT, buzzer e ventoinha). Os sensores, o buzzer e o LED da ventoinha ficam fora das protoboards, ligados por fios.

## Como rodar

1. Abra o link e clique no botão verde para iniciar a simulação. A primeira compilação pode levar até 2 minutos.
2. O monitor serial mostra uma linha por segundo com as leituras.
3. Para mudar um valor, clique na peça com a simulação rodando. O DS18B20 abre um controle de temperatura, o DHT22 de temperatura e umidade e o LDR de luz (lux). O botão verde funciona com o mouse.

O `sketch.ino` do Wokwi tem o conteúdo de `firmware/hardware_check/hardware_check.ino`, e a aba `pins.h` é o `firmware/hardware_check/pins.h`. Para mudar o código ou o circuito, edite primeiro os arquivos do repositório e depois copie para o Wokwi.

## Diferenças para a bancada

| Ponto | Wokwi | Bancada |
|---|---|---|
| DHT | DHT22, porque o simulador não tem DHT11 | DHT11. Trocar `DHT_TYPE` no sketch |
| LDR | Módulo com o resistor de 10 kΩ embutido | LDR e resistor de 10 kΩ em divisor. O limiar da tampa aberta é calibrado na hora, no firmware principal |
| Ventoinha | LED azul com resistor de 300 Ω | Transistor, diodo e ventoinha, testados separados antes |
| Placa | ESP32 DevKit C V4 (38 pinos) | Provavelmente ESP32 DevKit V1 (30 pinos): mesmos GPIOs, em outras posições |
