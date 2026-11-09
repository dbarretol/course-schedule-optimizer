from __future__ import annotations

from datetime import date, time
from pathlib import Path

import pytest

from course_scheduler.models import Course, ScheduledCourse, TimeSlot
from course_scheduler.sessions import generate_sessions

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def make_course(
    course_id: str = "1",
    *,
    name: str | None = None,
    priority: int = 1,
    start: date = date(2026, 2, 9),  # a Monday
    hours: float = 3,
    slots: list[tuple[set[int], str, str]] | None = None,
) -> Course:
    slots = slots or [({0}, "09:00", "12:00")]
    return Course(
        course_id=course_id,
        name=name or f"Course {course_id}",
        priority=priority,
        start_date=start,
        total_hours=hours,
        slots=tuple(
            TimeSlot(frozenset(days), time.fromisoformat(s), time.fromisoformat(e))
            for days, s, e in slots
        ),
    )


def scheduled(course: Course) -> ScheduledCourse:
    return ScheduledCourse(course, generate_sessions(course))


@pytest.fixture
def sample_csv() -> Path:
    return EXAMPLES / "courses.sample.csv"
