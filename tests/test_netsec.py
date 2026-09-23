import unittest

from jarvis import netsec


class NetsecTests(unittest.TestCase):
    def test_actions_have_unique_ids_and_shape(self) -> None:
        ids = [a["id"] for a in netsec.security_actions()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("ping", ids)
        self.assertIn("portas", ids)
        for action in netsec.security_actions():
            self.assertEqual(
                set(action),
                {"id", "label", "icon", "category", "description", "fields"},
            )
            for f in action["fields"]:
                self.assertEqual(
                    set(f), {"key", "label", "placeholder", "optional", "default"}
                )

    def test_build_prompt_fills_placeholders(self) -> None:
        out = netsec.build_prompt("ping", {"alvo": "10.0.0.1"})
        self.assertIn("10.0.0.1", out)
        self.assertIn("autorizado", out.lower())

    def test_optional_field_uses_default(self) -> None:
        out = netsec.build_prompt("portas", {"alvo": "host"})
        self.assertIn("portas: comuns", out)
        out2 = netsec.build_prompt("portas", {"alvo": "host", "portas": "1-1000"})
        self.assertIn("portas: 1-1000", out2)

    def test_missing_required_field_raises(self) -> None:
        with self.assertRaises(ValueError):
            netsec.build_prompt("porta_especifica", {"alvo": "host"})  # falta 'porta'

    def test_no_field_actions_build(self) -> None:
        for aid in ("conexoes", "portas_locais", "meu_ip", "firewall", "latencia"):
            self.assertTrue(netsec.build_prompt(aid, {}))

    def test_unknown_action(self) -> None:
        with self.assertRaises(KeyError):
            netsec.build_prompt("nao_existe", {})


class RunActionTests(unittest.TestCase):
    def test_dispatches_to_netscan(self) -> None:
        from unittest.mock import patch

        with patch("jarvis.netscan.ping",
                   return_value={"host": "h", "reachable": True,
                                 "loss_pct": "0", "avg_ms": "5", "raw": "pong"}):
            out = netsec.run_action("ping", {"alvo": "h"})
        self.assertIn("latencia media: 5 ms", out)
        self.assertIn("pong", out)

    def test_scan_formatter(self) -> None:
        from unittest.mock import patch

        fake = {"host": "h", "ip": "1.2.3.4", "checked": 47,
                "open": [{"port": 3389, "service": "RDP", "banner": "",
                          "risky_if_public": True}]}
        with patch("jarvis.netscan.scan_ports", return_value=fake):
            out = netsec.run_action("portas", {"alvo": "h"})
        self.assertIn("3389/tcp  RDP", out)
        self.assertIn("arriscada", out)

    def test_collect_failure_is_contained(self) -> None:
        from unittest.mock import patch

        with patch("jarvis.netscan.whois_query", side_effect=OSError("boom")):
            out = netsec.run_action("whois", {"dominio": "x.com"})
        self.assertIn("falhou", out)


if __name__ == "__main__":
    unittest.main()
