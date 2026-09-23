import tempfile
import unittest
from pathlib import Path

from jarvis.database import Database
from jarvis.models import Routine
from jarvis.routines import match_routine_command, seed_default_routines


class MatchRoutineCommandTests(unittest.TestCase):
    NAMES = ["Modo trabalho", "Bom dia", "Backup Projetos"]

    def test_verb_prefix_matches(self) -> None:
        self.assertEqual(
            match_routine_command("rodar modo trabalho", self.NAMES), "Modo trabalho"
        )
        self.assertEqual(
            match_routine_command("executa bom dia agora", self.NAMES), "Bom dia"
        )
        self.assertEqual(
            match_routine_command("inicia a rotina backup projetos", self.NAMES),
            "Backup Projetos",
        )

    def test_wake_prefix_and_accents(self) -> None:
        self.assertEqual(
            match_routine_command("jarvis, rodar Modo Trabalho", self.NAMES),
            "Modo trabalho",
        )
        self.assertEqual(
            match_routine_command("dispara backup projétos", self.NAMES),
            "Backup Projetos",
        )

    def test_explicit_rotina_keyword(self) -> None:
        self.assertEqual(
            match_routine_command("rotina bom dia", self.NAMES), "Bom dia"
        )

    def test_non_command_returns_none(self) -> None:
        self.assertIsNone(match_routine_command("abra o youtube", self.NAMES))
        self.assertIsNone(match_routine_command("que horas sao", self.NAMES))
        self.assertIsNone(
            match_routine_command("rodar um script qualquer", self.NAMES)
        )

    def test_partial_name(self) -> None:
        self.assertEqual(
            match_routine_command("roda trabalho", ["Modo trabalho"]), "Modo trabalho"
        )


class RoutineStoreTests(unittest.TestCase):
    def test_crud_round_trip(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            db = Database(Path(directory) / "jarvis.db")
            db.initialize()

            new_id = db.save_routine(
                Routine(name="Teste", steps=("passo um", "passo dois"), description="d")
            )
            self.assertGreater(new_id, 0)

            fetched = db.get_routine("Teste")
            self.assertIsNotNone(fetched)
            assert fetched is not None
            self.assertEqual(fetched.steps, ("passo um", "passo dois"))

            db.save_routine(
                Routine(id=new_id, name="Teste", steps=("so um passo",))
            )
            self.assertEqual(db.get_routine(new_id).steps, ("so um passo",))

            self.assertEqual([r.name for r in db.list_routines()], ["Teste"])

            db.delete_routine(new_id)
            self.assertEqual(db.list_routines(), [])

    def test_save_by_name_upserts(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            db = Database(Path(directory) / "jarvis.db")
            db.initialize()
            first = db.save_routine(Routine(name="X", steps=("a",)))
            again = db.save_routine(Routine(name="X", steps=("b",)))
            self.assertEqual(first, again)
            self.assertEqual(db.get_routine("X").steps, ("b",))

    def test_seed_runs_once(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            db = Database(Path(directory) / "jarvis.db")
            db.initialize()
            seed_default_routines(db)
            count = len(db.list_routines())
            self.assertGreater(count, 0)
            db.delete_routine(db.list_routines()[0].id)
            seed_default_routines(db)
            self.assertEqual(len(db.list_routines()), count - 1)


if __name__ == "__main__":
    unittest.main()
