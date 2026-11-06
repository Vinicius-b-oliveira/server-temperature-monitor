# Monitor de temperatura para servidor

Projeto final da disciplina de Internet das Coisas (Engenharia de Software, Católica de Santa Catarina), Grupo 2.

Um ESP32 mede a temperatura de um gabinete que faz o papel de rack de servidor e classifica a situação em normal, atenção ou crítico. Conforme o estado, ele liga a ventoinha, muda a cor do LED RGB e toca o buzzer. A telemetria vai por MQTT para um servidor em Python, que guarda as leituras em SQLite, mostra um painel web e envia comandos de volta ao ESP32.

O projeto está em andamento. Por enquanto o repositório tem o teste de hardware e o teste de rede do ESP32, o circuito no Wokwi e a lista de dependências do servidor. O firmware principal, o servidor e o painel entram nas próximas etapas.

## Estrutura

```
firmware/
  hardware_check/  teste dos sensores e das saídas, sem rede
  wifi_check/      teste de Wi-Fi e da porta 1883 do broker
wokwi/             circuito do simulador (diagram.json e libraries.txt)
server/
  requirements.txt
docs/
  diagrams/        diagramas das etapas (SVG e PNG)
  stage1_proposal.pdf          Etapa 1 entregue: proposta e planejamento
  stage2_technical_design.pdf  Etapa 2 entregue: projeto técnico
```

## Teste de hardware (`firmware/hardware_check`)

Lê o DS18B20, o DHT e o LDR, mostra o estado do botão e troca a cor do LED RGB a cada 2 s (verde, amarelo, vermelho e azul). O LED da ventoinha acende junto com o vermelho, e o buzzer apita quando o botão é apertado. O monitor serial, em 115200, mostra uma linha por segundo com todas as leituras. Leitura `nan` indica sensor sem resposta.

Na bancada, troque `DHT_TYPE` para `DHT11` no início do `hardware_check.ino`. O mesmo sketch roda no Wokwi (veja `wokwi/README.md`).

Bibliotecas, instaladas pelo Gerenciador de Bibliotecas do Arduino IDE:

| Biblioteca | Versão |
|---|---|
| OneWire | 2.3.8 |
| DallasTemperature | 4.0.6 |
| DHT sensor library (Adafruit) | 1.4.7 |
| Adafruit Unified Sensor | 1.1.15 |

Placa "ESP32 Dev Module", pacote `esp32` 3.3.12.

## Teste de Wi-Fi (`firmware/wifi_check`)

Conecta ao Wi-Fi e mostra no monitor serial o IP, o sinal (RSSI) e se os brokers MQTT públicos respondem na porta 1883. Se nenhum broker responder, faz um teste HTTP para saber se a rede bloqueia só o MQTT, se pede login numa página do navegador (portal cativo) ou se está sem internet.

1. Copie `config.example.h` para `config.h`, na mesma pasta, e preencha o nome e a senha da rede. Em rede aberta, deixe a senha vazia (`""`). O `config.h` não vai para o git.
2. Abra `wifi_check.ino` no Arduino IDE 2.x, com a placa "ESP32 Dev Module" (pacote de placas `esp32` da Espressif).
3. Grave no ESP32 e abra o monitor serial em 115200. O teste se repete a cada 10 s.

No Linux, o usuário precisa estar no grupo `dialout` para gravar pela USB.

## Servidor

Precisa de Python 3.10 ou mais novo. Em Debian ou Ubuntu, instale antes o pacote `python3-venv`.

```
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
