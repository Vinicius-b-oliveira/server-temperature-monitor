const REFRESH_MS = 2000;
const CHART_REFRESH_MS = 10000;
const SCALE_MIN_C = 15;
const SCALE_MAX_C = 45;
const HYSTERESIS_C = 2;

const STATE_LABELS = {
  normal: "Normal",
  warning: "Atenção",
  critical: "Crítico",
  fault: "Falha no sensor",
};

const $ = (id) => document.getElementById(id);

let chart = null;
let chartMinutes = 15;
let lastChartLoad = 0;

// Formatação

function formatNumber(value, digits = 1) {
  return value.toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function formatTemp(value) {
  return value === null ? "sem leitura" : `${formatNumber(value)} °C`;
}

function formatTime(iso) {
  const date = new Date(iso);
  const time = date.toLocaleTimeString("pt-BR");
  if (date.toDateString() === new Date().toDateString()) {
    return time;
  }
  return `${date.toLocaleDateString("pt-BR")} ${time}`;
}

function formatAgo(iso) {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(iso)) / 1000));
  if (seconds < 60) return `há ${seconds} s`;
  if (seconds < 3600) return `há ${Math.floor(seconds / 60)} min`;
  return `há ${Math.floor(seconds / 3600)} h`;
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

// Leitura atual

function stateNote(reading) {
  const warning = formatNumber(reading.warning_c, 0);
  const critical = formatNumber(reading.critical_c, 0);
  switch (reading.state) {
    case "normal":
      return `Abaixo de ${warning} °C. No modo automático a ventoinha fica desligada.`;
    case "warning":
      return `Entre ${warning} e ${critical} °C. A ventoinha liga e o estado volta ao normal em ${formatNumber(reading.warning_c - HYSTERESIS_C, 0)} °C.`;
    case "critical":
      return `A partir de ${critical} °C. O alarme toca até alguém silenciar, e o estado volta para atenção em ${formatNumber(reading.critical_c - HYSTERESIS_C, 0)} °C.`;
    default:
      return "O sensor principal não responde. A ventoinha fica ligada por segurança até a leitura voltar.";
  }
}

function placeOnScale(value, min, max) {
  return `${((value - min) / (max - min)) * 100}%`;
}

// Em tela estreita o CSS esconde o nome e fica só o valor
function setTick(tick, name, value, min, max) {
  const label = document.createElement("span");
  label.className = "tick-name";
  label.textContent = `${name} `;
  tick.replaceChildren(label, `${formatNumber(value, 0)} °C`);
  tick.style.left = placeOnScale(value, min, max);
}

function renderRuler(reading) {
  const min = Math.min(SCALE_MIN_C, reading.warning_c - 10);
  const max = Math.max(SCALE_MAX_C, reading.critical_c + 8);
  $("zone-normal").style.flex = `${reading.warning_c - min}`;
  $("zone-warning").style.flex = `${reading.critical_c - reading.warning_c}`;
  $("zone-critical").style.flex = `${max - reading.critical_c}`;
  $("scale-min").textContent = `${min} °C`;
  $("scale-max").textContent = `${max} °C`;

  setTick($("tick-warning"), "Atenção", reading.warning_c, min, max);
  setTick($("tick-critical"), "Crítico", reading.critical_c, min, max);

  const needle = $("needle");
  needle.hidden = reading.temp_c === null;
  if (reading.temp_c !== null) {
    const clamped = Math.min(max, Math.max(min, reading.temp_c));
    needle.style.left = placeOnScale(clamped, min, max);
  }
}

