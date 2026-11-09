"""Course schedule optimizer: split courses across accounts without schedule clashes."""

from course_scheduler.conflicts import find_conflicts, sessions_overlap
from course_scheduler.loader import InputError, load_courses
from course_scheduler.models import (
    Course,
    ScheduledCourse,
    Session,
    SolveResult,
    SolveStatus,
    TimeSlot,
)
from course_scheduler.sessions import generate_sessions, schedule_courses
from course_scheduler.solver import solve

__version__ = "0.1.0"

__all__ = [
    "Course",
    "InputError",
    "ScheduledCourse",
    "Session",
    "SolveResult",
    "SolveStatus",
    "TimeSlot",
    "find_conflicts",
    "generate_sessions",
    "load_courses",
    "schedule_courses",
    "sessions_overlap",
    "solve",
]
