"""
Unit tests for the AI-Powered Timetable Generator.
"""

import pytest

from timetable_generator import (
    ClassSection,
    Room,
    Subject,
    Teacher,
    TimeSlot,
    TimetableEntry,
    TimetableGenerator,
    build_weekly_grid,
    entries_to_dict,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_config():
    classes = [
        ClassSection(id="cs_a", name="CS-A", strength=30),
    ]
    subjects = [
        Subject(id="math",    name="Mathematics",       sessions_per_week=2),
        Subject(id="english", name="English",            sessions_per_week=2),
    ]
    teachers = [
        Teacher(id="t1", name="Alice", subjects=["math"]),
        Teacher(id="t2", name="Bob",   subjects=["english"]),
    ]
    rooms = [
        Room(id="r1", name="Room 1", capacity=40),
    ]
    return classes, subjects, teachers, rooms


@pytest.fixture
def multi_class_config():
    classes = [
        ClassSection(id="cs_a", name="CS-A", strength=30),
        ClassSection(id="cs_b", name="CS-B", strength=30),
    ]
    subjects = [
        Subject(id="math",    name="Mathematics",    sessions_per_week=3),
        Subject(id="physics", name="Physics",        sessions_per_week=2),
        Subject(id="cs",      name="Computer Sci",   sessions_per_week=3),
    ]
    teachers = [
        Teacher(id="t1", name="Alice",  subjects=["math"]),
        Teacher(id="t2", name="Bob",    subjects=["physics"]),
        Teacher(id="t3", name="Carol",  subjects=["cs"]),
        Teacher(id="t4", name="Dave",   subjects=["math", "physics"]),
    ]
    rooms = [
        Room(id="r1", name="Room 1", capacity=40),
        Room(id="r2", name="Room 2", capacity=40),
    ]
    return classes, subjects, teachers, rooms


# ---------------------------------------------------------------------------
# TimetableGenerator tests
# ---------------------------------------------------------------------------

class TestTimetableGenerator:

    def test_returns_list(self, simple_config):
        classes, subjects, teachers, rooms = simple_config
        gen = TimetableGenerator(classes, subjects, teachers, rooms)
        result = gen.generate()
        assert isinstance(result, list)

    def test_schedules_all_sessions(self, simple_config):
        classes, subjects, teachers, rooms = simple_config
        gen = TimetableGenerator(classes, subjects, teachers, rooms, max_restarts=20)
        entries = gen.generate()

        # Total required sessions = sum of sessions_per_week for each class × subject
        expected = len(classes) * sum(s.sessions_per_week for s in subjects)
        assert len(entries) == expected, (
            f"Expected {expected} entries, got {len(entries)}"
        )

    def test_no_teacher_conflict(self, multi_class_config):
        """A teacher must never be in two places at the same time."""
        classes, subjects, teachers, rooms = multi_class_config
        gen = TimetableGenerator(classes, subjects, teachers, rooms, max_restarts=30)
        entries = gen.generate()

        seen = set()
        for e in entries:
            key = (e.teacher.id, e.timeslot.id)
            assert key not in seen, (
                f"Teacher conflict: {e.teacher.name} double-booked on {e.timeslot.id}"
            )
            seen.add(key)

    def test_no_room_conflict(self, multi_class_config):
        """A room must never be used by two classes at the same time."""
        classes, subjects, teachers, rooms = multi_class_config
        gen = TimetableGenerator(classes, subjects, teachers, rooms, max_restarts=30)
        entries = gen.generate()

        seen = set()
        for e in entries:
            key = (e.room.id, e.timeslot.id)
            assert key not in seen, (
                f"Room conflict: {e.room.name} double-booked on {e.timeslot.id}"
            )
            seen.add(key)

    def test_no_class_conflict(self, multi_class_config):
        """A class section must never have two sessions at the same time."""
        classes, subjects, teachers, rooms = multi_class_config
        gen = TimetableGenerator(classes, subjects, teachers, rooms, max_restarts=30)
        entries = gen.generate()

        seen = set()
        for e in entries:
            key = (e.class_section.id, e.timeslot.id)
            assert key not in seen, (
                f"Class conflict: {e.class_section.name} double-booked on {e.timeslot.id}"
            )
            seen.add(key)

    def test_teacher_only_teaches_assigned_subjects(self, multi_class_config):
        """Each entry must pair a teacher with a subject they are qualified to teach."""
        classes, subjects, teachers, rooms = multi_class_config
        gen = TimetableGenerator(classes, subjects, teachers, rooms, max_restarts=30)
        entries = gen.generate()

        for e in entries:
            assert e.subject.id in e.teacher.subjects, (
                f"{e.teacher.name} is not qualified to teach {e.subject.name}"
            )

    def test_no_subject_without_teacher(self):
        """Sessions with no eligible teacher should simply not be scheduled."""
        classes  = [ClassSection(id="c1", name="C1", strength=20)]
        subjects = [Subject(id="orphan", name="Orphan Subject", sessions_per_week=2)]
        teachers = [Teacher(id="t1", name="Alice", subjects=["math"])]  # can't teach "orphan"
        rooms    = [Room(id="r1", name="Room 1", capacity=30)]

        gen = TimetableGenerator(classes, subjects, teachers, rooms, max_restarts=5)
        entries = gen.generate()
        # No entries should be produced for the orphaned subject
        assert entries == []

    def test_room_capacity_preferred(self):
        """When a room is too small, it should still be used as a fallback."""
        classes  = [ClassSection(id="c1", name="C1", strength=50)]
        subjects = [Subject(id="math", name="Math", sessions_per_week=1)]
        teachers = [Teacher(id="t1", name="Alice", subjects=["math"])]
        rooms    = [Room(id="r1", name="Small Room", capacity=20)]  # smaller than class

        gen = TimetableGenerator(classes, subjects, teachers, rooms, max_restarts=10)
        entries = gen.generate()
        # Should still schedule (fallback to any room)
        assert len(entries) == 1


# ---------------------------------------------------------------------------
# Serialisation tests
# ---------------------------------------------------------------------------

class TestSerialisationHelpers:

    def _make_entry(self):
        cls  = ClassSection(id="cs_a", name="CS-A", strength=30)
        subj = Subject(id="math", name="Mathematics", sessions_per_week=3)
        tchr = Teacher(id="t1", name="Alice", subjects=["math"])
        room = Room(id="r1", name="Room 1", capacity=40)
        slot = TimeSlot(day="Monday", period=1, start_time="08:00", end_time="09:00")
        return TimetableEntry(cls, subj, tchr, room, slot)

    def test_entries_to_dict_keys(self):
        entry = self._make_entry()
        result = entries_to_dict([entry])
        assert len(result) == 1
        d = result[0]
        for key in ("class", "subject", "teacher", "room", "day", "period",
                    "start_time", "end_time"):
            assert key in d, f"Missing key: {key}"

    def test_entries_to_dict_values(self):
        entry = self._make_entry()
        d = entries_to_dict([entry])[0]
        assert d["class"]      == "CS-A"
        assert d["subject"]    == "Mathematics"
        assert d["teacher"]    == "Alice"
        assert d["room"]       == "Room 1"
        assert d["day"]        == "Monday"
        assert d["period"]     == 1
        assert d["start_time"] == "08:00"
        assert d["end_time"]   == "09:00"

    def test_build_weekly_grid_structure(self):
        entry = self._make_entry()
        grid = build_weekly_grid([entry])
        assert "CS-A" in grid
        assert "Monday" in grid["CS-A"]
        assert 1 in grid["CS-A"]["Monday"]
        cell = grid["CS-A"]["Monday"][1]
        assert cell["subject"] == "Mathematics"
        assert cell["teacher"] == "Alice"
        assert cell["room"]    == "Room 1"

    def test_timeslot_id(self):
        slot = TimeSlot(day="Friday", period=3, start_time="10:00", end_time="11:00")
        assert slot.id == "Friday_P3"


# ---------------------------------------------------------------------------
# Flask API tests
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


class TestFlaskAPI:

    def test_index_returns_200(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert b"Timetable" in res.data

    def test_sample_endpoint(self, client):
        res = client.get("/api/sample")
        assert res.status_code == 200
        data = res.get_json()
        for key in ("classes", "subjects", "teachers", "rooms"):
            assert key in data
            assert len(data[key]) > 0

    def test_generate_valid_payload(self, client):
        payload = {
            "classes":  [{"id": "c1", "name": "Class 1", "strength": 30}],
            "subjects": [{"id": "math", "name": "Mathematics", "sessions_per_week": 2}],
            "teachers": [{"id": "t1", "name": "Alice", "subjects": ["math"]}],
            "rooms":    [{"id": "r1", "name": "Room 1", "capacity": 40}],
            "periods_per_day": 5,
        }
        res = client.post(
            "/api/generate",
            json=payload,
        )
        assert res.status_code == 200
        data = res.get_json()
        assert "entries" in data
        assert "grid" in data
        assert "stats" in data
        assert data["stats"]["total_entries"] == 2

    def test_generate_missing_classes_returns_422(self, client):
        payload = {
            "subjects": [{"id": "math", "name": "Mathematics"}],
            "teachers": [{"id": "t1", "name": "Alice", "subjects": ["math"]}],
            "rooms":    [{"id": "r1", "name": "Room 1", "capacity": 40}],
        }
        res = client.post("/api/generate", json=payload)
        assert res.status_code == 422

    def test_generate_empty_body_returns_400(self, client):
        res = client.post(
            "/api/generate",
            data="not json",
            content_type="text/plain",
        )
        assert res.status_code == 400

    def test_generate_no_conflicts(self, client):
        """Integration test: generated timetable must be conflict-free."""
        res = client.get("/api/sample")
        sample = res.get_json()
        gen_res = client.post("/api/generate", json=sample)
        assert gen_res.status_code == 200
        entries = gen_res.get_json()["entries"]

        teacher_slots: set = set()
        room_slots:    set = set()
        class_slots:   set = set()

        for e in entries:
            slot = f"{e['day']}_P{e['period']}"

            tk = (e["teacher_id"], slot)
            assert tk not in teacher_slots, f"Teacher conflict: {e['teacher']} at {slot}"
            teacher_slots.add(tk)

            rk = (e["room_id"], slot)
            assert rk not in room_slots, f"Room conflict: {e['room']} at {slot}"
            room_slots.add(rk)

            ck = (e["class_id"], slot)
            assert ck not in class_slots, f"Class conflict: {e['class']} at {slot}"
            class_slots.add(ck)
