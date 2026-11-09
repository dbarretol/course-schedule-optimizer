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
from collections.abc import Callable
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


@dataclass(frozen=True, slots=True)
class _Row:
    course_id: str
    name: str
    start_date: date
    slot: TimeSlot
    total_hours: float
    priority: int


def _parse_field[T](
    values: dict[str, str], column: str, parser: Callable[[str], T], where: str, errors: list[str]
) -> T | None:
    try:
        return parser(values[column])
    except ValueError as exc:
        errors.append(f"{where}: {column}: {exc}")
        return None


def _parse_row(values: dict[str, str], where: str) -> tuple[_Row | None, list[str]]:
    """Parse one data row; returns the row, or ``None`` and the list of its problems."""
    errors: list[str] = []
    course_id, name = values["course_id"], values["name"]
    if not course_id:
        errors.append(f"{where}: course_id: empty")
    if not name:
        errors.append(f"{where}: name: empty")
    start_date = _parse_field(values, "start_date", parse_date, where, errors)
    days = _parse_field(values, "days", parse_days, where, errors)
    start_time = _parse_field(values, "start_time", parse_time, where, errors)
    end_time = _parse_field(values, "end_time", parse_time, where, errors)
    total_hours = _parse_field(values, "total_hours", parse_hours, where, errors)
    priority = _parse_field(values, "priority", parse_priority, where, errors)
    if start_time is not None and end_time is not None and end_time <= start_time:
        errors.append(
            f"{where}: end_time {values['end_time']} is not after start_time {values['start_time']}"
        )
    if (
        errors
        or start_date is None
        or days is None
        or start_time is None
        or end_time is None
        or total_hours is None
        or priority is None
    ):
        return None, errors
    slot = TimeSlot(days, start_time, end_time)
    return _Row(course_id, name, start_date, slot, total_hours, priority), []


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

    for line_number, cells in enumerate(reader, start=2):
        if not any(cell.strip() for cell in cells):
            continue
        where = f"{source}:{line_number}"
        values = {
            column: cells[index].strip() if index < len(cells) else ""
            for column, index in positions.items()
        }
        row, row_errors = _parse_row(values, where)
        if row is None:
            errors.extend(row_errors)
            continue

        draft = drafts.get(row.course_id)
        if draft is None:
            draft = drafts[row.course_id] = _CourseDraft(
                row.course_id, row.name, row.priority, row.total_hours, line_number
            )
        else:
            if row.name != draft.name or row.priority != draft.priority:
                errors.append(
                    f"{where}: course {row.course_id} has name/priority "
                    f"{row.name!r}/{row.priority}, but line {draft.first_line} says "
                    f"{draft.name!r}/{draft.priority}"
                )
                continue
            if row.total_hours != draft.total_hours:
                logger.warning(
                    "%s: course %s has total_hours %s, but line %d says %s; using %s",
                    where,
                    row.course_id,
                    row.total_hours,
                    draft.first_line,
                    draft.total_hours,
                    draft.total_hours,
                )
        draft.start_dates.append(row.start_date)
        draft.slots.append(row.slot)

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
