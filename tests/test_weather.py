import io
import json
import unittest
from unittest.mock import patch

from jarvis.weather import WeatherService, describe_code


class DescribeCodeTests(unittest.TestCase):
    def test_known_codes(self) -> None:
        self.assertEqual(describe_code(0, True), ("Ceu limpo", "sun"))
        self.assertEqual(describe_code(0, False)[1], "moon")
        self.assertEqual(describe_code(95)[0], "Tempestade")

    def test_unknown_code(self) -> None:
        text, icon = describe_code(1234)
        self.assertEqual(icon, "cloud")


def _fake_urlopen(geocode: dict, forecast: dict):
    def opener(request, timeout=0):
        url = request.full_url if hasattr(request, "full_url") else request
        payload = geocode if "geocoding-api" in url else forecast
        return io.BytesIO(json.dumps(payload).encode("utf-8"))

    return opener


class WeatherServiceTests(unittest.TestCase):
    GEO = {"results": [{"name": "Sao Paulo", "latitude": -23.5, "longitude": -46.6,
                        "admin1": "Sao Paulo", "country_code": "BR"}]}
    FORECAST = {"current": {"temperature_2m": 21.4, "relative_humidity_2m": 88,
                            "apparent_temperature": 23.1, "weather_code": 3,
                            "wind_speed_10m": 6.0, "is_day": 1}}

    def test_fetch_builds_report(self) -> None:
        with patch("urllib.request.urlopen", _fake_urlopen(self.GEO, self.FORECAST)):
            report = WeatherService().get("Sao Paulo")
        self.assertTrue(report.ok)
        self.assertEqual(report.city, "Sao Paulo")
        self.assertEqual(report.region, "Sao Paulo / BR")
        self.assertEqual(report.temperature_c, 21.4)
        self.assertEqual(report.description, "Nublado")
        data = report.as_dict()
        self.assertEqual(data["temperature_c"], 21)

    def test_cache_avoids_second_call(self) -> None:
        calls = {"n": 0}

        def opener(request, timeout=0):
            calls["n"] += 1
            url = request.full_url
            payload = self.GEO if "geocoding-api" in url else self.FORECAST
            return io.BytesIO(json.dumps(payload).encode("utf-8"))

        service = WeatherService()
        with patch("urllib.request.urlopen", opener):
            service.get("Sao Paulo")
            first = calls["n"]
            service.get("Sao Paulo")
        self.assertEqual(calls["n"], first)

    def test_network_failure_returns_not_ok(self) -> None:
        def opener(request, timeout=0):
            raise OSError("offline")

        with patch("urllib.request.urlopen", opener):
            report = WeatherService().get("Sao Paulo")
        self.assertFalse(report.ok)
        self.assertIn("localizar", report.error)

    def test_empty_city(self) -> None:
        report = WeatherService().get("")
        self.assertFalse(report.ok)


if __name__ == "__main__":
    unittest.main()
