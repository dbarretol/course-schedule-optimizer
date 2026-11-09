"""Parsers for the individual fields of the input file."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, time

DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d")
TIME_FORMAT = "%H:%M"

# English and Spanish names, full and abbreviated, without accents (see ``normalize``).
_DAY_NAMES: dict[int, tuple[str, ...]] = {
    0: ("monday", "mon", "lunes", "lun"),
    1: ("tuesday", "tue", "tues", "martes", "mar"),
    2: ("wednesday", "wed", "miercoles", "mie"),
    3: ("thursday", "thu", "thur", "thurs", "jueves", "jue"),
    4: ("friday", "fri", "viernes", "vie"),
    5: ("saturday", "sat", "sabado", "sab"),
    6: ("sunday", "sun", "domingo", "dom"),
}
DAY_LOOKUP: dict[str, int] = {
    name: index for index, names in _DAY_NAMES.items() for name in names
}
_DAY_CONNECTORS = frozenset({"and", "y", "e"})
_DAY_SEPARATORS = re.compile(r"[\s,;/&+.]+")


def normalize(text: str) -> str:
    """Lowercase, strip accents and collapse whitespace: ``' Miércoles '`` -> ``'miercoles'``."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(without_accents.lower().split())


def parse_days(text: str) -> frozenset[int]:
    """Parse ``'Monday, Wednesday and Friday'`` or ``'Lunes y Viernes'`` into weekday numbers.

    Raises:
        ValueError: if a token is not a known day name or no day is given.
    """
    days: set[int] = set()
    for token in _DAY_SEPARATORS.split(normalize(text)):
        if not token or token in _DAY_CONNECTORS:
            continue
        try:
            days.add(DAY_LOOKUP[token])
        except KeyError:
            raise ValueError(f"unknown day {token!r}") from None
    if not days:
        raise ValueError("no days given")
    return frozenset(days)


def parse_time(text: str) -> time:
    """Parse a 24-hour ``HH:MM`` time."""
    try:
        return datetime.strptime(text.strip(), TIME_FORMAT).time()
    except ValueError:
        raise ValueError(f"invalid time {text!r} (expected HH:MM)") from None


def parse_date(text: str) -> date:
    """Parse ``DD/MM/YYYY`` or ISO ``YYYY-MM-DD``."""
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"invalid date {text!r} (expected DD/MM/YYYY or YYYY-MM-DD)")


def parse_hours(text: str) -> float:
    """Parse a positive number of hours; accepts ``,`` as decimal separator."""
    try:
        value = float(text.strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"invalid number of hours {text!r}") from None
    if value <= 0:
        raise ValueError(f"total hours must be positive, got {text!r}")
    return value


def parse_priority(text: str) -> int:
    """Parse a priority: a positive integer, where 1 is the most important."""
    try:
        value = float(text.strip())
    except ValueError:
        raise ValueError(f"invalid priority {text!r}") from None
    if not value.is_integer() or value < 1:
        raise ValueError(f"priority must be a positive integer, got {text!r}")
    return int(value)
