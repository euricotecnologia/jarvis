import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from jarvis import ssh
from jarvis.models import Server


def _server(**kw):
    base = dict(alias="vps", host="1.2.3.4", user="root", port=2222, auth="key")
    base.update(kw)
    return Server(**base)


class BaseArgvTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = patch.object(ssh, "_ssh_executable", return_value="ssh")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_key_auth_uses_batchmode_and_identity(self) -> None:
        argv = ssh._base_argv(_server(key_path="~/.ssh/id_ed25519"))
        self.assertIn("BatchMode=yes", argv)
        self.assertIn("-i", argv)
        self.assertEqual(argv[-1], "root@1.2.3.4")
        self.assertIn("2222", argv)

    def test_password_auth_no_batchmode(self) -> None:
        argv = ssh._base_argv(_server(auth="password"))
        self.assertNotIn("BatchMode=yes", argv)
        self.assertTrue(any("PreferredAuthentications=password" in a for a in argv))

    def test_agent_auth_batchmode_no_identity(self) -> None:
        argv = ssh._base_argv(_server(auth="agent"))
        self.assertIn("BatchMode=yes", argv)
        self.assertNotIn("-i", argv)


class RunRemoteTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = patch.object(ssh, "_ssh_executable", return_value="ssh")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_returns_result_from_subprocess(self) -> None:
        fake = SimpleNamespace(returncode=0, stdout="ola\n", stderr="")
        with patch("subprocess.run", return_value=fake) as run:
            result = ssh.run_remote(_server(), "echo ola")
        self.assertTrue(result.ok)
        self.assertEqual(result.stdout, "ola")
        argv = run.call_args[0][0]
        self.assertEqual(argv[-1], "echo ola")

    def test_password_auth_sets_askpass_and_cleans_helper(self) -> None:
        captured = {}
        created = []
        real_unlink = __import__("os").unlink

        def fake_run(argv, **kw):
            captured["env"] = kw.get("env", {})
            captured["helper_exists"] = __import__("os").path.exists(
                captured["env"].get("SSH_ASKPASS", "")
            )
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=fake_run):
            ssh.run_remote(_server(auth="password"), "whoami", password="s3cr3t")

        self.assertEqual(captured["env"].get("JARVIS_SSH_PW"), "s3cr3t")
        self.assertEqual(captured["env"].get("SSH_ASKPASS_REQUIRE"), "force")
        self.assertTrue(captured["helper_exists"])
        # helper removido depois
        self.assertFalse(
            __import__("os").path.exists(captured["env"]["SSH_ASKPASS"])
        )

    def test_password_auth_without_password_errors(self) -> None:
        with self.assertRaises(ssh.SSHError):
            ssh.run_remote(_server(auth="password"), "id")

    def test_timeout_becomes_ssh_error(self) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ssh", 5)):
            with self.assertRaises(ssh.SSHError):
                ssh.run_remote(_server(), "sleep 100", timeout=5)

    def test_empty_command_rejected(self) -> None:
        with self.assertRaises(ssh.SSHError):
            ssh.run_remote(_server(), "   ")


if __name__ == "__main__":
    unittest.main()
