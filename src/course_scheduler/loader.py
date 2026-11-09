"""Load and validate the course CSV.

Canonical header (``;``-separated)::

    course_id;name;start_date;days;start_time;end_time;total_hours;priority

A course with several weekly blocks spans several rows with the same ``course_id``.
Spanish headers (``ID Curso;Curso;Inicio;Días;Hora inicio;Hora fin;Horas;Prioridad``)
are accepted as aliases.
"""

from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from course_scheduler.models import Course, TimeSlot
from course_scheduler.parsing import (
    normalize,
    parse_date,
    parse_days,
    parse_hours,
    parse_priority,
    parse_time,
)

logger = logging.getLogger(__name__)

COLUMNS = (
    "course_id",
    "name",
    "start_date",
    "days",
    "start_time",
    "end_time",
    "total_hours",
    "priority",
)

_ALIASES = {
    "id_curso": "course_id",
    "curso": "name",
    "inicio": "start_date",
    "dias": "days",
    "hora_inicio": "start_time",
    "hora_fin": "end_time",
    "horas": "total_hours",
    "prioridad": "priority",
}
COLUMN_ALIASES: dict[str, str] = {name: name for name in COLUMNS} | _ALIASES

ENCODINGS = ("utf-8-sig", "cp1252")


class InputError(Exception):
    """The input file cannot be used. ``errors`` lists every problem found."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def _header_key(text: str) -> str:
    return re.sub(r"[\s\-]+", "_", normalize(text))


def _decode(raw: bytes, source: str) -> str:
    for encoding in ENCODINGS:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise InputError([f"{source}: cannot decode file as UTF-8 or Windows-1252"])


@dataclass
class _CourseDraft:
    course_id: str
    name: str
    priority: int
    total_hours: float
    first_line: int
    start_dates: list[date] = field(default_factory=list)
    slots: list[TimeSlot] = field(default_factory=list)


def load_courses(path: str | Path, delimiter: str = ";") -> list[Course]:
    """Read ``path`` and return its courses in order of first appearance.

    Raises:
        InputError: with every problem found (missing columns, invalid values,
            rows of one course that disagree on name or priority).
    """
    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise InputError([f"{path}: {exc.strerror or exc}"]) from exc
    return parse_courses(_decode(raw, str(path)), delimiter=delimiter, source=str(path))


def parse_courses(text: str, delimiter: str = ";", source: str = "<input>") -> list[Course]:
    """Parse CSV ``text``; see :func:`load_courses`."""
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = next(reader, None)
    if header is None:
        raise InputError([f"{source}: file is empty"])

    positions: dict[str, int] = {}
    for index, title in enumerate(header):
        column = COLUMN_ALIASES.get(_header_key(title))
        if column is not None and column not in positions:
            positions[column] = index
    missing = [column for column in COLUMNS if column not in positions]
    if missing:
        raise InputError(
            [
                f"{source}: missing columns {', '.join(missing)}; "
                f"found {header!r}. Expected: {delimiter.join(COLUMNS)}"
            ]
        )

    errors: list[str] = []
    drafts: dict[str, _CourseDraft] = {}

    for line_number, row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in row):
            continue
        where = f"{source}:{line_number}"
        values = {
            column: row[index].strip() if index < len(row) else ""
            for column, index in positions.items()
        }
        row_errors: list[str] = []

        def field_value(column: str, parser, values=values, row_errors=row_errors):
            try:
                return parser(values[column])
            except ValueError as exc:
                row_errors.append(f"{where}: {column}: {exc}")
                return None

        course_id = values["course_id"]
        name = values["name"]
        if not course_id:
            row_errors.append(f"{where}: course_id: empty")
        if not name:
            row_errors.append(f"{where}: name: empty")
        start_date = field_value("start_date", parse_date)
        days = field_value("days", parse_days)
        start_time = field_value("start_time", parse_time)
        end_time = field_value("end_time", parse_time)
        total_hours = field_value("total_hours", parse_hours)
        priority = field_value("priority", parse_priority)
        if start_time is not None and end_time is not None and end_time <= start_time:
            row_errors.append(
                f"{where}: end_time {values['end_time']} is not after "
                f"start_time {values['start_time']}"
            )

        if row_errors:
            errors.extend(row_errors)
            continue

        draft = drafts.get(course_id)
        if draft is None:
            draft = drafts[course_id] = _CourseDraft(
                course_id, name, priority, total_hours, line_number
            )
        else:
            if name != draft.name or priority != draft.priority:
                errors.append(
                    f"{where}: course {course_id} has name/priority "
                    f"{name!r}/{priority}, but line {draft.first_line} says "
                    f"{draft.name!r}/{draft.priority}"
                )
                continue
            if total_hours != draft.total_hours:
                logger.warning(
                    "%s: course %s has total_hours %s, but line %d says %s; using %s",
                    where, course_id, total_hours, draft.first_line,
                    draft.total_hours, draft.total_hours,
                )
        draft.start_dates.append(start_date)
        draft.slots.append(TimeSlot(days, start_time, end_time))

    if errors:
        raise InputError(errors)
    if not drafts:
        raise InputError([f"{source}: no courses found"])

    return [
        Course(
            course_id=draft.course_id,
            name=draft.name,
            priority=draft.priority,
            start_date=min(draft.start_dates),
            total_hours=draft.total_hours,
            slots=tuple(draft.slots),
        )
        for draft in drafts.values()
    ]
