from datetime import date, time

import pytest

from course_scheduler.parsing import (
    normalize,
    parse_date,
    parse_days,
    parse_hours,
    parse_priority,
    parse_time,
)


def test_normalize_strips_accents_case_and_spaces():
    assert normalize("  Miércoles   SÁBADO ") == "miercoles sabado"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Monday", {0}),
        ("Monday, Wednesday and Friday", {0, 2, 4}),
        ("tue/THU", {1, 3}),
        ("Lunes y Miércoles", {0, 2}),
        ("mar, JUE, vie", {1, 3, 4}),
        ("Sábado", {5}),
        ("sabado y domingo", {5, 6}),
        ("Martes, Jueves y Sábado", {1, 3, 5}),
    ],
)
def test_parse_days(text, expected):
    assert parse_days(text) == frozenset(expected)


@pytest.mark.parametrize("text", ["", "  ", "Funday", "Monday and someday"])
def test_parse_days_rejects_unknown_or_empty(text):
    with pytest.raises(ValueError):
        parse_days(text)


def test_parse_time():
    assert parse_time("09:00") == time(9, 0)
    assert parse_time(" 23:59 ") == time(23, 59)
    assert parse_time("9:30") == time(9, 30)
    with pytest.raises(ValueError):
        parse_time("25:00")


@pytest.mark.parametrize(
    "text", ["10/02/2026", "2026-02-10", "10/2/2026", " 10/02/2026 "]
)
def test_parse_date(text):
    assert parse_date(text) == date(2026, 2, 10)


def test_parse_date_rejects_invalid():
    with pytest.raises(ValueError):
        parse_date("02-10-2026")


def test_parse_hours():
    assert parse_hours("16") == 16
    assert parse_hours("7,5") == 7.5
    for bad in ("0", "-1", "abc"):
        with pytest.raises(ValueError):
            parse_hours(bad)


def test_parse_priority():
    assert parse_priority("2") == 2
    assert parse_priority("3.0") == 3
    for bad in ("0", "1.5", "high"):
        with pytest.raises(ValueError):
            parse_priority(bad)
