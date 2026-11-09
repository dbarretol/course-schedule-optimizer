# course-schedule-optimizer

[![CI](https://github.com/dbarretol/course-schedule-optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/dbarretol/course-schedule-optimizer/actions/workflows/ci.yml)

Pick the best set of courses when you can enroll through several accounts.

Some course platforms refuse to enroll one account in two courses whose schedules clash, but
nothing stops you from using a second account. Given a list of courses with their weekly
schedules and your priorities, this tool:

1. expands every course into its real sessions (start date, weekdays, hours per block, total hours);
2. finds every pair of courses that clash;
3. uses [OR-Tools CP-SAT](https://developers.google.com/optimization/cp/cp_solver) to assign
   courses to accounts with **no clash inside an account**, taking as many priority-1 courses
   as possible, then as many priority-2 courses as possible, and so on (the same input always
   gives the same result);
4. optionally exports the sessions to an iCalendar (`.ics`) file for Google Calendar, Outlook, etc.

## Installation

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/dbarretol/course-schedule-optimizer.git
cd course-schedule-optimizer
uv sync
```

## Usage

```bash
# Assign courses to 2 accounts (default) and print the report
uv run course-scheduler solve examples/courses.sample.csv

# 3 accounts, 30 s time limit, save the report, list sessions per course
uv run course-scheduler solve my-courses.csv --accounts 3 --timeout 30 -o result.txt -v

# Calendar with every course in the file
uv run course-scheduler export-ics my-courses.csv -o calendar.ics

# Calendar with only the courses the optimizer picked, tagged by account, plus a CSV of sessions
uv run course-scheduler export-ics my-courses.csv --assigned-only -o calendar.ics --sessions-csv sessions.csv
```

Run `uv run course-scheduler --help` or `uv run course-scheduler <command> --help` for all options.
Exit codes: `0` success, `1` the solver found no solution within the time limit, `2` invalid input.

### Example output

```text
ACCOUNT 1 (4 courses):
  [1] Intro to Python (priority 1)
  [2] SQL Fundamentals (priority 1)
  [4] Linux Basics (priority 2)
  [6] Project Management (priority 3)

ACCOUNT 2 (3 courses):
  [3] Data Visualization (priority 2)
  [5] Cloud Essentials (priority 3)
  [7] Git Workshop (priority 4)

UNASSIGNED COURSES (1):
  [8] Public Speaking (priority 4)
```

## Input format

A `;`-separated CSV, UTF-8 or Windows-1252. See [`examples/courses.sample.csv`](examples/courses.sample.csv).

```text
course_id;name;start_date;days;start_time;end_time;total_hours;priority
1;Intro to Python;02/03/2026;Monday, Wednesday;18:00;21:00;24;1
6;Project Management;05/03/2026;Thursday;18:00;20:00;10;3
6;Project Management;05/03/2026;Friday;18:00;21:00;10;3
```

| Column | Meaning |
|---|---|
| `course_id` | Identifier. Rows with the same id are one course with several weekly blocks. |
| `name` | Course name. |
| `start_date` | Date of the first class: `DD/MM/YYYY` or `YYYY-MM-DD`. |
| `days` | Weekdays of this block, e.g. `Monday, Wednesday and Friday` or `Mon/Wed`. |
| `start_time`, `end_time` | Block time, 24-hour `HH:MM`. |
| `total_hours` | Total course length in hours (not the number of sessions). The last session is shortened if needed. |
| `priority` | Positive integer; `1` is the most important. |

Sessions are generated from `start_date` onwards until `total_hours` is reached. A session that ends
exactly when another starts is not a clash. All rows of one course must share `name` and
`priority`; invalid rows are reported with their line number.

> Spanish headers (`ID Curso;Curso;Inicio;Días;Hora inicio;Hora fin;Horas;Prioridad`) and Spanish
> day names (`Lunes y Miércoles`) are also accepted.

## How it works

See [docs/model.md](docs/model.md) for the optimization model.

## Development

```bash
uv sync                        # install the package and dev tools
uv run pre-commit install      # run ruff and mypy on every commit
uv run pytest --cov            # tests with coverage (minimum 90%)
uv run ruff check . && uv run ruff format --check .
uv run mypy                    # strict type checking of src/
```

CI runs lint, type checking and the test suite on Linux and Windows with Python 3.12 and 3.13.

## License

[MIT](LICENSE)
