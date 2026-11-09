from course_scheduler.cli import EXIT_INPUT_ERROR, EXIT_OK, main


def test_solve_sample(sample_csv, tmp_path, capsys):
    report_path = tmp_path / "report.txt"
    assert main(["solve", str(sample_csv), "--output", str(report_path)]) == EXIT_OK
    out = capsys.readouterr().out
    assert "ACCOUNT 1" in out and "ACCOUNT 2" in out
    assert "UNASSIGNED COURSES (1):" in out
    assert "[8] Public Speaking" in out
    assert report_path.read_text(encoding="utf-8").strip() == out.strip()


def test_solve_with_three_accounts_assigns_everything(sample_csv, capsys):
    assert main(["solve", str(sample_csv), "--accounts", "3"]) == EXIT_OK
    assert "All courses were assigned." in capsys.readouterr().out


def test_invalid_input_exits_with_input_error(tmp_path, capsys):
    path = tmp_path / "bad.csv"
    path.write_text("name;priority\nA;1\n", encoding="utf-8")
    assert main(["solve", str(path)]) == EXIT_INPUT_ERROR
    assert "missing columns" in capsys.readouterr().err


def test_export_ics_assigned_only(sample_csv, tmp_path):
    ics = tmp_path / "out.ics"
    sessions = tmp_path / "sessions.csv"
    code = main(
        ["export-ics", str(sample_csv), "-o", str(ics), "--sessions-csv", str(sessions), "--assigned-only"]
    )
    assert code == EXIT_OK
    text = ics.read_text(encoding="utf-8")
    assert "Public Speaking" not in text
    assert "CATEGORIES:Account" in text
    assert sessions.exists()


def test_export_ics_all_courses(sample_csv, tmp_path):
    ics = tmp_path / "out.ics"
    assert main(["export-ics", str(sample_csv), "-o", str(ics)]) == EXIT_OK
    assert "Public Speaking" in ics.read_text(encoding="utf-8")
