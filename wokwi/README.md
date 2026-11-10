# Circuito no Wokwi

Projeto: https://wokwi.com/projects/480262655510684673

O circuito usa a mesma placa da bancada, a ESP32 DevKit V1 de 30 pinos, e os mesmos GPIOs. A placa fica entre duas meias protoboards, nas colunas 16 a 30. Os pinos de um lado entram na protoboard de cima (LDR, LED RGB e botão) e os do outro lado na de baixo (DS18B20, DHT, buzzer e ventoinha). Os sensores, o buzzer e o LED da ventoinha ficam fora das protoboards, ligados por fios. O 3V3 sai da protoboard de baixo e alimenta os dois trilhos positivos; o GND sai da de cima e passa para a de baixo pela direita.

## Como rodar

1. Abra o link e clique no botão verde para iniciar a simulação. A primeira compilação pode levar até 2 minutos.
2. O monitor serial mostra uma linha por segundo com as leituras, o estado e se o MQTT está conectado.
3. Para mudar um valor, clique na peça com a simulação rodando. O DS18B20 abre um controle de temperatura, o DHT22 de temperatura e umidade e o LDR de luz (lux). O botão verde silencia o alarme.
4. O simulador conecta no Wi-Fi `Wokwi-GUEST` e publica no broker público. Com o servidor rodando no computador (veja o README principal), as leituras aparecem no painel.

## Arquivos

| No Wokwi | No repositório |
|---|---|
| `sketch.ino` | `firmware/monitor/monitor.ino` |
| `pins.h`, `sensors.*`, `state_machine.*`, `actuators.*`, `network.*` | os arquivos de mesmo nome em `firmware/monitor/` |
| `config.h` | `wokwi/config.h` (só valores do simulador, sem senha) |
| `diagram.json`, `libraries.txt` | os arquivos desta pasta |

Para mudar o código ou o circuito, edite primeiro os arquivos do repositório e depois copie para o Wokwi.

O circuito usado na Etapa 2, com o teste de hardware, continua em https://wokwi.com/projects/479892496574303233.

## Diferenças para a bancada

| Ponto | Wokwi | Bancada |
|---|---|---|
| DHT | DHT22, porque o simulador não tem DHT11 | DHT11. `DHT_TYPE` no `config.h` |
| LDR | Módulo com o resistor de 10 kΩ embutido. Limiar 500 (cerca de 1500 lux) | LDR e resistor de 10 kΩ em divisor. O limiar é calibrado na hora |
| Ventoinha | LED azul com resistor de 300 Ω | Transistor, diodo e ventoinha, testados separados antes |
| Wi-Fi | `Wokwi-GUEST`, sem senha | Rede do laboratório, no `config.h` |
| Sensor principal | DS18B20 | DS18B20, ou o DHT11 (`PRIMARY_SENSOR = SENSOR_DHT`) enquanto o DS18B20 não estiver montado |
