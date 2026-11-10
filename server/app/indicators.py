from datetime import datetime

MOVING_AVERAGE_WINDOW = 5


def _points(readings: list[dict]) -> list[tuple[float, float]]:
    """Converte as leituras em pares (minutos desde a primeira, temperatura)."""
    valid = [r for r in readings if r["temp_c"] is not None]
    if not valid:
        return []
    start = datetime.fromisoformat(valid[0]["received_at"])
    return [
        ((datetime.fromisoformat(r["received_at"]) - start).total_seconds() / 60, r["temp_c"])
        for r in valid
    ]


def slope(points: list[tuple[float, float]]) -> float | None:
    """Inclinação da reta de mínimos quadrados."""
    n = len(points)
    if n < 2:
        return None
    mean_x = sum(x for x, _ in points) / n
    mean_y = sum(y for _, y in points) / n
    spread = sum((x - mean_x) ** 2 for x, _ in points)
    if spread == 0:
        return None
    return sum((x - mean_x) * (y - mean_y) for x, y in points) / spread


def moving_average(points: list[tuple[float, float]], window: int) -> list[tuple[float, float]]:
    averaged = []
    for i in range(window - 1, len(points)):
        chunk = points[i - window + 1:i + 1]
        averaged.append((sum(x for x, _ in chunk) / window, sum(y for _, y in chunk) / window))
    return averaged


def rate_per_minute(readings: list[dict]) -> float | None:
    return slope(moving_average(_points(readings), MOVING_AVERAGE_WINDOW))


def minutes_to_critical(readings: list[dict], critical_c: float) -> float | None:
    points = _points(readings)
    rate = slope(points)
    if rate is None or rate <= 0:
        return None
    current = points[-1][1]
    return max((critical_c - current) / rate, 0.0)
