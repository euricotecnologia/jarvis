import unittest
from types import SimpleNamespace
from unittest.mock import patch

from jarvis.config import AgentConfig
from jarvis.models import Server
from jarvis.tools.context import ToolContext
from jarvis.tools.ssh_tool import ExecutarNoServidor, ListarServidores


class FakeDB:
    def __init__(self, servers):
        self._servers = servers

    def list_servers(self):
        return list(self._servers)

    def find_server(self, alias):
        for s in self._servers:
            if s.alias.lower() == alias.lower():
                return s
        return None


def _ctx(db):
    return ToolContext(config=AgentConfig(enabled=True, ssh=True), database=db)


class ListarServidoresTests(unittest.IsolatedAsyncioTestCase):
    async def test_lists_aliases(self) -> None:
        db = FakeDB([Server(alias="vps", host="h", user="root", notes="prod")])
        result = await ListarServidores().run({}, _ctx(db))
        self.assertTrue(result.ok)
        self.assertIn("vps", result.content)
        self.assertIn("prod", result.content)

    async def test_empty(self) -> None:
        result = await ListarServidores().run({}, _ctx(FakeDB([])))
        self.assertIn("Nenhum servidor", result.content)


class ExecutarNoServidorTests(unittest.IsolatedAsyncioTestCase):
    def test_always_confirms(self) -> None:
        tool = ExecutarNoServidor()
        self.assertTrue(tool.is_destructive({"servidor": "x", "comando": "ls"}, None))
        self.assertIn("SSH em 'x'", tool.confirm_message({"servidor": "x", "comando": "ls"}))

    async def test_unknown_server(self) -> None:
        db = FakeDB([Server(alias="vps", host="h", user="root")])
        result = await ExecutarNoServidor().run(
            {"servidor": "outra", "comando": "ls"}, _ctx(db)
        )
        self.assertFalse(result.ok)
        self.assertIn("vps", result.content)

    async def test_runs_and_formats_output(self) -> None:
        db = FakeDB([Server(alias="vps", host="h", user="root", auth="key")])
        fake_result = SimpleNamespace(
            exit_code=0, stdout="linux vps 6.1", stderr="", ok=True
        )
        with patch("jarvis.ssh.run_remote", return_value=fake_result):
            result = await ExecutarNoServidor().run(
                {"servidor": "vps", "comando": "uname -a"}, _ctx(db)
            )
        self.assertTrue(result.ok)
        self.assertIn("exit_code=0", result.content)
        self.assertIn("linux vps 6.1", result.content)

    async def test_password_server_without_secret(self) -> None:
        db = FakeDB([Server(alias="vps", host="h", user="root", auth="password")])
        with patch("jarvis.secret_store.decrypt_value", return_value=None):
            result = await ExecutarNoServidor().run(
                {"servidor": "vps", "comando": "id"}, _ctx(db)
            )
        self.assertFalse(result.ok)
        self.assertIn("senha", result.content.lower())


if __name__ == "__main__":
    unittest.main()
