import socket
import threading
import unittest

from jarvis import netscan


class PortSpecTests(unittest.TestCase):
    def test_presets(self) -> None:
        self.assertGreater(len(netscan.resolve_ports_spec("comuns")), 20)
        self.assertEqual(netscan.resolve_ports_spec("web")[:2], [80, 443])
        self.assertEqual(len(netscan.resolve_ports_spec("todas")), 65535)

    def test_list_and_range(self) -> None:
        self.assertEqual(netscan.resolve_ports_spec("22,80,443"), [22, 80, 443])
        self.assertEqual(netscan.resolve_ports_spec("1-5"), [1, 2, 3, 4, 5])
        self.assertEqual(netscan.resolve_ports_spec("80 443\t22"), [80, 443, 22])

    def test_garbage_falls_back(self) -> None:
        self.assertEqual(
            netscan.resolve_ports_spec("xyz"), netscan.resolve_ports_spec("comuns")
        )


class HelperTests(unittest.TestCase):
    def test_grab_first_group(self) -> None:
        self.assertEqual(netscan._grab("Registrar: Foo Inc", r"Registrar:\s*(.+)"),
                         "Foo Inc")
        self.assertEqual(netscan._grab("nope", r"x:\s*(.+)"), "")

    def test_name_from_cert(self) -> None:
        field = ((("commonName", "example.com"),), (("organizationName", "ACME"),))
        self.assertEqual(
            netscan._name_from_cert(field),
            "commonName=example.com, organizationName=ACME",
        )

    def test_days_until_none_on_junk(self) -> None:
        self.assertIsNone(netscan._days_until("not a date"))


class LivePortScanTests(unittest.TestCase):
    """Scan de verdade contra um socket local aberto neste teste."""

    def setUp(self) -> None:
        self.srv = socket.socket()
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(1)
        self.port = self.srv.getsockname()[1]
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self) -> None:
        try:
            while True:
                conn, _ = self.srv.accept()
                conn.close()
        except OSError:
            pass

    def tearDown(self) -> None:
        self.srv.close()

    def test_finds_open_port_and_misses_closed(self) -> None:
        result = netscan.scan_ports(
            "127.0.0.1", f"{self.port},{self.port + 1}", timeout=0.5
        )
        opened = [p["port"] for p in result["open"]]
        self.assertIn(self.port, opened)

    def test_check_single_port(self) -> None:
        self.assertTrue(netscan.check_single_port("127.0.0.1", self.port)["open"])
        # porta quase certamente fechada
        self.assertFalse(netscan.check_single_port("127.0.0.1", 1)["open"])


class HttpHeaderAnalysisTests(unittest.TestCase):
    def test_missing_headers_flagged(self) -> None:
        import io
        from email.message import Message
        from unittest.mock import patch

        msg = Message()
        msg["Server"] = "nginx"
        msg["Strict-Transport-Security"] = "max-age=1"

        class Resp:
            status = 200
            headers = msg

            def geturl(self):
                return "https://x"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self, *a):
                return b""

        with patch("urllib.request.urlopen", return_value=Resp()):
            out = netscan.http_headers("x")
        self.assertEqual(out["server"], "nginx")
        self.assertIn("strict-transport-security", out["security_headers_present"])
        self.assertIn("content-security-policy", out["security_headers_missing"])


if __name__ == "__main__":
    unittest.main()
