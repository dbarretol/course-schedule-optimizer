from datetime import date, datetime
from itertools import pairwise

import pytest

from conftest import make_course
from course_scheduler.sessions import generate_sessions


def total_hours(sessions):
    return sum(s.hours for s in sessions)


def test_two_slots_per_week_reach_total_hours():
    # Tuesday 12-15 (3h) and Thursday 12-17 (5h): 16h = two full weeks.
    course = make_course(
        start=date(2026, 2, 10),
        hours=16,
        slots=[({1}, "12:00", "15:00"), ({3}, "12:00", "17:00")],
    )
    sessions = generate_sessions(course)
    assert total_hours(sessions) == pytest.approx(16)
    assert len(sessions) == 4
    assert {s.start.weekday() for s in sessions} == {1, 3}
    assert all(s.end > s.start for s in sessions)
    assert all(a.end <= b.start for a, b in pairwise(sessions))


def test_single_day_course():
    sessions = generate_sessions(make_course(hours=9))  # Mondays 09-12
    assert len(sessions) == 3
    assert total_hours(sessions) == pytest.approx(9)


def test_last_session_is_truncated():
    course = make_course(start=date(2026, 2, 10), hours=7, slots=[({1}, "10:00", "15:00")])
    sessions = generate_sessions(course)
    assert [s.hours for s in sessions] == pytest.approx([5, 2])
    assert sessions[1].end == datetime(2026, 2, 17, 12, 0)


def test_starts_on_first_matching_weekday_on_or_after_start_date():
    # Start on a Wednesday; the first Monday session is the following week.
    sessions = generate_sessions(make_course(start=date(2026, 2, 11), hours=3))
    assert sessions[0].start == datetime(2026, 2, 16, 9, 0)


def test_same_day_slots_are_chronological():
    course = make_course(hours=6, slots=[({0}, "14:00", "16:00"), ({0}, "09:00", "10:00")])
    sessions = generate_sessions(course)
    assert [s.start.hour for s in sessions] == [9, 14, 9, 14]


def test_stops_at_max_days_and_warns(caplog):
    sessions = generate_sessions(make_course(hours=100), max_days=14)
    assert len(sessions) == 2
    assert "only 6.00 of 100.00 hours" in caplog.text
