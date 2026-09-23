import unittest

from jarvis import profiles


class ProfileCatalogTests(unittest.TestCase):
    def test_order_and_ids(self) -> None:
        ids = [c["id"] for c in profiles.profile_choices()]
        self.assertEqual(ids, ["normal", "seguranca", "desenvolvimento"])

    def test_get_profile_falls_back_to_default(self) -> None:
        self.assertEqual(profiles.get_profile("inexistente").id, "normal")
        self.assertEqual(profiles.get_profile("").id, "normal")

    def test_choice_dict_shape(self) -> None:
        for choice in profiles.profile_choices():
            self.assertEqual(
                set(choice),
                {"id", "name", "icon", "tagline", "description",
                 "needsFolder", "capabilities"},
            )


class PermissionBundleTests(unittest.TestCase):
    def test_normal_is_read_only_no_shell(self) -> None:
        prefs = profiles.get_profile("normal").permission_prefs()
        self.assertTrue(prefs["agent_enabled"])
        self.assertTrue(prefs["agent_fs_read"])
        self.assertFalse(prefs["agent_fs_write"])
        self.assertFalse(prefs["agent_shell"])
        self.assertTrue(prefs["agent_browser"])
        self.assertEqual(prefs["agent_allowed_roots"], [])

    def test_security_has_shell_but_no_write_no_ssh(self) -> None:
        prefs = profiles.get_profile("seguranca").permission_prefs()
        self.assertTrue(prefs["agent_shell"])
        self.assertFalse(prefs["agent_fs_write"])
        self.assertFalse(prefs["agent_ssh"])
        self.assertEqual(prefs["agent_allowed_roots"], [])

    def test_dev_needs_folder_and_scopes_roots(self) -> None:
        profile = profiles.get_profile("desenvolvimento")
        self.assertTrue(profile.needs_folder)
        prefs = profile.permission_prefs(folder="D:/proj")
        self.assertTrue(prefs["agent_fs_write"])
        self.assertTrue(prefs["agent_shell"])
        self.assertTrue(prefs["agent_ssh"])
        self.assertEqual(prefs["agent_allowed_roots"], ["D:/proj"])
        self.assertEqual(
            profile.permission_prefs(folder="")["agent_allowed_roots"], []
        )

    def test_only_dev_enables_ssh(self) -> None:
        self.assertFalse(profiles.get_profile("normal").permission_prefs()["agent_ssh"])
        self.assertFalse(profiles.get_profile("seguranca").permission_prefs()["agent_ssh"])
        self.assertTrue(profiles.get_profile("desenvolvimento").permission_prefs()["agent_ssh"])


class SystemPromptTests(unittest.TestCase):
    def test_persona_appended_to_base(self) -> None:
        out = profiles.compose_system_prompt(
            "Voce e o Jarvis.", profiles.get_profile("seguranca")
        )
        self.assertTrue(out.startswith("Voce e o Jarvis."))
        self.assertIn("Ciberseguranca", out)
        self.assertIn("AUTORIZADOS", out)

    def test_dev_folder_is_substituted(self) -> None:
        out = profiles.compose_system_prompt(
            "base", profiles.get_profile("desenvolvimento"), folder="C:/app"
        )
        self.assertIn("C:/app", out)
        self.assertNotIn("{folder}", out)

    def test_dev_without_folder_has_placeholder_text(self) -> None:
        out = profiles.compose_system_prompt(
            "base", profiles.get_profile("desenvolvimento")
        )
        self.assertIn("nenhuma pasta", out)


if __name__ == "__main__":
    unittest.main()