function renderLatest(data) {
  const reading = data.reading;
  document.body.classList.toggle("is-offline", !data.online);
  $("connection-dot").classList.toggle("is-online", data.online);
  $("connection").textContent = data.online ? "Online" : reading ? "Offline" : "Aguardando dados";

  if (!reading) {
    document.body.dataset.state = "none";
    return;
  }

  document.body.dataset.state = reading.state;
  $("device").textContent = reading.device;
  $("last-seen").textContent = formatAgo(reading.received_at);
  $("temp-value").textContent = reading.temp_c === null ? "--" : formatNumber(reading.temp_c);
  $("state-text").textContent = STATE_LABELS[reading.state];
  $("state-icon").setAttribute("href", `#icon-${reading.state}`);
  $("state-note").textContent = data.online
    ? stateNote(reading)
    : `Sem dados novos ${formatAgo(reading.received_at)}. Os valores abaixo são da última leitura recebida.`;

  $("fact-fan").textContent = reading.fan_on ? "Ligada" : "Desligada";
  $("fact-lid").textContent = reading.lid_open ? "Aberta" : "Fechada";
  $("fact-mode").textContent = reading.mode === "auto" ? "Automático" : "Manual";
  $("fact-humidity").textContent = reading.humidity_pct === null ? "sem leitura" : `${reading.humidity_pct}%`;
  $("fact-dht").textContent = formatTemp(reading.dht_temp_c);

  renderRuler(reading);
  renderControls(reading, data.online);
}

// Gráfico

// Linha vertical no ponto do tooltip, para ler o horário sem mirar na linha
const crosshair = {
  id: "crosshair",
  afterDatasetsDraw(target) {
    const active = target.tooltip?.getActiveElements();
    if (!active?.length) return;
    const { ctx, chartArea } = target;
    const x = active[0].element.x;
    ctx.save();
    ctx.strokeStyle = cssVar("--ink-3");
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, chartArea.top);
    ctx.lineTo(x, chartArea.bottom);
    ctx.stroke();
    ctx.restore();
  },
};

function chartColors() {
  return {
    series: cssVar("--series"),
    warning: cssVar("--warning"),
    critical: cssVar("--critical"),
    ink: cssVar("--ink-2"),
    rule: cssVar("--rule"),
  };
}

function createChart() {
  const colors = chartColors();
  const line = (label, color, dashed) => ({
    label,
    data: [],
    borderColor: color,
    borderWidth: 2,
    borderDash: dashed ? [6, 4] : [],
    pointRadius: 0,
    pointHoverRadius: dashed ? 0 : 4,
    stepped: dashed,
    spanGaps: false,
  });
  chart = new Chart($("chart"), {
    type: "line",
    data: {
      datasets: [
        line("Temperatura", colors.series, false),
        line("Limite de atenção", colors.warning, true),
        line("Limite crítico", colors.critical, true),
      ],
    },
    options: {
      animation: false,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (items) => new Date(items[0].parsed.x).toLocaleTimeString("pt-BR"),
            label: (item) => `${item.dataset.label}: ${item.parsed.y === null ? "sem leitura" : formatTemp(item.parsed.y)}`,
          },
        },
      },
      scales: {
        x: {
          type: "linear",
          ticks: {
            color: colors.ink,
            maxTicksLimit: 7,
            callback: (value) => new Date(value).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }),
          },
          grid: { display: false },
        },
        y: {
          ticks: { color: colors.ink, callback: (value) => `${value} °C` },
          grid: { color: colors.rule },
          suggestedMin: 20,
          suggestedMax: 35,
        },
      },
    },
    plugins: [crosshair],
  });
}

async function loadChart() {
  const box = document.querySelector(".chart-box");
  box.classList.add("is-loading");
  try {
    const readings = await api(`/api/readings?minutes=${chartMinutes}`);
    const points = (key) => readings.map((r) => ({ x: new Date(r.received_at).getTime(), y: r[key] }));
    const colors = chartColors();
    const [temp, warning, critical] = chart.data.datasets;
    temp.data = points("temp_c");
    warning.data = points("warning_c");
    critical.data = points("critical_c");
    chart.options.scales.x.ticks.color = colors.ink;
    chart.options.scales.y.ticks.color = colors.ink;
    chart.options.scales.y.grid.color = colors.rule;
    temp.borderColor = colors.series;
    warning.borderColor = colors.warning;
    critical.borderColor = colors.critical;
    // Marcas do eixo em minutos redondos: 3 min, 10 min ou 1 h
    chart.options.scales.x.ticks.stepSize = { 15: 3, 60: 10, 360: 60 }[chartMinutes] * 60000;
    chart.options.scales.x.min = Date.now() - chartMinutes * 60000;
    chart.options.scales.x.max = Date.now();
    chart.update();
    $("chart-empty").hidden = readings.length > 0;
    lastChartLoad = Date.now();
  } finally {
    box.classList.remove("is-loading");
  }
}

