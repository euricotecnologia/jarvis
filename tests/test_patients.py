import tempfile
import unittest
from datetime import date
from pathlib import Path

from jarvis import patients
from jarvis.database import Database


class PatientHelperTests(unittest.TestCase):
    def test_age_from_iso_and_br(self) -> None:
        t = date(2026, 9, 1)
        self.assertEqual(patients.age_from("1990-09-02", today=t), 35)
        self.assertEqual(patients.age_from("02/09/1990", today=t), 35)
        self.assertEqual(patients.age_from("1990-08-31", today=t), 36)
        self.assertIsNone(patients.age_from("", today=t))
        self.assertIsNone(patients.age_from("lixo", today=t))

    def test_patient_context_is_confidential_and_compact(self) -> None:
        ctx = patients.patient_context(
            {"name": "Ana", "birthdate": "2000-01-01", "sex": "F",
             "allergies": "dipirona", "conditions": "asma", "medications": "",
             "blood_type": "A+"},
            today=date(2026, 9, 1),
        )
        self.assertIn("confidencial", ctx.lower())
        self.assertIn("Ana", ctx)
        self.assertIn("26 anos", ctx)
        self.assertIn("dipirona", ctx)
        self.assertNotIn("Medicações", ctx)  # vazio não entra

    def test_analyze_prompt_has_guardrails_and_content(self) -> None:
        system, user = patients.analyze_record_prompt(
            {"name": "Ana", "birthdate": "2000-01-01", "conditions": "asma",
             "medications": "varfarina, AAS"},
            [],
            {"kind": "laudo", "title": "Rx tórax", "occurred_at": "2026-08-10",
             "body": "opacidade em base direita"},
            ["Creatinina 1,9"],
            today=date(2026, 9, 1),
        )
        self.assertIn("APOIO", system)
        self.assertIn("não substitui", system.lower())
        self.assertIn("opacidade em base direita", user)
        self.assertIn("Creatinina 1,9", user)
        self.assertIn("nivel_risco", user)  # pede JSON estruturado
        # interação local (varfarina x AAS) entra no contexto
        self.assertIn("INTERAÇÕES DETECTADAS", user)

    def test_parse_and_format_analysis(self) -> None:
        raw = ('```json\n{"nivel_risco":"critico","alertas":["anafilaxia"],'
               '"resumo":"reação grave","conduta_sugerida":["adrenalina IM"],'
               '"cid_sugeridos":[{"code":"T78.2","description":"choque anafilático",'
               '"confianca":"alta","justificativa":"quadro"}]}\n```')
        a = patients.parse_analysis(raw)
        self.assertEqual(a["nivel_risco"], "critico")
        full, resumo, flags = patients.format_analysis(a)
        self.assertIn("CRÍTICO", full)
        self.assertIn("T78.2", full)
        self.assertIn("adrenalina IM", full)
        self.assertEqual(flags, "anafilaxia")

    def test_parse_analysis_survives_garbage(self) -> None:
        a = patients.parse_analysis("desculpe, não entendi")
        full, resumo, flags = patients.format_analysis(a)
        self.assertIn("não entendi", full)


class PatientDbTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Database(Path(tempfile.mkdtemp()) / "p.db")
        self.db.initialize()

    def test_patient_crud(self) -> None:
        pid = self.db.save_patient({"name": "João", "document": "123", "allergies": "AAS"})
        self.assertGreater(pid, 0)
        self.assertEqual(self.db.get_patient(pid)["allergies"], "AAS")
        self.db.save_patient({"id": pid, "name": "João Silva", "allergies": "AAS, iodo"})
        self.assertEqual(self.db.get_patient(pid)["name"], "João Silva")
        self.assertEqual(len(self.db.list_patients("silva")), 1)
        self.assertEqual(len(self.db.list_patients("nao-existe")), 0)

    def test_new_clinical_fields_persist(self) -> None:
        pid = self.db.save_patient({
            "name": "Ana", "background": "tabagista 20 maços-ano",
            "family_background": "IAM precoce no pai", "cns": "123",
            "city": "Campinas/SP", "insurance": "Unimed",
        })
        p = self.db.get_patient(pid)
        self.assertEqual(p["background"], "tabagista 20 maços-ano")
        self.assertEqual(p["family_background"], "IAM precoce no pai")
        self.assertEqual(p["city"], "Campinas/SP")

    def test_record_vitals_and_ai_json(self) -> None:
        pid = self.db.save_patient({"name": "Bia"})
        rid = self.db.save_patient_record({
            "patient_id": pid, "kind": "consulta", "title": "Retorno",
            "vitals": '{"pa": "120/80", "fc": "72"}',
        })
        self.assertEqual(self.db.get_patient_record(rid)["vitals"], '{"pa": "120/80", "fc": "72"}')
        self.db.set_record_ai(rid, "resumo", "alerta", '{"nivel_risco": "baixo"}')
        r = self.db.get_patient_record(rid)
        self.assertEqual(r["ai_json"], '{"nivel_risco": "baixo"}')

    def test_records_and_files_cascade(self) -> None:
        pid = self.db.save_patient({"name": "Ana"})
        rid = self.db.save_patient_record(
            {"patient_id": pid, "kind": "laudo", "title": "Hemograma", "body": "Hb 9"}
        )
        fid = self.db.add_record_file(
            {"record_id": rid, "patient_id": pid, "name": "l.pdf", "path": "/x/l.pdf",
             "mime": "document", "size": 10, "extracted_text": "texto"}
        )
        self.assertEqual(len(self.db.list_patient_records(pid)), 1)
        self.assertEqual(len(self.db.list_record_files(rid)), 1)
        self.db.set_record_ai(rid, "resumo", "alerta")
        self.assertEqual(self.db.get_patient_record(rid)["ai_summary"], "resumo")
        # apagar o paciente leva registros e arquivos junto (ON DELETE CASCADE)
        self.db.delete_patient(pid)
        self.assertEqual(self.db.list_patient_records(pid), [])
        self.assertIsNone(self.db.get_record_file(fid))


if __name__ == "__main__":
    unittest.main()
