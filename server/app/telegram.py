import logging
import threading
import time
import urllib.parse
import urllib.request

from app import config

log = logging.getLogger(__name__)

ALERT_STATES = {"warning": "atenção", "critical": "estado crítico", "fault": "falha no sensor"}
MIN_INTERVAL_S = 60
SEND_TIMEOUT_S = 10

_last_sent: dict[str, float] = {}
_now = time.monotonic


def enabled() -> bool:
    return bool(config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID)


def _format_temp(value: float) -> str:
    return f"{value:.1f}".replace(".", ",") + " °C"


def format_message(reading: dict) -> str:
    state = reading["state"]
    title = f"{reading['device']}: {ALERT_STATES[state]}"
    if state == "fault":
        return f"{title}. Sem leitura válida do sensor principal, a ventoinha fica ligada."
    limit = reading["warning_c"] if state == "warning" else reading["critical_c"]
    temp = "sem leitura" if reading["temp_c"] is None else _format_temp(reading["temp_c"])
    return f"{title}, {temp} (limite de {_format_temp(limit)})."


def _send(text: str) -> None:
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": config.TELEGRAM_CHAT_ID, "text": text}).encode()
    try:
        with urllib.request.urlopen(url, data=body, timeout=SEND_TIMEOUT_S) as response:
            response.read()
    except OSError as err:
        log.warning("Telegram message not sent: %s", err)


# Em thread própria, para a espera da API não travar a recepção do MQTT
def _dispatch(text: str) -> None:
    threading.Thread(target=_send, args=(text,), daemon=True).start()


def notify_state_change(old_state: str | None, reading: dict) -> None:
    state = reading["state"]
    if not enabled() or state not in ALERT_STATES or state == old_state:
        return
    # O broker é público: o intervalo impede que mensagens forjadas lotem o chat
    now = _now()
    last = _last_sent.get(state)
    if last is not None and now - last < MIN_INTERVAL_S:
        log.info("Telegram alert for %s skipped, last one less than %d s ago", state, MIN_INTERVAL_S)
        return
    _last_sent[state] = now
    _dispatch(format_message(reading))
