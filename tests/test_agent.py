import tempfile
import unittest
from pathlib import Path

from jarvis.agent import ToolAgent, system_context
from jarvis.config import AgentConfig
from jarvis.models import LLMResponse, Message, ToolCall
from jarvis.tools.context import ToolContext
from jarvis.tools.filesystem import EscreverArquivo, LerArquivo
from jarvis.tools.registry import build_tools


class ScriptedRouter:
    """Devolve `LLMResponse` pre-definidos, um por rodada do agente."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self._index = 0
        self.requests: list = []

    async def chat(self, request, provider_name=None) -> LLMResponse:
        self.requests.append(request)
        response = self._responses[min(self._index, len(self._responses) - 1)]
        self._index += 1
        return response


def _text(content: str) -> LLMResponse:
    return LLMResponse(provider="fake", model="m", content=content)


def _call(name: str, **arguments) -> LLMResponse:
    return LLMResponse(
        provider="fake",
        model="m",
        content="",
        tool_calls=(ToolCall(id=f"c-{name}", name=name, arguments=dict(arguments)),),
    )


async def _no(_message: str) -> bool:
    return False


class SystemContextTests(unittest.TestCase):
    def test_has_date_and_os(self) -> None:
        text = system_context()
        self.assertRegex(text, r"\d{2}/\d{2}/\d{4}")
        self.assertIn("Sistema:", text)


class ToolRegistryTests(unittest.TestCase):
    def test_toggles_control_available_tools(self) -> None:
        read_only = {t.name for t in build_tools(AgentConfig(enabled=True, filesystem_read=True))}
        self.assertIn("ler_arquivo", read_only)
        self.assertNotIn("escrever_arquivo", read_only)

        everything = {
            t.name
            for t in build_tools(
                AgentConfig(
                    enabled=True,
                    filesystem_read=True,
                    filesystem_write=True,
                    shell=True,
                    browser=True,
                )
            )
        }
        self.assertGreaterEqual(
            everything,
            {"escrever_arquivo", "executar_comando", "abrir_site", "pesquisar_web"},
        )
        # shell liga o listar_servidores (read-only, p/ recon) mas NAO o remoto
        self.assertIn("listar_servidores", everything)
        self.assertNotIn("executar_no_servidor", everything)
        self.assertNotIn("listar_servidores", read_only)

        with_ssh = {
            t.name
            for t in build_tools(AgentConfig(enabled=True, shell=True, ssh=True))
        }
        self.assertIn("executar_no_servidor", with_ssh)
        self.assertIn("listar_servidores", with_ssh)


class ShellGuardTests(unittest.IsolatedAsyncioTestCase):
    async def _run(self, command: str):
        from jarvis.tools.shell import ExecutarComando

        return await ExecutarComando().run(
            {"comando": command},
            ToolContext(config=AgentConfig(enabled=True, shell=True)),
        )

    async def test_ssh_command_redirects_to_server_tool(self) -> None:
        for command in ("ssh root@1.2.3.4 ls", "scp a root@h:/tmp",
                        "winget install Microsoft.OpenSSH", "putty -ssh host"):
            result = await self._run(command)
            self.assertFalse(result.ok, command)
            self.assertIn("executar_no_servidor", result.content)

    async def test_normal_dev_commands_pass(self) -> None:
        for command in ("git status", "npm install", "python -m pytest"):
            result = await self._run(command)
            self.assertNotIn("executar_no_servidor", result.content)


class FilesystemToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_write_then_read_within_roots(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            ctx = ToolContext(
                config=AgentConfig(
                    enabled=True, filesystem_write=True, allowed_roots=(directory,)
                )
            )
            target = str(Path(directory) / "nota.txt")
            wrote = await EscreverArquivo().run(
                {"caminho": target, "conteudo": "ola"}, ctx
            )
            self.assertTrue(wrote.ok)
            read = await LerArquivo().run({"caminho": target}, ctx)
            self.assertEqual(read.content, "ola")

    async def test_drive_shorthand_normalizes_to_root(self) -> None:
        from jarvis.tools.context import _normalize_raw_path

        for raw in ("D:", "d:", "disco D", "unidade d:", "raiz do D"):
            self.assertEqual(_normalize_raw_path(raw), "D:\\", raw)
        self.assertEqual(_normalize_raw_path("D:/Projetos"), "D:/Projetos")

    async def test_abrir_pasta_calls_os_open(self) -> None:
        from unittest.mock import patch

        from jarvis.tools.filesystem import AbrirPasta

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            ctx = ToolContext(config=AgentConfig(enabled=True, filesystem_read=True))
            with patch("jarvis.tools.filesystem.os.startfile", create=True) as opener:
                result = await AbrirPasta().run({"caminho": directory}, ctx)
            self.assertTrue(result.ok)
            opener.assert_called_once()

    async def test_write_outside_roots_is_denied(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            ctx = ToolContext(
                config=AgentConfig(
                    enabled=True, filesystem_write=True, allowed_roots=(directory,)
                )
            )
            result = await EscreverArquivo().run(
                {"caminho": "C:/Windows/System32/x.txt", "conteudo": "x"}, ctx
            )
            self.assertFalse(result.ok)
            self.assertIn("fora das pastas permitidas", result.content)


class ToolAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_tool_call_then_answer(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            (Path(directory) / "a.txt").write_text("x", encoding="utf-8")
            (Path(directory) / "b.txt").write_text("y", encoding="utf-8")
            config = AgentConfig(
                enabled=True, filesystem_read=True, allowed_roots=(directory,)
            )
            router = ScriptedRouter(
                [
                    _call("listar_pasta", caminho=directory),
                    _text("Tem dois arquivos: a.txt e b.txt."),
                ]
            )
            agent = ToolAgent(router, config)
            ctx = ToolContext(config=config, confirm=_no)

            deltas, finals, notices = [], [], []
            async for event in agent.run_stream(
                [Message(role="user", content="o que tem na pasta?")],
                build_tools(config),
                ctx,
            ):
                {"delta": deltas, "final": finals, "notice": notices}.get(
                    event.kind, []
                ).append(event.text)

        self.assertEqual(finals, ["Tem dois arquivos: a.txt e b.txt."])
        self.assertTrue("".join(deltas).startswith("Tem dois arquivos"))
        self.assertTrue(any("listar_pasta" in n for n in notices))
        # A 2a chamada ao provedor deve conter a mensagem 'tool' com o resultado.
        second = router.requests[1].messages
        self.assertTrue(any(m.role == "tool" for m in second))
        self.assertTrue(any(m.role == "assistant" and m.tool_calls for m in second))

    async def test_destructive_tool_asks_and_respects_refusal(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            victim = Path(directory) / "importante.txt"
            victim.write_text("nao apague", encoding="utf-8")
            config = AgentConfig(
                enabled=True,
                filesystem_read=True,
                filesystem_write=True,
                allowed_roots=(directory,),
            )
            asked: list[str] = []

            async def confirm(message: str) -> bool:
                asked.append(message)
                return False

            router = ScriptedRouter(
                [
                    _call("apagar", caminho=str(victim)),
                    _text("Ok, nao apaguei nada."),
                ]
            )
            agent = ToolAgent(router, config)
            ctx = ToolContext(config=config, confirm=confirm)
            kinds = [
                event.kind
                async for event in agent.run_stream(
                    [Message(role="user", content="apague o arquivo")],
                    build_tools(config),
                    ctx,
                )
            ]

            self.assertTrue(asked)
            self.assertIn("notice", kinds)
            self.assertTrue(victim.exists())

    async def test_provider_failure_is_not_fatal(self) -> None:
        class Boom:
            async def chat(self, request, provider_name=None):
                raise RuntimeError("503 sobrecarregado")

        agent = ToolAgent(Boom(), AgentConfig(enabled=True))
        events = [
            (e.kind, e.text)
            async for e in agent.run_stream(
                [Message(role="user", content="oi")],
                [],
                ToolContext(config=AgentConfig(enabled=True)),
            )
        ]
        kinds = [k for k, _ in events]
        self.assertIn("final", kinds)
        self.assertIn("error", kinds)
        final = next(t for k, t in events if k == "final")
        self.assertIn("provedor", final.lower())


if __name__ == "__main__":
    unittest.main()
