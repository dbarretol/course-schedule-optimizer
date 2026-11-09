"""Schedule-clash detection between courses."""

from __future__ import annotations

from collections.abc import Sequence

from course_scheduler.models import ScheduledCourse, Session


def sessions_overlap(first: Sequence[Session], second: Sequence[Session]) -> bool:
    """True if any session of ``first`` overlaps any session of ``second``.

    Both sequences must be sorted by start time. Intervals are half-open: a session
    ending exactly when another starts is not a clash.
    """
    if not first or not second:
        return False
    if first[-1].end <= second[0].start or second[-1].end <= first[0].start:
        return False

    i = j = 0
    while i < len(first) and j < len(second):
        a, b = first[i], second[j]
        if a.start < b.end and b.start < a.end:
            return True
        if a.end <= b.start:
            i += 1
        else:
            j += 1
    return False


def find_conflicts(courses: Sequence[ScheduledCourse]) -> list[tuple[int, int]]:
    """Index pairs ``(i, j)``, ``i < j``, of courses that clash."""
    return [
        (i, j)
        for i in range(len(courses))
        for j in range(i + 1, len(courses))
        if sessions_overlap(courses[i].sessions, courses[j].sessions)
    ]
