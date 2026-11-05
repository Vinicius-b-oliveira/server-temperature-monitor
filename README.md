# Monitor de temperatura para servidor

Projeto final da disciplina de Internet das Coisas (Engenharia de Software, Católica de Santa Catarina), Grupo 2.

Um ESP32 mede a temperatura de um gabinete que faz o papel de rack de servidor e classifica a situação em normal, atenção ou crítico. Conforme o estado, ele liga a ventoinha, muda a cor do LED RGB e toca o buzzer. A telemetria vai por MQTT para um servidor em Python, que guarda as leituras em SQLite, mostra um painel web e envia comandos de volta ao ESP32.

O projeto está em andamento. Por enquanto o repositório tem o teste de rede do ESP32 e a base do servidor. O firmware principal, o servidor e o painel entram nas próximas etapas.

## Estrutura

```
firmware/
  wifi_check/    teste de Wi-Fi e da porta 1883 do broker
server/
  requirements.txt
docs/
  diagrams/      diagramas das etapas (SVG e PNG)
```

## Teste de Wi-Fi (`firmware/wifi_check`)

Conecta ao Wi-Fi e mostra no monitor serial o IP, o sinal (RSSI) e se os brokers MQTT públicos respondem na porta 1883. Se nenhum broker responder, tenta a porta 80 para saber se a rede bloqueia só o MQTT ou se está sem internet.

1. Copie `config.example.h` para `config.h`, na mesma pasta, e preencha o nome e a senha da rede. O `config.h` não vai para o git.
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
