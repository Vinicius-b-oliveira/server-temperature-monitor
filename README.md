# Monitor de temperatura para servidor

Projeto final da disciplina de Internet das Coisas (Engenharia de Software, Católica de Santa Catarina), Grupo 2.

Um ESP32 mede a temperatura de um gabinete que faz o papel de rack de servidor e classifica a situação em normal, atenção ou crítico. Conforme o estado, ele liga a ventoinha, muda a cor do LED RGB e toca o buzzer. A telemetria vai por MQTT para um servidor em Python, que guarda as leituras em SQLite, mostra um painel web e envia comandos de volta ao ESP32.

## Estrutura

```
firmware/
  monitor/         firmware principal: sensores, estados, atuadores e MQTT
  hardware_check/  teste dos sensores e das saídas, sem rede
  wifi_check/      teste de Wi-Fi e da porta 1883 do broker
server/            servidor Python: MQTT, SQLite e API (FastAPI)
  app/
  tests/
  reset_db.py      apaga os dados, guardando uma cópia
web/               painel (HTML, CSS e JavaScript, sem framework)
wokwi/             circuito do simulador (diagram.json, libraries.txt e config.h)
docs/              documentos entregues (PDF) e diagramas
```

## Firmware (`firmware/monitor`)

O ESP32 lê os sensores, decide o estado e aciona as saídas sozinho. A rede só leva a telemetria e traz os comandos, então o controle local continua funcionando sem Wi-Fi ou sem broker.

| Estado | Quando | LED | Ventoinha | Buzzer |
|---|---|---|---|---|
| normal | abaixo de 27 °C | verde | desligada | desligado |
| atenção (`warning`) | a partir de 27 °C | amarelo | ligada | desligado |
| crítico (`critical`) | a partir de 32 °C | vermelho | ligada | toca até ser silenciado |
| falha (`fault`) | 3 leituras inválidas seguidas do sensor principal | vermelho piscando | ligada | desligado |

A histerese é de 2 °C: de atenção o estado só volta para normal em 25 °C, e de crítico só volta para atenção em 30 °C. Os limites podem ser mudados pelo painel, entre 20 e 50 °C e com o crítico pelo menos 3 °C acima do de atenção. Ao reiniciar, o ESP32 volta aos padrões. O botão silencia o buzzer até o estado mudar. O LDR indica se a tampa está aberta.

Para gravar:

1. Copie `config.example.h` para `config.h`, na mesma pasta, e ajuste a rede. Em rede aberta, deixe a senha vazia (`""`). O `config.h` não vai para o git.
2. No `config.h`, confira também:
   - `DHT_TYPE`: `DHT11` na bancada.
   - `PRIMARY_SENSOR`: `SENSOR_DS18B20` com a sonda montada, ou `SENSOR_DHT` para usar o DHT11 como sensor principal.
   - `LDR_OPEN_THRESHOLD`: valor do LDR abaixo do qual a tampa conta como aberta. Calibre olhando o monitor serial com a tampa aberta e fechada.
3. Abra `monitor.ino` no Arduino IDE 2.x, com a placa "ESP32 Dev Module" (pacote `esp32` 3.3.12), grave e abra o monitor serial em 115200.

O monitor serial mostra uma linha por segundo com as leituras, o estado, o modo, a ventoinha, o buzzer e se o MQTT está conectado. Mudanças de estado e comandos recebidos aparecem em linhas próprias.

Bibliotecas, instaladas pelo Gerenciador de Bibliotecas do Arduino IDE:

| Biblioteca | Autor | Versão |
|---|---|---|
| OneWire | Paul Stoffregen | 2.3.8 |
| DallasTemperature | Miles Burton | 4.0.6 |
| DHT sensor library | Adafruit | 1.4.7 |
| Adafruit Unified Sensor | Adafruit | 1.1.15 |
| PubSubClient | Nick O'Leary | 2.8.0 |
| ArduinoJson | Benoit Blanchon | 7.4.3 |

No Linux, o usuário precisa estar no grupo `dialout` para gravar pela USB.

## Simulador (Wokwi)

O mesmo firmware roda no Wokwi, com a mesma placa e os mesmos GPIOs: https://wokwi.com/projects/480262655510684673. Detalhes em `wokwi/README.md`.

## Mensagens MQTT

Broker público `broker.hivemq.com`, porta 1883. Todos os tópicos começam com `thermomon/g2-axr2adzj/rack01/`.

| Tópico | Direção | Conteúdo |
|---|---|---|
| `telemetry` | ESP32 para o servidor, a cada 5 s | JSON abaixo |
| `status` | ESP32 para o servidor | `online` ao conectar; `offline` publicado pelo broker (Last Will) quando a conexão cai |
| `cmd/mode` | servidor para o ESP32 | `auto` ou `manual` |
| `cmd/fan` | servidor para o ESP32 | `on` ou `off`. Só vale no modo manual e não desliga a ventoinha em crítico ou falha |
| `cmd/limits` | servidor para o ESP32 | `{"warning":27,"critical":32}` |
| `cmd/silence` | servidor para o ESP32 | `1` |

```json
{"device":"esp32-rack01","uptime_s":1234,"temp_c":24.31,"dht_temp_c":24.0,"humidity_pct":41,"lid_open":false,"fan_on":true,"state":"warning","mode":"auto","warning_c":27.0,"critical_c":32.0}
```

Leitura que falhou vai como `null`. O broker é aberto, então o ESP32 só aceita comandos com o conteúdo exato da tabela, e o servidor descarta telemetria fora do formato.

## Servidor e painel

Precisa de Python 3.10 ou mais novo. Em Debian ou Ubuntu, instale antes o pacote `python3-venv`.

```
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

O painel fica em http://127.0.0.1:8000. Ele mostra a temperatura atual, as faixas e os limites em vigor, o histórico, a tendência, os eventos e os controles de modo, ventoinha, limites e alarme. As leituras ficam em `server/data/monitor.db`. A API está em `/api` (`/api/latest`, `/api/readings`, `/api/events`, `/api/indicators` e `/api/commands/...`).

Configuração por variável de ambiente, todas opcionais: `MQTT_HOST`, `MQTT_PORT`, `TEAM_CODE`, `DEVICE_ID`, `DB_PATH` e `OFFLINE_AFTER_S` (segundos sem leitura até o painel mostrar offline, padrão 15).

Testes:

```
cd server
.venv/bin/python -m pytest
```

Para começar com o banco vazio, pare o servidor e rode:

```
cd server
.venv/bin/python reset_db.py
```

O script pede confirmação, move o banco atual para `server/data/backup/` com a data e a hora no nome e cria um banco novo.

## Testes do hardware

- `firmware/hardware_check`: lê o DS18B20, o DHT e o LDR, troca a cor do LED RGB a cada 2 s e apita o buzzer quando o botão é apertado. Serve para conferir a montagem antes de gravar o monitor. Na bancada, troque `DHT_TYPE` para `DHT11` no início do sketch.
- `firmware/wifi_check`: conecta ao Wi-Fi e mostra o IP, o sinal e se os brokers públicos respondem na porta 1883. Precisa de um `config.h` copiado do `config.example.h`.

## Documentos

- `docs/stage1_proposal.pdf`: Etapa 1, proposta e planejamento
- `docs/stage2_technical_design.pdf`: Etapa 2, projeto técnico
- `docs/stage3_hardware_firmware.pdf`: Etapa 3, hardware e firmware
- `docs/stage4_iot_data_control.pdf`: Etapa 4, integração IoT, dados e controle remoto
- `docs/diagrams/`: diagramas das etapas (SVG e PNG)
