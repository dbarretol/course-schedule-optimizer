"""Schedule-clash detection between courses.

Sessions are half-open intervals: a session ending exactly when another starts is not
a clash.
"""

from __future__ import annotations

import heapq
from collections.abc import Sequence
from datetime import datetime
from itertools import combinations

from course_scheduler.models import ScheduledCourse, Session


def sessions_overlap(first: Sequence[Session], second: Sequence[Session]) -> bool:
    """True if any session of ``first`` overlaps any session of ``second``.

    Both sequences must be sorted by start time. Sessions of one course may overlap
    each other (two blocks on the same day), so this sweeps both lists in start order
    and remembers the latest end seen on each side: a session clashes with the other
    side if it starts before that side's latest end.
    """
    if not first or not second:
        return False
    tagged = heapq.merge(
        ((session, 0) for session in first),
        ((session, 1) for session in second),
        key=lambda pair: pair[0].start,
    )
    latest_end: list[datetime | None] = [None, None]
    for session, side in tagged:
        other_end = latest_end[1 - side]
        if other_end is not None and session.start < other_end:
            return True
        own_end = latest_end[side]
        if own_end is None or session.end > own_end:
            latest_end[side] = session.end
    return False


def find_conflicts(courses: Sequence[ScheduledCourse]) -> list[tuple[int, int]]:
    """Index pairs ``(i, j)``, ``i < j``, of courses that clash, in sorted order."""
    return [
        (i, j)
        for i, j in combinations(range(len(courses)), 2)
        if sessions_overlap(courses[i].sessions, courses[j].sessions)
    ]
