import os
import unittest
from unittest.mock import patch

from jarvis import sysinfo
from jarvis.sysinfo import _fmt_bytes, _fmt_uptime, _is_protected


class FormatTests(unittest.TestCase):
    def test_fmt_bytes(self) -> None:
        self.assertEqual(_fmt_bytes(512), "512 B")
        self.assertEqual(_fmt_bytes(1536 * 1024), "1.5 MB")

    def test_fmt_uptime(self) -> None:
        self.assertEqual(_fmt_uptime(90), "1m")
        self.assertEqual(_fmt_uptime(3660), "1h 1m")
        self.assertEqual(_fmt_uptime(90061), "1d 1h 1m")


class ProtectionTests(unittest.TestCase):
    def test_protects_system_and_self(self) -> None:
        self.assertTrue(_is_protected("System", 4))
        self.assertTrue(_is_protected("csrss.exe", 999))
        self.assertTrue(_is_protected("anything", os.getpid()))

    def test_allows_normal_process(self) -> None:
        self.assertFalse(_is_protected("firefox.exe", 12345))

    def test_kill_refuses_protected(self) -> None:
        result = sysinfo.kill_process(4)
        self.assertFalse(result["ok"])


class ProcessListTests(unittest.TestCase):
    def test_returns_rows_without_idle(self) -> None:
        rows = sysinfo.list_processes("memory", limit=10)
        self.assertIsInstance(rows, list)
        for row in rows:
            self.assertIn("pid", row)
            self.assertIn("cpuText", row)
            self.assertIn("memText", row)
            self.assertNotEqual(row["name"].lower(), "system idle process")

    def test_sort_by_memory(self) -> None:
        rows = sysinfo.list_processes("memory", limit=10)
        if len(rows) >= 2:
            self.assertGreaterEqual(rows[0]["memBytes"], rows[1]["memBytes"])


class DisksAndPowerTests(unittest.TestCase):
    def test_disks_structure(self) -> None:
        data = sysinfo.disks()
        self.assertIn("volumes", data)
        self.assertIn("temp", data)
        self.assertIn("recycle", data)
        for volume in data["volumes"]:
            self.assertIn("percent", volume)
            self.assertIn("freeText", volume)

    def test_power_status_has_plans_key(self) -> None:
        status = sysinfo.power_status()
        self.assertIn("plans", status)
        self.assertIn("hasBattery", status)


class PowerPlanParsingTests(unittest.TestCase):
    def test_parses_powercfg_output(self) -> None:
        sample = (
            "Esquemas de Energia Existentes (* Ativos)\n"
            "-----------------------------------\n"
            "GUID do Esquema de Energia: 381b4222-f694-41f0-9685-ff5bb260df2e  (Equilibrado) *\n"
            "GUID do Esquema de Energia: a1841308-3541-4fab-bc81-f71556f20b4a  (Economia de energia)\n"
        )
        with patch("jarvis.sysinfo._run", return_value=sample), \
             patch("jarvis.sysinfo.sys.platform", "win32"):
            plans, active = sysinfo._power_plans()
        self.assertEqual(len(plans), 2)
        self.assertEqual(active, "381b4222-f694-41f0-9685-ff5bb260df2e")
        self.assertEqual(plans[1]["name"], "Economia de energia")


class QuickActionTests(unittest.TestCase):
    def test_unknown_action(self) -> None:
        self.assertFalse(sysinfo.run_quick_action("nao_existe")["ok"])

    def test_set_power_plan_rejects_bad_guid(self) -> None:
        result = sysinfo.set_power_plan("xxx")
        self.assertFalse(result["ok"])


class SpecsTests(unittest.TestCase):
    def test_full_specs_structure(self) -> None:
        specs = sysinfo.full_specs()
        self.assertIn("hardware", specs)
        self.assertIn("system", specs)
        self.assertIn("gpu", specs)
        if specs["available"]:
            labels = [row["k"] for row in specs["hardware"]]
            self.assertIn("Processador", labels)
            self.assertTrue(all(isinstance(row["v"], str) for row in specs["hardware"]))


if __name__ == "__main__":
    unittest.main()
