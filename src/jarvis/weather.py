"""Clima atual via Open-Meteo (gratis, sem chave de API).

Duas chamadas: geocodificação do nome da cidade e previsão atual. O resultado
fica em cache por 15 minutos. Falha de rede não lanca exceção para a interface:
devolve `WeatherReport(ok=False, ...)` com a mensagem do erro.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from typing import Any

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
_TIMEOUT = 8.0
_CACHE_TTL = 900.0

# Códigos WMO -> (descrição pt-BR, chave de icone)
_WMO: dict[int, tuple[str, str]] = {
    0: ("Ceu limpo", "sun"),
    1: ("Predominantemente limpo", "sun"),
    2: ("Parcialmente nublado", "cloud-sun"),
    3: ("Nublado", "cloud"),
    45: ("Nevoeiro", "fog"),
    48: ("Nevoeiro com geada", "fog"),
    51: ("Garoa fraca", "drizzle"),
    53: ("Garoa moderada", "drizzle"),
    55: ("Garoa forte", "drizzle"),
    56: ("Garoa congelante", "drizzle"),
    57: ("Garoa congelante forte", "drizzle"),
    61: ("Chuva fraca", "rain"),
    63: ("Chuva moderada", "rain"),
    65: ("Chuva forte", "rain"),
    66: ("Chuva congelante", "rain"),
    67: ("Chuva congelante forte", "rain"),
    71: ("Neve fraca", "snow"),
    73: ("Neve moderada", "snow"),
    75: ("Neve forte", "snow"),
    77: ("Granizo fino", "snow"),
    80: ("Pancadas de chuva fracas", "rain"),
    81: ("Pancadas de chuva", "rain"),
    82: ("Pancadas de chuva fortes", "rain"),
    85: ("Pancadas de neve", "snow"),
    86: ("Pancadas de neve fortes", "snow"),
    95: ("Tempestade", "storm"),
    96: ("Tempestade com granizo", "storm"),
    99: ("Tempestade forte com granizo", "storm"),
}


@dataclass(frozen=True, slots=True)
class WeatherReport:
    city: str = ""
    region: str = ""
    temperature_c: float = 0.0
    feels_like_c: float = 0.0
    humidity: int = 0
    wind_kmh: float = 0.0
    description: str = "--"
    icon: str = "cloud"
    is_day: bool = True
    updated_at: str = ""
    ok: bool = False
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["temperature_c"] = round(self.temperature_c)
        data["feels_like_c"] = round(self.feels_like_c)
        data["wind_kmh"] = round(self.wind_kmh)
        return data


def _get_json(url: str, params: dict[str, Any]) -> Any:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}", headers={"User-Agent": "JarvisPessoal/1.0"}
    )
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def describe_code(code: int, is_day: bool = True) -> tuple[str, str]:
    text, icon = _WMO.get(int(code), ("Tempo indefinido", "cloud"))
    if icon == "sun" and not is_day:
        icon = "moon"
    return text, icon


def _fetch(city: str) -> WeatherReport:
    name = (city or "").strip()
    if not name:
        return WeatherReport(error="Nenhuma cidade configurada.")
    try:
        geo = _get_json(
            _GEOCODE_URL,
            {"name": name, "count": 1, "language": "pt", "format": "json"},
        )
    except Exception as exc:  # noqa: BLE001
        return WeatherReport(city=name, error=f"Falha ao localizar a cidade: {exc}")

    results = geo.get("results") if isinstance(geo, dict) else None
    if not results:
        return WeatherReport(city=name, error=f'Cidade "{name}" não encontrada.')
    place = results[0]
    lat, lon = place.get("latitude"), place.get("longitude")

    try:
        forecast = _get_json(
            _FORECAST_URL,
            {
                "latitude": lat,
                "longitude": lon,
                "current": (
                    "temperature_2m,relative_humidity_2m,apparent_temperature,"
                    "weather_code,wind_speed_10m,is_day"
                ),
                "wind_speed_unit": "kmh",
                "timezone": "auto",
            },
        )
    except Exception as exc:  # noqa: BLE001
        return WeatherReport(
            city=place.get("name", name), error=f"Falha ao obter a previsão: {exc}"
        )

    current = forecast.get("current", {}) if isinstance(forecast, dict) else {}
    is_day = bool(current.get("is_day", 1))
    description, icon = describe_code(current.get("weather_code", 3), is_day)
    region = " / ".join(
        piece
        for piece in (place.get("admin1"), place.get("country_code"))
        if piece
    )
    return WeatherReport(
        city=place.get("name", name),
        region=region,
        temperature_c=float(current.get("temperature_2m", 0.0)),
        feels_like_c=float(current.get("apparent_temperature", 0.0)),
        humidity=int(current.get("relative_humidity_2m", 0)),
        wind_kmh=float(current.get("wind_speed_10m", 0.0)),
        description=description,
        icon=icon,
        is_day=is_day,
        updated_at=time.strftime("%H:%M"),
        ok=True,
    )


class WeatherService:
    """Cache simples por cidade (TTL de 15 min)."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, WeatherReport]] = {}

    def get(self, city: str, *, force: bool = False) -> WeatherReport:
        key = (city or "").strip().lower()
        now = time.monotonic()
        cached = self._cache.get(key)
        if cached and not force and now - cached[0] < _CACHE_TTL and cached[1].ok:
            return cached[1]
        report = _fetch(city)
        if report.ok or key not in self._cache:
            self._cache[key] = (now, report)
        return report
