import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from jarvis.whatsapp import WhatsAppManager


class TestWhatsAppManager(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        self.manager = WhatsAppManager(self.base_dir)

    def tearDown(self) -> None:
        self.manager.stop_bridge()
        self.temp_dir.cleanup()

    def test_init_defaults(self) -> None:
        self.assertEqual(self.manager.port, 25874)
        self.assertEqual(self.manager.base_url, "http://127.0.0.1:25874")
        self.assertFalse(self.manager.is_bridge_installed())

    def test_status_fallback_when_offline(self) -> None:
        status = self.manager.get_status()
        self.assertEqual(status.get("status"), "disconnected")
        self.assertFalse(status.get("connected"))

    @patch("urllib.request.urlopen")
    def test_send_message_mock(self, mock_urlopen: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"success": true, "messageId": "TEST1234"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        res = self.manager.send_message("551999999999", "Ola teste")
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("messageId"), "TEST1234")


if __name__ == "__main__":
    unittest.main()
