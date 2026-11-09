from datetime import date, time

import pytest

from course_scheduler.loader import InputError, load_courses, parse_courses

HEADER = "course_id;name;start_date;days;start_time;end_time;total_hours;priority\n"


def test_loads_sample_file(sample_csv):
    courses = load_courses(sample_csv)
    assert [c.course_id for c in courses] == [str(i) for i in range(1, 9)]
    project_management = courses[5]
    assert len(project_management.slots) == 2  # two rows, one course


def test_groups_rows_and_uses_earliest_start_date():
    text = HEADER + (
        "7;Git;12/05/2026;Monday;16:00;19:00;18;1\n"
        "7;Git;10/05/2026;Tuesday, Thursday;16:00;19:00;18;1\n"
    )
    (course,) = parse_courses(text)
    assert course.start_date == date(2026, 5, 10)
    assert course.slots[1].weekdays == frozenset({1, 3})
    assert course.slots[0].start == time(16, 0)


def test_accepts_spanish_headers():
    text = (
        "ID Curso;Curso;Inicio;Días;Hora inicio;Hora fin;Horas;Prioridad\n"
        "3;CCNA;16/05/2026;Sábado;13:00;17:00;24;2\n"
    )
    (course,) = parse_courses(text)
    assert (course.course_id, course.name, course.priority) == ("3", "CCNA", 2)
    assert course.slots[0].weekdays == frozenset({5})


def test_reads_windows_1252_files(tmp_path):
    path = tmp_path / "courses.csv"
    text = HEADER + "1;Computación;10/02/2026;Miércoles;09:00;12:00;6;1\n"
    path.write_bytes(text.encode("cp1252"))
    (course,) = load_courses(path)
    assert course.name == "Computación"


def test_skips_blank_lines():
    text = HEADER + "\n1;A;10/02/2026;Monday;09:00;12:00;6;1\n;;;;;;;\n"
    assert len(parse_courses(text)) == 1


def test_missing_columns():
    with pytest.raises(InputError, match="missing columns .*priority"):
        parse_courses("course_id;name;start_date;days;start_time;end_time;total_hours\n")


def test_empty_file():
    with pytest.raises(InputError, match="empty"):
        parse_courses("")


def test_header_only():
    with pytest.raises(InputError, match="no courses"):
        parse_courses(HEADER)


def test_reports_every_invalid_value_with_line_numbers():
    text = HEADER + (
        "1;A;31/02/2026;Monday;09:00;12:00;6;1\n"
        "2;B;10/02/2026;Someday;12:00;09:00;x;0\n"
    )
    with pytest.raises(InputError) as info:
        parse_courses(text, source="in.csv")
    errors = info.value.errors
    assert any(e.startswith("in.csv:2: start_date") for e in errors)
    assert any(e.startswith("in.csv:3: days") for e in errors)
    assert any(e.startswith("in.csv:3: total_hours") for e in errors)
    assert any(e.startswith("in.csv:3: priority") for e in errors)
    assert any(e.startswith("in.csv:3: end_time") for e in errors)


def test_rejects_rows_of_one_course_with_different_priority():
    text = HEADER + (
        "1;A;10/02/2026;Monday;09:00;12:00;6;1\n"
        "1;A;10/02/2026;Tuesday;09:00;12:00;6;2\n"
    )
    with pytest.raises(InputError, match="course 1 has name/priority"):
        parse_courses(text)


def test_inconsistent_hours_warns_and_keeps_first(caplog):
    text = HEADER + (
        "1;A;10/02/2026;Monday;09:00;12:00;6;1\n"
        "1;A;10/02/2026;Tuesday;09:00;12:00;9;1\n"
    )
    (course,) = parse_courses(text)
    assert course.total_hours == 6
    assert "total_hours" in caplog.text


def test_missing_file(tmp_path):
    with pytest.raises(InputError):
        load_courses(tmp_path / "nope.csv")
