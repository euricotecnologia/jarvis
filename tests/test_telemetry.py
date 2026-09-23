import unittest
from unittest.mock import patch

from jarvis import telemetry
from jarvis.telemetry import Metric, SystemMonitor, _fmt_uptime


class HelperTests(unittest.TestCase):
    def test_fmt_uptime(self) -> None:
        self.assertEqual(_fmt_uptime(90), "1m")
        self.assertEqual(_fmt_uptime(3660), "1h 1m")
        self.assertEqual(_fmt_uptime(90000), "1d 1h 0m")

    def test_metric_as_dict_rounds(self) -> None:
        data = Metric(percent=41.678, primary="42%", label="CPU").as_dict()
        self.assertEqual(data["percent"], 41.7)
        self.assertEqual(data["primary"], "42%")


class GpuParseTests(unittest.TestCase):
    def test_query_gpu_parses_nvidia_smi(self) -> None:
        class Result:
            stdout = "17, 2048, 24564, NVIDIA GeForce RTX 5090 Laptop GPU\n"

        with (
            patch("jarvis.telemetry.shutil.which", return_value="nvidia-smi"),
            patch("jarvis.telemetry.subprocess.run", return_value=Result()),
        ):
            metric = telemetry._query_gpu()
        self.assertIsNotNone(metric)
        assert metric is not None
        self.assertEqual(metric.percent, 17.0)
        self.assertEqual(metric.label, "RTX 5090 Laptop GPU")
        self.assertIn("GB", metric.secondary)

    def test_query_gpu_returns_none_without_binary(self) -> None:
        with patch("jarvis.telemetry.shutil.which", return_value=None):
            self.assertIsNone(telemetry._query_gpu())

    def test_query_gpu_returns_none_on_error(self) -> None:
        with (
            patch("jarvis.telemetry.shutil.which", return_value="nvidia-smi"),
            patch(
                "jarvis.telemetry.subprocess.run", side_effect=OSError("boom")
            ),
        ):
            self.assertIsNone(telemetry._query_gpu())


class SampleTests(unittest.TestCase):
    def test_sample_without_psutil_is_unavailable(self) -> None:
        with patch.object(telemetry, "psutil", None):
            stats = SystemMonitor().sample()
        self.assertFalse(stats.available)
        self.assertEqual(stats.as_dict()["available"], False)

    def test_network_rate_is_computed_between_samples(self) -> None:
        monitor = SystemMonitor()
        times = iter([100.0, 101.0])

        class Counters:
            def __init__(self, sent: int, recv: int) -> None:
                self.bytes_sent = sent
                self.bytes_recv = recv

        counters = iter([Counters(0, 0), Counters(1_000_000, 25_000_000)])
        with (
            patch("jarvis.telemetry.time.monotonic", lambda: next(times)),
            patch("jarvis.telemetry.psutil.net_io_counters", lambda: next(counters)),
        ):
            monitor._network()
            metric, down, up = monitor._network()
        self.assertAlmostEqual(down, 25_000_000 * 8 / 1e6, places=1)
        self.assertAlmostEqual(up, 1_000_000 * 8 / 1e6, places=1)
        self.assertIn("Mbps", metric.primary)


if __name__ == "__main__":
    unittest.main()
