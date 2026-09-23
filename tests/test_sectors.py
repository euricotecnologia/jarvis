import unittest

from jarvis import sectors


class SectorTests(unittest.TestCase):
    def test_all_industries_present(self) -> None:
        ids = {s["id"] for s in sectors.sector_choices()}
        for expected in (
            "geral", "saude", "juridico", "marketing", "financeiro", "varejo",
            "educacao", "agronegocio", "imobiliario", "contabilidade",
            "consultoria", "programacao",
        ):
            self.assertIn(expected, ids)

    def test_choices_are_ordered_and_shaped(self) -> None:
        choices = sectors.sector_choices()
        self.assertEqual(choices[0]["id"], "geral")
        for c in choices:
            self.assertTrue(c["name"] and c["icon"] and c["tagline"])
            self.assertIsInstance(c["hiddenViews"], list)
            self.assertIsInstance(c["capabilities"], list)

    def test_default_and_unknown(self) -> None:
        self.assertEqual(sectors.get_sector("").id, "geral")
        self.assertEqual(sectors.get_sector("xpto").id, "geral")

    def test_geral_changes_nothing(self) -> None:
        self.assertEqual(sectors.apply_sector("BASE", "geral"), "BASE")
        self.assertEqual(sectors.hidden_views("geral"), [])

    def test_saude_specialises_and_hides_hardware(self) -> None:
        prompt = sectors.apply_sector("BASE", "saude")
        self.assertIn("SETOR: Saúde", prompt)
        self.assertIn("APOIO ao profissional", prompt)
        # trava de segurança presente no prompt
        self.assertIn("RASCUNHO", prompt.upper())
        self.assertIn("sistema", sectors.hidden_views("saude"))

    def test_saude_nav_adds_patient_screens_and_hides_others(self) -> None:
        keys = [n["key"] for n in sectors.nav_items("saude")]
        self.assertIn("pacientes", keys)
        self.assertIn("laudos", keys)
        self.assertNotIn("sistema", keys)
        self.assertNotIn("analises", keys)
        self.assertNotIn("arquivos", keys)
        self.assertEqual(keys[-1], "config")
        # geral não ganha as telas de saúde
        self.assertNotIn("pacientes", [n["key"] for n in sectors.nav_items("geral")])

    def test_saude_hides_cyber_and_dev_profiles(self) -> None:
        self.assertEqual(
            set(sectors.hidden_profiles("saude")), {"seguranca", "desenvolvimento"}
        )
        self.assertEqual(sectors.hidden_profiles("geral"), [])

    def test_every_sector_has_persona_except_geral(self) -> None:
        for sid in sectors.ORDER:
            s = sectors.get_sector(sid)
            if sid == "geral":
                self.assertEqual(s.persona, "")
            else:
                self.assertTrue(s.persona.startswith("SETOR:"))


if __name__ == "__main__":
    unittest.main()
