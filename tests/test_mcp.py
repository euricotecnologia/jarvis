import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from jarvis.database import Database
from jarvis.mcp import MCPClient, MCPError, MCPManager

_FAKE_SERVER = textwrap.dedent(
    """
    import sys, json
    def send(o): sys.stdout.write(json.dumps(o) + "\\n"); sys.stdout.flush()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        m = json.loads(line)
        method, mid = m.get("method"), m.get("id")
        if method == "initialize":
            send({"jsonrpc":"2.0","id":mid,"result":{
                "protocolVersion":"2024-11-05","capabilities":{},
                "serverInfo":{"name":"fake","version":"9"}}})
        elif method == "notifications/initialized":
            pass
        elif method == "tools/list":
            send({"jsonrpc":"2.0","id":mid,"result":{"tools":[
                {"name":"soma","description":"soma a+b",
                 "inputSchema":{"type":"object","properties":{
                    "a":{"type":"number"},"b":{"type":"number"}}}}]}})
        elif method == "tools/call":
            p = m["params"]
            if p["name"] == "soma":
                a = p["arguments"]
                send({"jsonrpc":"2.0","id":mid,"result":{"content":[
                    {"type":"text","text":str(a["a"] + a["b"])}]}})
            else:
                send({"jsonrpc":"2.0","id":mid,"result":{
                    "content":[{"type":"text","text":"erro"}],"isError":True}})
        else:
            send({"jsonrpc":"2.0","id":mid,"error":{"code":-32601,"message":"?"}})
    """
)


class MCPClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.mkdtemp()
        cls.server = Path(cls.tmp) / "fake_mcp.py"
        cls.server.write_text(_FAKE_SERVER, encoding="utf-8")

    def _client(self) -> MCPClient:
        return MCPClient(sys.executable, [str(self.server)])

    def test_handshake_and_tools(self) -> None:
        c = self._client()
        c.start(timeout=15)
        try:
            self.assertEqual(c.server_info.get("name"), "fake")
            names = [t["name"] for t in c.list_tools()]
            self.assertEqual(names, ["soma"])
            self.assertEqual(c.call_tool("soma", {"a": 2, "b": 40}), "42")
        finally:
            c.close()

    def test_tool_error_is_flagged(self) -> None:
        c = self._client()
        c.start(timeout=15)
        try:
            out = c.call_tool("inexistente", {})
            self.assertIn("erro", out.lower())
        finally:
            c.close()

    def test_bad_command_raises(self) -> None:
        c = MCPClient("comando_que_nao_existe_xyz", [])
        with self.assertRaises(MCPError):
            c.start(timeout=5)


class MCPManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.server = Path(self.tmp) / "fake_mcp.py"
        self.server.write_text(_FAKE_SERVER, encoding="utf-8")
        self.db = Database(Path(self.tmp) / "t.db")
        self.db.initialize()
        self.db.save_mcp_server({
            "name": "calc", "command": sys.executable,
            "args": json.dumps([str(self.server)]), "env_vars": "{}",
            "enabled": True,
        })
        self.mgr = MCPManager(self.db)

    def tearDown(self) -> None:
        self.mgr.shutdown()

    def test_probe_ok(self) -> None:
        res = self.mgr.probe({
            "name": "calc", "command": sys.executable,
            "args": json.dumps([str(self.server)]), "env_vars": "{}",
        })
        self.assertTrue(res["ok"])
        self.assertEqual([t["name"] for t in res["tools"]], ["soma"])

    def test_dynamic_tools_and_call(self) -> None:
        import asyncio

        from jarvis.config import AgentConfig
        from jarvis.tools.context import ToolContext

        tools = self.mgr.load_active_mcp_tools()
        self.assertEqual([t.name for t in tools], ["mcp_calc_soma"])
        self.assertTrue(tools[0].is_destructive({}, None))
        result = asyncio.run(
            tools[0].run({"a": 5, "b": 5}, ToolContext(config=AgentConfig(enabled=True)))
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.content, "10")

    def test_disabled_server_gives_no_tools(self) -> None:
        rows = self.db.list_mcp_servers()
        self.db.save_mcp_server({**rows[0], "enabled": False})
        self.mgr.invalidate()
        self.assertEqual(self.mgr.load_active_mcp_tools(), [])

    def test_invalidate_closes_live_clients(self) -> None:
        self.mgr.load_active_mcp_tools(force=True)
        client = self.mgr._clients["calc"]
        self.assertTrue(client._alive)
        self.mgr.invalidate()
        self.assertEqual(self.mgr._clients, {})
        self.assertFalse(client._alive)
        self.assertIsNone(client._proc)

    def test_edit_takes_effect_without_restart(self) -> None:
        # servidor 2, com uma ferramenta de nome diferente
        server2 = Path(self.tmp) / "fake_mcp2.py"
        server2.write_text(_FAKE_SERVER.replace('"soma"', '"soma2"'), encoding="utf-8")
        self.mgr.load_active_mcp_tools(force=True)
        self.assertEqual(
            [t.name for t in self.mgr.load_active_mcp_tools(force=True)],
            ["mcp_calc_soma"],
        )
        rows = self.db.list_mcp_servers()
        self.db.save_mcp_server(
            {**rows[0], "args": json.dumps([str(server2)])}
        )
        self.mgr.invalidate()
        self.assertEqual(
            [t.name for t in self.mgr.load_active_mcp_tools(force=True)],
            ["mcp_calc_soma2"],
        )

    def test_shutdown_kills_subprocess(self) -> None:
        self.mgr.load_active_mcp_tools(force=True)
        proc = self.mgr._clients["calc"]._proc
        self.assertIsNotNone(proc)
        self.assertIsNone(proc.poll())  # vivo
        self.mgr.shutdown()
        self.assertEqual(self.mgr._clients, {})
        self.assertIsNotNone(proc.poll())  # encerrado


if __name__ == "__main__":
    unittest.main()
