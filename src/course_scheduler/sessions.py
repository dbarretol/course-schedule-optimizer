"""Expand a course's weekly time slots into concrete sessions."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime, timedelta

from course_scheduler.models import Course, ScheduledCourse, Session

logger = logging.getLogger(__name__)

MAX_DAYS_AHEAD = 365
_EPSILON_HOURS = 1e-9


def generate_sessions(course: Course, max_days: int = MAX_DAYS_AHEAD) -> tuple[Session, ...]:
    """Walk forward from ``course.start_date`` creating one session per matching slot
    until ``course.total_hours`` is reached. The last session is shortened so the
    total is exact. Sessions are returned in chronological order.
    """
    slots = sorted(course.slots, key=lambda slot: (slot.start, slot.end))
    remaining = course.total_hours
    sessions: list[Session] = []
    day = course.start_date
    last_day = day + timedelta(days=max_days)

    while remaining > _EPSILON_HOURS and day < last_day:
        weekday = day.weekday()
        for slot in slots:
            if weekday not in slot.weekdays:
                continue
            start = datetime.combine(day, slot.start)
            end = datetime.combine(day, slot.end)
            hours = (end - start).total_seconds() / 3600.0
            if hours > remaining:
                end = start + timedelta(hours=remaining)
                hours = remaining
            sessions.append(Session(start, end))
            remaining -= hours
            if remaining <= _EPSILON_HOURS:
                break
        day += timedelta(days=1)

    if remaining > _EPSILON_HOURS:
        logger.warning(
            "Course %s (%s): only %.2f of %.2f hours fit within %d days",
            course.course_id, course.name, course.total_hours - remaining,
            course.total_hours, max_days,
        )
    return tuple(sessions)


def schedule_courses(
    courses: Iterable[Course], max_days: int = MAX_DAYS_AHEAD
) -> list[ScheduledCourse]:
    """Attach generated sessions to every course."""
    return [ScheduledCourse(course, generate_sessions(course, max_days)) for course in courses]
