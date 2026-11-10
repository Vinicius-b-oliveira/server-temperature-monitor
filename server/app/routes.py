import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app import config, database, indicators, mqtt_client, validation

RATE_MINUTES = 5
FORECAST_MINUTES = 10

router = APIRouter(prefix="/api")


class ModeCommand(BaseModel):
    mode: Literal["auto", "manual"]


class FanCommand(BaseModel):
    fan: Literal["on", "off"]


class LimitsCommand(BaseModel):
    warning: int
    critical: int


def _seconds_since(timestamp: str) -> float:
    return (datetime.now(timezone.utc) - datetime.fromisoformat(timestamp)).total_seconds()


def _send(name: str, payload: str) -> dict:
    if not mqtt_client.publish_command(name, payload):
        raise HTTPException(status_code=503, detail="MQTT broker unavailable")
    return {"command": name, "payload": payload}


@router.get("/latest")
def get_latest() -> dict:
    reading = database.latest_reading(config.DB_PATH)
    fresh = reading is not None and _seconds_since(reading["received_at"]) < config.OFFLINE_AFTER_S
    # Sem nenhum status recebido ainda, vale só a idade da última leitura
    online = fresh and database.last_status(config.DB_PATH) != "offline"
    return {"online": online, "reading": reading}


@router.get("/readings")
def get_readings(minutes: int = Query(60, ge=1, le=1440)) -> list[dict]:
    return database.readings_since(config.DB_PATH, minutes)


@router.get("/events")
def get_events(limit: int = Query(50, ge=1, le=500)) -> list[dict]:
    return database.recent_events(config.DB_PATH, limit)


@router.get("/indicators")
def get_indicators() -> dict:
    latest = database.latest_reading(config.DB_PATH)
    critical_c = latest["critical_c"] if latest else config.CRITICAL_C
    return {
        "rate_c_per_min": indicators.rate_per_minute(
            database.readings_since(config.DB_PATH, RATE_MINUTES)
        ),
        "minutes_to_critical": indicators.minutes_to_critical(
            database.readings_since(config.DB_PATH, FORECAST_MINUTES), critical_c
        ),
        "critical_c": critical_c,
    }


@router.post("/commands/mode")
def post_mode(body: ModeCommand) -> dict:
    return _send("mode", body.mode)


@router.post("/commands/fan")
def post_fan(body: FanCommand) -> dict:
    return _send("fan", body.fan)


@router.post("/commands/limits")
def post_limits(body: LimitsCommand) -> dict:
    if not validation.limits_are_valid(body.warning, body.critical):
        raise HTTPException(
            status_code=400,
            detail="Limits must be between 20 and 50 and critical at least 3 above warning",
        )
    return _send("limits", json.dumps({"warning": body.warning, "critical": body.critical}))


@router.post("/commands/silence")
def post_silence() -> dict:
    return _send("silence", "1")
