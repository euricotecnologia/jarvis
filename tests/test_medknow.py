import unittest

from jarvis import medknow


class DrugInteractionTests(unittest.TestCase):
    def test_known_grave_interaction(self) -> None:
        rows = medknow.check_interactions(["Varfarina", "AAS"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["gravidade"], "grave")

    def test_alias_and_class_matching(self) -> None:
        # aspirina -> AAS ; clonazepam -> benzodiazepínico
        rows = medknow.check_interactions(["aspirina", "ibuprofeno"])
        self.assertTrue(rows)
        rows2 = medknow.check_interactions(["morfina", "clonazepam"])
        self.assertTrue(any(r["gravidade"] == "grave" for r in rows2))

    def test_contraindicado_sorts_first(self) -> None:
        rows = medknow.check_interactions(["sildenafila", "mononitrato de isossorbida", "AAS", "ibuprofeno"])
        self.assertEqual(rows[0]["gravidade"], "contraindicado")

    def test_no_interaction(self) -> None:
        self.assertEqual(medknow.check_interactions(["paracetamol", "vitamina C"]), [])
        self.assertEqual(medknow.check_interactions(["só um"]), [])


class CidTests(unittest.TestCase):
    def test_by_code(self) -> None:
        res = medknow.cid_search("E11")
        self.assertTrue(res)
        self.assertEqual(res[0]["code"], "E11")

    def test_by_text(self) -> None:
        res = medknow.cid_search("pneumonia")
        self.assertTrue(res)
        self.assertTrue(any("pneumonia" in r["description"].lower() for r in res))

    def test_short_query_empty(self) -> None:
        self.assertEqual(medknow.cid_search("a"), [])

    def test_dataset_loaded(self) -> None:
        self.assertGreater(len(medknow._cid10()), 9000)


class CalcTests(unittest.TestCase):
    def test_bmi(self) -> None:
        r = medknow.bmi(72, 1.70)
        self.assertEqual(r["valor"], 24.9)
        self.assertEqual(r["categoria"], "eutrófico")

    def test_bmi_accepts_cm(self) -> None:
        self.assertEqual(medknow.bmi(72, 170)["valor"], 24.9)

    def test_cockcroft(self) -> None:
        r = medknow.cockcroft_gault(65, 70, 1.4, female=False)
        self.assertTrue(40 < r["valor"] < 60)

    def test_invalid_raises(self) -> None:
        with self.assertRaises(ValueError):
            medknow.bmi(0, 1.7)


if __name__ == "__main__":
    unittest.main()
