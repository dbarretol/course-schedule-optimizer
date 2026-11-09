import pytest
from conftest import make_course, scheduled

from course_scheduler.models import SolveStatus
from course_scheduler.solver import priority_weights, solve

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
        scheduled(make_course(f"low{i}", priority=2, slots=[({0}, f"{9 + i:02d}:00", f"{10 + i:02d}:00")], hours=1))
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


def test_priority_weights_are_strictly_decreasing():
    weights = priority_weights([1, 2, 3, 4], num_courses=4)
    assert weights[1] > weights[2] > weights[3] > weights[4] == 1
