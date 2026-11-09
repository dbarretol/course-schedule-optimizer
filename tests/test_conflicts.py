from datetime import datetime

from conftest import make_course, scheduled

from course_scheduler.conflicts import find_conflicts, sessions_overlap
from course_scheduler.models import Session


def s(day, start, end):
    return Session(datetime(2026, 2, day, start), datetime(2026, 2, day, end))


def test_overlapping_sessions_clash():
    assert sessions_overlap([s(10, 12, 15)], [s(10, 14, 17)])


def test_touching_sessions_do_not_clash():
    assert not sessions_overlap([s(10, 12, 15)], [s(10, 15, 18)])


def test_empty_never_clashes():
    assert not sessions_overlap([], [s(10, 9, 10)])


def test_clash_found_late_in_the_lists():
    first = [s(2, 9, 10), s(9, 9, 10), s(16, 9, 10)]
    second = [s(3, 9, 10), s(10, 9, 10), s(16, 9, 10)]
    assert sessions_overlap(first, second)
    assert not sessions_overlap(first, second[:2])


def test_find_conflicts_returns_index_pairs():
    courses = [
        scheduled(make_course("a", slots=[({0}, "09:00", "12:00")])),
        scheduled(make_course("b", slots=[({0}, "11:00", "14:00")])),
        scheduled(make_course("c", slots=[({1}, "09:00", "12:00")])),
        scheduled(make_course("d", slots=[({0}, "12:00", "13:00")])),
    ]
    assert find_conflicts(courses) == [(0, 1), (1, 3)]
