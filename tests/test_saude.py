import unittest

from jarvis import saude


class SaudeActionTests(unittest.TestCase):
    def test_actions_shape(self) -> None:
        acts = saude.health_actions()
        self.assertGreaterEqual(len(acts), 8)
        for a in acts:
            self.assertTrue(a["id"] and a["label"] and a["description"])
            for f in a["fields"]:
                self.assertIn("key", f)
                self.assertIn("long", f)

    def test_build_prompt_fills_and_frames(self) -> None:
        p = saude.build_prompt("resumir_exame", {"conteudo": "Hb 9,1 / VCM 72"})
        self.assertIn("Hb 9,1", p)
        self.assertIn("rascunho", p.lower())
        self.assertIn("não é diagnóstico", p.lower())

    def test_optional_field_defaulted(self) -> None:
        p = saude.build_prompt("interacoes", {"medicamentos": "varfarina, aas"})
        self.assertIn("varfarina", p)
        self.assertIn("não informado", p)

    def test_required_field_raises(self) -> None:
        with self.assertRaises(ValueError):
            saude.build_prompt("hipoteses", {})

    def test_unknown_action(self) -> None:
        with self.assertRaises(KeyError):
            saude.build_prompt("nope", {})


if __name__ == "__main__":
    unittest.main()
