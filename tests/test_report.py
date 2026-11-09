from conftest import make_course, scheduled
from course_scheduler.models import SolveResult, SolveStatus
from course_scheduler.report import format_report

A = scheduled(make_course("1", name="Alpha", priority=2, hours=6))
B = scheduled(make_course("2", name="Beta", priority=1, hours=3))
C = scheduled(make_course("3", name="Gamma", priority=3, hours=3))


def result(status=SolveStatus.OPTIMAL, unassigned=(C,)):
    return SolveResult(status, ((A, B), ()), unassigned, ((A, C),))


def test_accounts_are_sorted_by_priority_then_name():
    text = format_report(result())
    assert text.index("[2] Beta") < text.index("[1] Alpha")
    assert "ACCOUNT 1 (2 courses):" in text
    assert "ACCOUNT 2 (0 courses):" in text


def test_lists_unassigned_and_clashes():
    text = format_report(result())
    assert "UNASSIGNED COURSES (1):\n  [3] Gamma (priority 3)" in text
    assert "CLASHES (1 pairs):\n  - Alpha <-> Gamma" in text


def test_all_assigned_message():
    assert "All courses were assigned." in format_report(result(unassigned=()))


def test_status_notes():
    assert "may not be optimal" in format_report(result(SolveStatus.FEASIBLE))
    assert "No solution found" in format_report(result(SolveStatus.NO_SOLUTION))
    assert "Note:" not in format_report(result())


def test_verbose_lists_sessions_per_assigned_course():
    text = format_report(result(), verbose=True)
    assert "[account 1] [1] Alpha: 2 sessions (09/02/2026 -> 16/02/2026)" in text
    assert "Gamma: " not in text.split("SESSIONS:")[1]


def test_report_is_ascii_for_ascii_names():
    assert format_report(result(), verbose=True).isascii()