// Indicadores

function renderTrend(indicators) {
  const trend = $("trend");
  trend.replaceChildren();
  const rate = indicators.rate_c_per_min;
  if (rate === null) {
    trend.textContent = "Ainda não há leituras suficientes para calcular a tendência.";
    return;
  }
  const strong = document.createElement("strong");
  if (Math.abs(rate) < 0.05) {
    strong.textContent = "Temperatura estável";
  } else {
    strong.textContent = `${rate > 0 ? "Subindo" : "Caindo"} ${formatNumber(Math.abs(rate), 2)} °C por minuto`;
  }
  trend.append(strong, " nos últimos 5 minutos.");

  const minutes = indicators.minutes_to_critical;
  const critical = formatNumber(indicators.critical_c, 0);
  if (minutes === 0) {
    trend.append(` Já passou do limite crítico de ${critical} °C.`);
  } else if (minutes !== null) {
    trend.append(` Nesse ritmo, chega a ${critical} °C em cerca de ${Math.max(1, Math.round(minutes))} min.`);
  }
}

// Eventos

function describeEvent(event) {
  const detail = event.detail ? JSON.parse(event.detail) : null;
  switch (event.kind) {
    case "state_change":
      return ["Mudança de estado", `${STATE_LABELS[detail.from] ?? detail.from} para ${STATE_LABELS[detail.to] ?? detail.to}`];
    case "sensor_fault":
      return ["Falha no sensor", "Sem leitura válida do sensor principal"];
    case "online":
      return ["Dispositivo conectado", ""];
    case "offline":
      return ["Dispositivo desconectado", "O broker avisou que a conexão caiu"];
    case "command":
      return ["Comando enviado", describeCommand(detail)];
    default:
      return [event.kind, event.detail ?? ""];
  }
}

function describeCommand({ name, payload }) {
  if (name === "mode") return payload === "auto" ? "Modo automático" : "Modo manual";
  if (name === "fan") return payload === "on" ? "Ligar a ventoinha" : "Desligar a ventoinha";
  if (name === "silence") return "Silenciar o alarme";
  if (name === "limits") {
    const limits = JSON.parse(payload);
    return `Limites: atenção ${limits.warning} °C, crítico ${limits.critical} °C`;
  }
  return `${name}: ${payload}`;
}

function renderEvents(events) {
  const rows = events.map((event) => {
    const [title, detail] = describeEvent(event);
    const row = document.createElement("tr");
    for (const text of [formatTime(event.occurred_at), title, detail]) {
      const cell = document.createElement("td");
      cell.textContent = text;
      row.append(cell);
    }
    return row;
  });
  $("events-body").replaceChildren(...rows);
  $("events-empty").hidden = events.length > 0;
}

// Comandos

function showFeedback(text, isError = false) {
  const feedback = $("feedback");
  feedback.textContent = text;
  feedback.classList.toggle("is-error", isError);
}

