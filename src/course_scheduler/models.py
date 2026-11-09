"""Domain types shared by every stage of the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import StrEnum
from typing import NamedTuple


@dataclass(frozen=True, slots=True)
class TimeSlot:
    """A weekly recurring block: the same start/end time on each of ``weekdays``.

    Weekdays follow :meth:`datetime.date.weekday` (0 = Monday ... 6 = Sunday).
    """

    weekdays: frozenset[int]
    start: time
    end: time


@dataclass(frozen=True, slots=True)
class Course:
    """A course as described by the input file (all rows sharing one ``course_id``)."""

    course_id: str
    name: str
    priority: int
    start_date: date
    total_hours: float
    slots: tuple[TimeSlot, ...]


class Session(NamedTuple):
    """One concrete class meeting."""

    start: datetime
    end: datetime

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600.0


@dataclass(frozen=True, slots=True)
class ScheduledCourse:
    """A course together with its expanded, chronologically sorted sessions."""

    course: Course
    sessions: tuple[Session, ...]


class SolveStatus(StrEnum):
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"  # time limit reached; the solution may not be optimal
    NO_SOLUTION = "no_solution"


@dataclass(frozen=True, slots=True)
class SolveResult:
    status: SolveStatus
    accounts: tuple[tuple[ScheduledCourse, ...], ...]
    unassigned: tuple[ScheduledCourse, ...]
    conflicts: tuple[tuple[ScheduledCourse, ScheduledCourse], ...]

    @property
    def assigned(self) -> tuple[tuple[int, ScheduledCourse], ...]:
        """``(account_index, course)`` pairs for every assigned course."""
        return tuple(
            (index, course)
            for index, courses in enumerate(self.accounts)
            for course in courses
        )
