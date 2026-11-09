import csv
from datetime import UTC, datetime

from conftest import make_course, scheduled

from course_scheduler.ical import build_calendar, write_sessions_csv

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def events(text):
    return text.count("BEGIN:VEVENT")


def test_one_event_per_session_with_required_properties():
    course = scheduled(make_course("1", name="Intro", hours=6))
    text = build_calendar([course], now=NOW)
    assert events(text) == 2
    assert "UID:1-1-20260209T090000@course-schedule-optimizer\r\n" in text
    assert "DTSTAMP:20260101T120000Z\r\n" in text
    assert "DTSTART:20260209T090000\r\n" in text
    assert "DTEND:20260209T120000\r\n" in text
    assert "DESCRIPTION:Session 2 of 2\r\n" in text
    assert text.startswith("BEGIN:VCALENDAR\r\n")
    assert text.endswith("END:VCALENDAR\r\n")


def test_lines_use_crlf_only():
    text = build_calendar([scheduled(make_course())], now=NOW)
    assert "\n" not in text.replace("\r\n", "")


def test_text_is_escaped():
    course = scheduled(make_course(name="Data; Viz, Pro\\"))
    assert "SUMMARY:Data\\; Viz\\, Pro\\\\\r\n" in build_calendar([course], now=NOW)


def test_long_lines_are_folded_to_75_octets():
    course = scheduled(make_course(name="Programación " * 12))
    text = build_calendar([course], now=NOW)
    lines = text.split("\r\n")
    assert all(len(line.encode("utf-8")) <= 75 for line in lines)
    unfolded = text.replace("\r\n ", "")
    assert "SUMMARY:" + "Programación " * 12 in unfolded


def test_account_category():
    course = scheduled(make_course("7"))
    text = build_calendar([course], account_of={"7": 2}, now=NOW)
    assert "CATEGORIES:Account 2\r\n" in text


def test_sessions_csv(tmp_path):
    path = tmp_path / "sessions.csv"
    rows = write_sessions_csv(path, [scheduled(make_course("1", name="Intro", hours=6))])
    assert rows == 2
    with path.open(encoding="utf-8-sig", newline="") as handle:
        data = list(csv.DictReader(handle))
    assert data[1] == {
        "course_id": "1",
        "course_name": "Intro",
        "session": "2",
        "date": "16/02/2026",
        "start_time": "09:00",
        "end_time": "12:00",
    }
