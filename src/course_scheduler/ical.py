"""Export sessions to iCalendar (RFC 5545) and CSV."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from course_scheduler.models import ScheduledCourse

PRODID = "-//course-schedule-optimizer//EN"
_UID_DOMAIN = "course-schedule-optimizer"
_LOCAL_FORMAT = "%Y%m%dT%H%M%S"
_MAX_LINE_OCTETS = 75


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> list[str]:
    """Split a content line into chunks of at most 75 octets (RFC 5545 section 3.1)."""
    chunks: list[str] = []
    current = ""
    limit = _MAX_LINE_OCTETS
    for char in line:
        if len((current + char).encode("utf-8")) > limit:
            chunks.append(current)
            current = char
            limit = _MAX_LINE_OCTETS - 1  # continuation lines start with a space
        else:
            current += char
    chunks.append(current)
    return [chunks[0], *(" " + chunk for chunk in chunks[1:])]


def build_calendar(
    courses: Iterable[ScheduledCourse],
    account_of: dict[str, int] | None = None,
    now: datetime | None = None,
) -> str:
    """Return the ``.ics`` text with one event per session.

    Times are floating local times (no time zone), so calendar apps show them as written.
    ``account_of`` maps ``course_id`` to a 1-based account number, added as a category.
    """
    stamp = (now or datetime.now(UTC)).astimezone(UTC).strftime(_LOCAL_FORMAT) + "Z"
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}", "CALSCALE:GREGORIAN"]

    for item in courses:
        course = item.course
        total = len(item.sessions)
        for number, session in enumerate(item.sessions, start=1):
            start = session.start.strftime(_LOCAL_FORMAT)
            lines += [
                "BEGIN:VEVENT",
                f"UID:{_escape(course.course_id)}-{number}-{start}@{_UID_DOMAIN}",
                f"DTSTAMP:{stamp}",
                f"DTSTART:{start}",
                f"DTEND:{session.end.strftime(_LOCAL_FORMAT)}",
                f"SUMMARY:{_escape(course.name)}",
                f"DESCRIPTION:{_escape(f'Session {number} of {total}')}",
            ]
            if account_of and course.course_id in account_of:
                lines.append(f"CATEGORIES:Account {account_of[course.course_id]}")
            lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "".join(chunk + "\r\n" for line in lines for chunk in _fold(line))


def write_calendar(
    path: str | Path,
    courses: Iterable[ScheduledCourse],
    account_of: dict[str, int] | None = None,
) -> None:
    text = build_calendar(courses, account_of)
    Path(path).write_text(text, encoding="utf-8", newline="")


def write_sessions_csv(path: str | Path, courses: Iterable[ScheduledCourse]) -> int:
    """Write one row per session; returns the number of rows written."""
    rows = 0
    with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["course_id", "course_name", "session", "date", "start_time", "end_time"])
        for item in courses:
            for number, session in enumerate(item.sessions, start=1):
                writer.writerow(
                    [
                        item.course.course_id,
                        item.course.name,
                        number,
                        session.start.strftime("%d/%m/%Y"),
                        session.start.strftime("%H:%M"),
                        session.end.strftime("%H:%M"),
                    ]
                )
                rows += 1
    return rows