async function sendCommand(name, body, doneText) {
  try {
    await api(`/api/commands/${name}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    showFeedback(`${doneText} às ${new Date().toLocaleTimeString("pt-BR")}. O painel mostra a mudança quando o ESP32 responder.`);
    return true;
  } catch (error) {
    if (error.status === 503) {
      showFeedback("O servidor está sem conexão com o broker MQTT. O comando não foi enviado.", true);
    } else if (error.status === 400 || error.status === 422) {
      showFeedback("O servidor recusou o comando. Confira os valores.", true);
    } else {
      showFeedback("O servidor não respondeu. Confira se ele está rodando.", true);
    }
    return false;
  }
}

function renderControls(reading, online) {
  const manual = reading.mode === "manual";
  $("mode-auto").setAttribute("aria-pressed", String(!manual));
  $("mode-manual").setAttribute("aria-pressed", String(manual));

  const forced = reading.state === "critical" || reading.state === "fault";
  $("fan-on").disabled = !manual;
  $("fan-off").disabled = !manual;
  if (!manual) {
    $("fan-hint").textContent = "Disponível no modo manual.";
  } else if (forced) {
    $("fan-hint").textContent = "Em crítico e em falha a ventoinha fica ligada, mesmo se mandar desligar.";
  } else {
    $("fan-hint").textContent = "O comando vale enquanto o modo for manual.";
  }

  const critical = reading.state === "critical";
  $("silence").disabled = !critical;
  $("silence-hint").textContent = critical
    ? "Silencia o buzzer até o estado mudar. O LED continua vermelho."
    : "O alarme só toca no estado crítico.";

  // Mostra os limites em vigor no ESP32, menos enquanto alguém está digitando
  const editing = document.activeElement?.matches("#limits-form input");
  if (!editing) {
    $("limit-warning").value = reading.warning_c;
    $("limit-critical").value = reading.critical_c;
  }
}

function setupControls() {
  $("mode-auto").addEventListener("click", () => sendCommand("mode", { mode: "auto" }, "Modo automático enviado"));
  $("mode-manual").addEventListener("click", () => sendCommand("mode", { mode: "manual" }, "Modo manual enviado"));
  $("fan-on").addEventListener("click", () => sendCommand("fan", { fan: "on" }, "Comando para ligar a ventoinha enviado"));
  $("fan-off").addEventListener("click", () => sendCommand("fan", { fan: "off" }, "Comando para desligar a ventoinha enviado"));
  $("silence").addEventListener("click", () => sendCommand("silence", null, "Pedido para silenciar o alarme enviado"));

  $("limits-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const warningInput = $("limit-warning");
    const criticalInput = $("limit-critical");
    const warning = Number(warningInput.value);
    const critical = Number(criticalInput.value);
    const inRange = (v) => Number.isInteger(v) && v >= 20 && v <= 50;
    const valid = inRange(warning) && inRange(critical) && critical - warning >= 3;
    warningInput.setAttribute("aria-invalid", String(!valid));
    criticalInput.setAttribute("aria-invalid", String(!valid));
    if (!valid) {
      showFeedback("Use números inteiros entre 20 e 50 °C, com o crítico pelo menos 3 °C acima do de atenção.", true);
      return;
    }
    await sendCommand("limits", { warning, critical }, `Limites de ${warning} e ${critical} °C enviados`);
  });

  for (const button of document.querySelectorAll(".range button")) {
    button.addEventListener("click", () => {
      chartMinutes = Number(button.dataset.minutes);
      for (const other of document.querySelectorAll(".range button")) {
        other.setAttribute("aria-pressed", String(other === button));
      }
      loadChart();
    });
  }
}

// Atualização periódica

async function refresh() {
  try {
    const [latest, indicators, events] = await Promise.all([
      api("/api/latest"),
      api("/api/indicators"),
      api("/api/events?limit=50"),
    ]);
    renderLatest(latest);
    renderTrend(indicators);
    renderEvents(events);
    if (Date.now() - lastChartLoad >= CHART_REFRESH_MS) {
      await loadChart();
    }
  } catch (error) {
    document.body.classList.add("is-offline");
    $("connection").textContent = "Servidor fora do ar";
    $("connection-dot").classList.remove("is-online");
  }
}

createChart();
setupControls();
refresh();
setInterval(refresh, REFRESH_MS);
