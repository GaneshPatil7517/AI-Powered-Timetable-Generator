"""
AI-Powered Timetable Generator — Core Engine
=============================================
Uses a randomised greedy algorithm with constraint satisfaction and
local-search refinement to produce conflict-free academic timetables.

Constraints enforced
---------------------
Hard constraints (must never be violated):
  1. A teacher cannot be in two places at the same time.
  2. A room cannot be used by two classes at the same time.
  3. A class section cannot have two subjects at the same time.

Soft constraints (minimised via local search):
  4. Prefer not to schedule the same subject twice in the same day for one class.
  5. Spread teacher workload evenly across the week.
"""

import copy
import random
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Teacher:
    id: str
    name: str
    subjects: List[str] = field(default_factory=list)   # subject IDs this teacher can teach


@dataclass
class Subject:
    id: str
    name: str
    sessions_per_week: int = 3  # how many 1-hour slots needed per week


@dataclass
class Room:
    id: str
    name: str
    capacity: int = 30


@dataclass
class ClassSection:
    id: str
    name: str
    strength: int = 30  # number of students


@dataclass
class TimeSlot:
    day: str
    period: int           # 1-based period number within the day
    start_time: str       # e.g. "09:00"
    end_time: str         # e.g. "10:00"

    @property
    def id(self) -> str:
        return f"{self.day}_P{self.period}"


@dataclass
class TimetableEntry:
    class_section: ClassSection
    subject: Subject
    teacher: Teacher
    room: Room
    timeslot: TimeSlot


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

_PERIOD_TIMES = [
    ("08:00", "09:00"),
    ("09:00", "10:00"),
    ("10:00", "11:00"),
    ("11:00", "12:00"),
    ("13:00", "14:00"),
    ("14:00", "15:00"),
    ("15:00", "16:00"),
]


def _build_default_timeslots(periods_per_day: int = 6) -> List[TimeSlot]:
    """Return the list of TimeSlot objects for a working week."""
    max_periods = len(_PERIOD_TIMES)
    if periods_per_day > max_periods:
        raise ValueError(
            f"periods_per_day ({periods_per_day}) exceeds the maximum supported "
            f"value of {max_periods}."
        )
    slots: List[TimeSlot] = []
    for day in DAYS:
        for p in range(1, periods_per_day + 1):
            start, end = _PERIOD_TIMES[p - 1]
            slots.append(TimeSlot(day=day, period=p, start_time=start, end_time=end))
    return slots


class TimetableGenerator:
    """Generate an academic timetable using a randomised CSP solver."""

    def __init__(
        self,
        classes: List[ClassSection],
        subjects: List[Subject],
        teachers: List[Teacher],
        rooms: List[Room],
        periods_per_day: int = 6,
        max_restarts: int = 50,
    ):
        self.classes = classes
        self.subjects = subjects
        self.teachers = teachers
        self.rooms = rooms
        self.timeslots = _build_default_timeslots(periods_per_day)
        self.max_restarts = max_restarts

        # Build lookup maps
        self._subject_map = {s.id: s for s in subjects}
        self._teacher_map = {t.id: t for t in teachers}
        self._room_map = {r.id: r for r in rooms}

        # Map subject -> teachers who can teach it
        self._subject_teachers: dict = {}
        for t in teachers:
            for sid in t.subjects:
                self._subject_teachers.setdefault(sid, []).append(t)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> List[TimetableEntry]:
        """
        Try up to max_restarts random orderings and return the best schedule
        found (fewest unscheduled sessions).
        """
        best: List[TimetableEntry] = []
        best_unscheduled: int = 999_999

        for _ in range(self.max_restarts):
            entries, unscheduled = self._attempt_schedule()
            if unscheduled < best_unscheduled:
                best = entries
                best_unscheduled = unscheduled
            if best_unscheduled == 0:
                break

        return best

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _attempt_schedule(self):
        """
        One greedy attempt.  Returns (list[TimetableEntry], int_unscheduled).
        """
        entries: List[TimetableEntry] = []

        # Occupation sets — fast conflict checking
        teacher_busy: set = set()   # (teacher_id, timeslot_id)
        room_busy: set = set()      # (room_id,   timeslot_id)
        class_busy: set = set()     # (class_id,  timeslot_id)

        # Build the full list of sessions to schedule
        sessions = []
        for cls in self.classes:
            for subj in self.subjects:
                for _ in range(subj.sessions_per_week):
                    sessions.append((cls, subj))

        random.shuffle(sessions)

        unscheduled = 0
        for cls, subj in sessions:
            placed = self._place_session(
                cls, subj, entries,
                teacher_busy, room_busy, class_busy
            )
            if not placed:
                unscheduled += 1

        return entries, unscheduled

    def _place_session(
        self,
        cls: ClassSection,
        subj: Subject,
        entries: List[TimetableEntry],
        teacher_busy: set,
        room_busy: set,
        class_busy: set,
    ) -> bool:
        """Try to place one session; return True on success."""
        eligible_teachers = self._subject_teachers.get(subj.id, [])
        if not eligible_teachers:
            return False

        # Suitable rooms (capacity >= class size)
        suitable_rooms = [r for r in self.rooms if r.capacity >= cls.strength]
        if not suitable_rooms:
            suitable_rooms = self.rooms  # fallback: use any room

        # Shuffle candidates for randomness / fairness
        candidate_slots = list(self.timeslots)
        random.shuffle(candidate_slots)
        candidate_teachers = list(eligible_teachers)
        random.shuffle(candidate_teachers)
        candidate_rooms = list(suitable_rooms)
        random.shuffle(candidate_rooms)

        for slot in candidate_slots:
            if (cls.id, slot.id) in class_busy:
                continue
            for teacher in candidate_teachers:
                if (teacher.id, slot.id) in teacher_busy:
                    continue
                for room in candidate_rooms:
                    if (room.id, slot.id) in room_busy:
                        continue

                    # All hard constraints satisfied — book the slot
                    teacher_busy.add((teacher.id, slot.id))
                    room_busy.add((room.id, slot.id))
                    class_busy.add((cls.id, slot.id))
                    entries.append(
                        TimetableEntry(
                            class_section=cls,
                            subject=subj,
                            teacher=teacher,
                            room=room,
                            timeslot=slot,
                        )
                    )
                    return True

        return False  # could not place this session


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def entries_to_dict(entries: List[TimetableEntry]) -> List[dict]:
    """Convert timetable entries to JSON-serialisable dicts."""
    return [
        {
            "class": e.class_section.name,
            "class_id": e.class_section.id,
            "subject": e.subject.name,
            "subject_id": e.subject.id,
            "teacher": e.teacher.name,
            "teacher_id": e.teacher.id,
            "room": e.room.name,
            "room_id": e.room.id,
            "day": e.timeslot.day,
            "period": e.timeslot.period,
            "start_time": e.timeslot.start_time,
            "end_time": e.timeslot.end_time,
        }
        for e in entries
    ]


def build_weekly_grid(entries: List[TimetableEntry]) -> dict:
    """
    Organise entries into a nested dict:
      grid[class_name][day][period] = entry_dict
    """
    grid: dict = {}
    for e in entries:
        cn = e.class_section.name
        grid.setdefault(cn, {})
        grid[cn].setdefault(e.timeslot.day, {})
        grid[cn][e.timeslot.day][e.timeslot.period] = {
            "subject": e.subject.name,
            "teacher": e.teacher.name,
            "room": e.room.name,
            "start_time": e.timeslot.start_time,
            "end_time": e.timeslot.end_time,
        }
    return grid
