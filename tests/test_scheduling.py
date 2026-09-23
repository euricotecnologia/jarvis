import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from jarvis.database import Database
from jarvis.models import Routine, Schedule
from jarvis.scheduling import (
    build_schedule,
    describe_schedule,
    is_due,
    is_missed,
    next_occurrence,
)


class IsDueTests(unittest.TestCase):
    def test_once_fires_after_target(self) -> None:
        s = Schedule(routine_id=1, kind="once", run_at="2026-08-31T08:00")
        self.assertFalse(is_due(s, datetime(2026, 8, 31, 7, 59)))
        self.assertTrue(is_due(s, datetime(2026, 8, 31, 8, 0)))
        self.assertTrue(is_due(s, datetime(2026, 8, 31, 9, 30)))

    def test_once_does_not_refire(self) -> None:
        s = Schedule(
            routine_id=1,
            kind="once",
            run_at="2026-08-31T08:00",
            last_run_at="2026-08-31T08:00:05",
        )
        self.assertFalse(is_due(s, datetime(2026, 8, 31, 10, 0)))

    def test_daily_fires_once_per_day(self) -> None:
        s = Schedule(routine_id=1, kind="daily", time_of_day="08:00")
        self.assertFalse(is_due(s, datetime(2026, 8, 31, 7, 30)))
        self.assertTrue(is_due(s, datetime(2026, 8, 31, 8, 1)))
        ran = Schedule(
            routine_id=1,
            kind="daily",
            time_of_day="08:00",
            last_run_at="2026-08-31T08:01:00",
        )
        self.assertFalse(is_due(ran, datetime(2026, 8, 31, 20, 0)))
        self.assertTrue(is_due(ran, datetime(2026, 9, 1, 8, 5)))

    def test_weekly_only_on_weekday(self) -> None:
        # 2026-08-31 e uma segunda-feira (weekday 0)
        s = Schedule(routine_id=1, kind="weekly", time_of_day="09:00", weekday=0)
        self.assertTrue(is_due(s, datetime(2026, 8, 31, 9, 0)))
        self.assertFalse(is_due(s, datetime(2026, 9, 1, 9, 0)))  # terca

    def test_disabled_never_due(self) -> None:
        s = Schedule(
            routine_id=1, kind="daily", time_of_day="08:00", enabled=False
        )
        self.assertFalse(is_due(s, datetime(2026, 8, 31, 8, 1)))


class MissedAndNextTests(unittest.TestCase):
    def test_is_missed_after_window(self) -> None:
        s = Schedule(routine_id=1, kind="once", run_at="2026-08-31T08:00")
        self.assertFalse(is_missed(s, datetime(2026, 8, 31, 12, 0)))
        self.assertTrue(is_missed(s, datetime(2026, 9, 1, 21, 0)))

    def test_next_occurrence_daily(self) -> None:
        s = Schedule(routine_id=1, kind="daily", time_of_day="08:00")
        nxt = next_occurrence(s, datetime(2026, 8, 31, 9, 0))
        self.assertEqual(nxt, datetime(2026, 9, 1, 8, 0))


class BuildAndDescribeTests(unittest.TestCase):
    def test_build_once(self) -> None:
        future = (datetime.now() + timedelta(days=2)).strftime("%d/%m/%Y")
        s = build_schedule(3, "once", date_text=future, time_text="07:30")
        self.assertEqual(s.kind, "once")
        self.assertTrue(s.run_at.endswith("07:30"))

    def test_build_rejects_past(self) -> None:
        with self.assertRaises(ValueError):
            build_schedule(3, "once", date_text="01/01/2020", time_text="07:30")

    def test_build_weekly_requires_weekday(self) -> None:
        with self.assertRaises(ValueError):
            build_schedule(3, "weekly", time_text="07:30", weekday=None)
        s = build_schedule(3, "weekly", time_text="07:30", weekday=2)
        self.assertEqual((s.kind, s.weekday), ("weekly", 2))

    def test_build_rejects_bad_time(self) -> None:
        with self.assertRaises(ValueError):
            build_schedule(3, "daily", time_text="99:99")

    def test_describe(self) -> None:
        self.assertEqual(
            describe_schedule(Schedule(routine_id=1, kind="daily", time_of_day="08:00")),
            "Todo dia às 08:00",
        )
        self.assertIn(
            "quarta",
            describe_schedule(
                Schedule(routine_id=1, kind="weekly", time_of_day="08:00", weekday=2)
            ),
        )


class ScheduleStoreTests(unittest.TestCase):
    def test_upsert_and_clear(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            db = Database(Path(directory) / "jarvis.db")
            db.initialize()
            rid = db.save_routine(Routine(name="R", steps=("x",)))

            db.set_schedule(Schedule(routine_id=rid, kind="daily", time_of_day="08:00"))
            self.assertEqual(db.get_schedule(rid).time_of_day, "08:00")

            db.set_schedule(Schedule(routine_id=rid, kind="daily", time_of_day="09:15"))
            self.assertEqual(db.get_schedule(rid).time_of_day, "09:15")
            self.assertEqual(len(db.list_schedules()), 1)

            db.mark_schedule_ran(db.get_schedule(rid).id, "2026-08-31T09:15:00", disable=False)
            self.assertEqual(db.get_schedule(rid).last_run_at, "2026-08-31T09:15:00")

            db.clear_schedule(rid)
            self.assertIsNone(db.get_schedule(rid))

    def test_schedule_cascades_on_routine_delete(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            db = Database(Path(directory) / "jarvis.db")
            db.initialize()
            rid = db.save_routine(Routine(name="R", steps=("x",)))
            db.set_schedule(Schedule(routine_id=rid, kind="daily", time_of_day="08:00"))
            db.delete_routine(rid)
            self.assertEqual(db.list_schedules(), [])


if __name__ == "__main__":
    unittest.main()
