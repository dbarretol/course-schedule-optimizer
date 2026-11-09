import random
from datetime import datetime
from itertools import combinations

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


def test_course_with_overlapping_own_blocks():
    # Regression: the last session (10-11) is not the one ending latest (09-17), so a
    # check based on the last session's end missed the clash with 13-14.
    first = [s(10, 9, 17), s(10, 10, 11)]
    second = [s(10, 13, 14)]
    assert sessions_overlap(first, second)
    assert sessions_overlap(second, first)


def test_matches_brute_force():
    rng = random.Random(7)

    def random_course(n):
        slots = []
        for _ in range(rng.randint(1, 3)):
            hour = rng.randint(8, 18)
            slots.append(
                ({rng.randint(0, 6)}, f"{hour:02d}:00", f"{hour + rng.randint(1, 4):02d}:00")
            )
        return scheduled(make_course(str(n), hours=rng.choice([3, 6, 9]), slots=slots))

    courses = [random_course(n) for n in range(60)]
    brute = [
        (i, j)
        for i, j in combinations(range(len(courses)), 2)
        if any(
            a.start < b.end and b.start < a.end
            for a in courses[i].sessions
            for b in courses[j].sessions
        )
    ]
    assert find_conflicts(courses) == brute
    pairwise = [
        (i, j)
        for i, j in combinations(range(len(courses)), 2)
        if sessions_overlap(courses[i].sessions, courses[j].sessions)
    ]
    assert pairwise == brute
