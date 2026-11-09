import logging
import random
from collections import Counter
from datetime import date, timedelta

import pytest

from conftest import make_course, scheduled
from course_scheduler import solver as solver_module
from course_scheduler.models import SolveStatus
from course_scheduler.solver import Strategy, priority_weights, solve

MONDAY_9_12 = [({0}, "09:00", "12:00")]
MONDAY_10_13 = [({0}, "10:00", "13:00")]
MONDAY_11_14 = [({0}, "11:00", "14:00")]
TUESDAY = [({1}, "09:00", "12:00")]


def ids(courses):
    return {item.course.course_id for item in courses}


def assigned_ids(result):
    return {item.course.course_id for _, item in result.assigned}


def assert_no_clash_within_accounts(result):
    for a, b in result.conflicts:
        for account in result.accounts:
            assert not (a in account and b in account)


def test_two_accounts_absorb_one_clash():
    courses = [
        scheduled(make_course("A", priority=1, slots=MONDAY_9_12)),
        scheduled(make_course("B", priority=2, slots=MONDAY_10_13)),
        scheduled(make_course("C", priority=1, slots=TUESDAY)),
    ]
    result = solve(courses, num_accounts=2)
    assert result.status is SolveStatus.OPTIMAL
    assert assigned_ids(result) == {"A", "B", "C"}
    assert_no_clash_within_accounts(result)


def test_lowest_priority_is_dropped_in_a_three_way_clash():
    courses = [
        scheduled(make_course("high", priority=1, slots=MONDAY_9_12)),
        scheduled(make_course("mid", priority=2, slots=MONDAY_10_13)),
        scheduled(make_course("low", priority=3, slots=MONDAY_11_14)),
    ]
    result = solve(courses, num_accounts=2)
    assert ids(result.unassigned) == {"low"}
    assert_no_clash_within_accounts(result)


def test_one_high_priority_beats_many_low_priority():
    high = scheduled(make_course("high", priority=1, slots=[({0}, "09:00", "18:00")], hours=9))
    lows = [
        scheduled(
            make_course(
                f"low{i}", priority=2, slots=[({0}, f"{9 + i:02d}:00", f"{10 + i:02d}:00")], hours=1
            )
        )
        for i in range(5)
    ]
    result = solve([high, *lows], num_accounts=1)
    assert assigned_ids(result) == {"high"}


def test_single_account():
    courses = [
        scheduled(make_course("A", slots=MONDAY_9_12)),
        scheduled(make_course("B", slots=MONDAY_10_13)),
    ]
    result = solve(courses, num_accounts=1)
    assert len(result.accounts) == 1
    assert len(result.unassigned) == 1


def test_many_priority_levels_do_not_overflow():
    courses = [
        scheduled(make_course("p1", priority=1, slots=[({0}, "09:00", "10:00")], hours=1)),
        scheduled(make_course("p15", priority=15, slots=[({0}, "10:00", "11:00")], hours=1)),
    ]
    result = solve(courses)
    assert assigned_ids(result) == {"p1", "p15"}


def test_empty_input():
    result = solve([], num_accounts=3)
    assert result.status is SolveStatus.OPTIMAL
    assert result.accounts == ((), (), ())
    assert result.unassigned == ()


def test_rejects_zero_accounts():
    with pytest.raises(ValueError):
        solve([], num_accounts=0)


def test_priority_weights_are_minimal_and_lexicographic():
    # Two courses of priority 3, one of priority 2, three of priority 1.
    weights = priority_weights([1, 1, 1, 2, 3, 3])
    assert weights == {3: 1, 2: 3, 1: 6}  # 3 = 1 + 2*1, 6 = 1 + 2*1 + 1*3


def test_priority_weights_ignore_gaps_between_levels():
    assert priority_weights([1, 5, 15]) == {15: 1, 5: 2, 1: 4}


def test_more_than_100_lower_priority_courses_never_beat_one_higher():
    # Regression: with the old fixed base 100, 101 priority-2 courses outweighed one
    # priority-1 course. Here every low course clashes with the high one (a daily
    # 09-10 block for 101 days) and with no other low course (each on its own day).
    start = date(2026, 1, 1)
    every_day = [(set(range(7)), "09:00", "10:00")]
    high = scheduled(make_course("high", priority=1, start=start, hours=101, slots=every_day))
    lows = [
        scheduled(
            make_course(
                f"low{k}", priority=2, start=start + timedelta(days=k), hours=1, slots=every_day
            )
        )
        for k in range(101)
    ]
    result = solve([high, *lows], num_accounts=1, strategy=Strategy.WEIGHTED)
    assert assigned_ids(result) == {"high"}


@pytest.mark.parametrize("seed", range(5))
def test_weighted_and_staged_agree_on_counts_per_priority(seed):
    rng = random.Random(seed)

    def random_course(n):
        hour = rng.randint(8, 18)
        return scheduled(
            make_course(
                str(n),
                priority=rng.randint(1, 4),
                start=date(2026, 3, 2) + timedelta(days=rng.randint(0, 6)),
                hours=rng.choice([2, 4, 6]),
                slots=[({rng.randint(0, 6)}, f"{hour:02d}:00", f"{hour + 2:02d}:00")],
            )
        )

    courses = [random_course(n) for n in range(25)]

    def per_priority(result):
        return Counter(item.course.priority for _, item in result.assigned)

    weighted = solve(courses, num_accounts=2, strategy="weighted")
    staged = solve(courses, num_accounts=2, strategy="staged")
    assert per_priority(weighted) == per_priority(staged)
    assert_no_clash_within_accounts(staged)


def test_auto_falls_back_to_staged_when_weights_are_too_large(monkeypatch, caplog):
    monkeypatch.setattr(solver_module, "MAX_WEIGHTED_OBJECTIVE", 1)
    caplog.set_level(logging.INFO)
    courses = [
        scheduled(make_course("high", priority=1, slots=MONDAY_9_12)),
        scheduled(make_course("mid", priority=2, slots=MONDAY_10_13)),
        scheduled(make_course("low", priority=3, slots=MONDAY_11_14)),
    ]
    result = solve(courses, num_accounts=2)
    assert "one priority level at a time" in caplog.text
    assert ids(result.unassigned) == {"low"}
