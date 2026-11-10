from datetime import datetime, timedelta, timezone

import pytest

from app import indicators

START = datetime(2026, 11, 13, 14, 0, tzinfo=timezone.utc)


def series(temps: list[float], step_s: int = 5) -> list[dict]:
    return [
        {"received_at": (START + timedelta(seconds=i * step_s)).isoformat(), "temp_c": t}
        for i, t in enumerate(temps)
    ]


# Caso 14: 0,5 °C/min, uma leitura a cada 5 s durante 10 min (120 leituras)
def test_linear_series():
    temps = [20 + 0.5 * i / 12 for i in range(120)]
    readings = series(temps)
    assert indicators.rate_per_minute(readings) == pytest.approx(0.5)
    # Última leitura: 20 + 0,5 * 119/12 = 24,958 °C. Faltam 7,042 °C a 0,5 °C/min
    assert indicators.minutes_to_critical(readings, 32) == pytest.approx(14.0833, abs=1e-3)


def test_flat_series_has_no_forecast():
    readings = series([24.0] * 60)
    assert indicators.rate_per_minute(readings) == pytest.approx(0.0)
    assert indicators.minutes_to_critical(readings, 32) is None


def test_falling_series_has_no_forecast():
    readings = series([30 - 0.1 * i for i in range(60)])
    assert indicators.minutes_to_critical(readings, 32) is None


def test_above_critical_returns_zero():
    readings = series([33 + 0.1 * i for i in range(20)])
    assert indicators.minutes_to_critical(readings, 32) == 0.0


def test_moving_average_removes_noise():
    temps = [20 + 0.5 * i / 12 + (0.2 if i % 2 else -0.2) for i in range(120)]
    assert indicators.rate_per_minute(series(temps)) == pytest.approx(0.5, abs=0.01)


def test_few_or_missing_readings():
    assert indicators.rate_per_minute([]) is None
    assert indicators.rate_per_minute(series([24.0, 24.1])) is None
    assert indicators.minutes_to_critical(series([None, None, None]), 32) is None


def test_slope_by_hand():
    assert indicators.slope([(0, 1), (1, 3), (2, 5)]) == pytest.approx(2.0)
