"""Plain-text report of a solve result."""

from __future__ import annotations

from collections.abc import Iterable

from course_scheduler.models import ScheduledCourse, SolveResult, SolveStatus

_RULE = "=" * 30
_DATE = "%d/%m/%Y"


def _sorted(courses: Iterable[ScheduledCourse]) -> list[ScheduledCourse]:
    return sorted(courses, key=lambda c: (c.course.priority, c.course.name))


def _line(item: ScheduledCourse) -> str:
    course = item.course
    return f"  [{course.course_id}] {course.name} (priority {course.priority})"


def format_report(result: SolveResult, verbose: bool = False) -> str:
    lines = [_RULE, "OPTIMIZATION RESULT", _RULE]

    if result.status is SolveStatus.FEASIBLE:
        lines.append("Note: time limit reached; the result may not be optimal.")
    elif result.status is SolveStatus.NO_SOLUTION:
        lines.append("No solution found within the time limit.")

    for index, courses in enumerate(result.accounts, start=1):
        lines.append(f"\nACCOUNT {index} ({len(courses)} courses):")
        lines.extend(_line(item) for item in _sorted(courses))

    if result.unassigned:
        lines.append(f"\nUNASSIGNED COURSES ({len(result.unassigned)}):")
        lines.extend(_line(item) for item in _sorted(result.unassigned))
    else:
        lines.append("\nAll courses were assigned.")

    if result.conflicts:
        lines.append(f"\nCLASHES ({len(result.conflicts)} pairs):")
        lines.extend(f"  - {a.course.name} <-> {b.course.name}" for a, b in result.conflicts)

    if verbose:
        lines.append("\nSESSIONS:")
        for index, courses in enumerate(result.accounts, start=1):
            for item in _sorted(courses):
                if not item.sessions:
                    continue
                first = item.sessions[0].start.strftime(_DATE)
                last = item.sessions[-1].start.strftime(_DATE)
                lines.append(
                    f"  [account {index}] [{item.course.course_id}] {item.course.name}: "
                    f"{len(item.sessions)} sessions ({first} -> {last})"
                )

    lines.append("\n" + _RULE)
    return "\n".join(lines)
