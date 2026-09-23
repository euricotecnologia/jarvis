import unittest

from jarvis import codeassist


class CodeAssistTests(unittest.TestCase):
    def test_actions_have_required_keys(self) -> None:
        acts = codeassist.code_actions()
        self.assertGreaterEqual(len(acts), 5)
        for a in acts:
            self.assertTrue(a["id"] and a["label"] and a["description"])
            for f in a["fields"]:
                self.assertIn("key", f)

    def test_build_prompt_defaults_folder(self) -> None:
        p = codeassist.build_prompt("analisar", {})
        self.assertIn("pasta de trabalho atual", p)

    def test_build_prompt_uses_folder(self) -> None:
        p = codeassist.build_prompt("analisar", {"caminho": "D:/proj"})
        self.assertIn("D:/proj", p)

    def test_optional_alvo_becomes_phrase(self) -> None:
        empty = codeassist.build_prompt("testes", {})
        full = codeassist.build_prompt("testes", {"alvo": "tests/x.py"})
        self.assertNotIn("(", empty.split("executar_testes_locais")[1][:3])
        self.assertIn("tests/x.py", full)

    def test_required_field_raises(self) -> None:
        with self.assertRaises(ValueError):
            codeassist.build_prompt("implementar", {"caminho": "x"})

    def test_unknown_action(self) -> None:
        with self.assertRaises(KeyError):
            codeassist.build_prompt("nope", {})


if __name__ == "__main__":
    unittest.main()
