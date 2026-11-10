import json

from app import config

MAX_PAYLOAD_BYTES = 512
TELEMETRY_KEYS = {
    "device", "uptime_s", "temp_c", "dht_temp_c", "humidity_pct",
    "lid_open", "fan_on", "state", "mode", "warning_c", "critical_c",
}
STATES = {"normal", "warning", "critical", "fault"}
MODES = {"auto", "manual"}
STATUSES = {"online", "offline"}
TEMP_MIN_C = -55
TEMP_MAX_C = 125

LIMIT_MIN_C = 20
LIMIT_MAX_C = 50
# Folga mínima entre warning e critical, para a histerese de 2 °C continuar valendo
LIMIT_GAP_C = 3


# bool é subclasse de int em Python, então True passaria como 1
def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_temperature(value) -> bool:
    return value is None or (_is_number(value) and TEMP_MIN_C <= value <= TEMP_MAX_C)


def _is_one_of(value, options: set) -> bool:
    return isinstance(value, str) and value in options


def validate_telemetry(raw: bytes) -> dict | None:
    if len(raw) > MAX_PAYLOAD_BYTES:
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or set(data) != TELEMETRY_KEYS:
        return None

    humidity = data["humidity_pct"]
    valid = (
        data["device"] == config.DEVICE_ID
        and _is_int(data["uptime_s"]) and data["uptime_s"] >= 0
        and _is_temperature(data["temp_c"])
        and _is_temperature(data["dht_temp_c"])
        and (humidity is None or (_is_int(humidity) and 0 <= humidity <= 100))
        and isinstance(data["lid_open"], bool)
        and isinstance(data["fan_on"], bool)
        and _is_one_of(data["state"], STATES)
        and _is_one_of(data["mode"], MODES)
        and _is_number(data["warning_c"])
        and _is_number(data["critical_c"])
        and limits_are_valid(data["warning_c"], data["critical_c"])
    )
    return data if valid else None


def validate_status(raw: bytes) -> str | None:
    try:
        status = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return status if status in STATUSES else None


def limits_are_valid(warning: float, critical: float) -> bool:
    in_range = LIMIT_MIN_C <= warning <= LIMIT_MAX_C and LIMIT_MIN_C <= critical <= LIMIT_MAX_C
    return in_range and critical >= warning + LIMIT_GAP_C
