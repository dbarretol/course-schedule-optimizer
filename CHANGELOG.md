# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-08

First public release.

### Added

- `course-scheduler solve`: assigns courses to one or more accounts (`--accounts`, default 2)
  so that no account has two clashing courses, maximizing courses by priority
  lexicographically (all possible priority-1 courses first, then priority 2, and so on).
- `course-scheduler export-ics`: exports course sessions to an RFC 5545 iCalendar file;
  `--assigned-only` exports only the courses picked by the optimizer, tagged by account;
  `--sessions-csv` also writes one CSV row per session.
- Input CSV with an English header (`course_id;name;start_date;days;start_time;end_time;total_hours;priority`);
  Spanish headers and day names are accepted as aliases. UTF-8 and Windows-1252 files are supported.
- Session expansion from start date, weekly blocks and total hours, shortening the last session
  so the total is exact.
- Input validation that reports every problem with its line number.
- Exit codes: `0` success, `1` no solution within the time limit, `2` invalid input.
- Reproducible results: the same input always yields the same assignment.
- Documentation of the optimization model in [docs/model.md](docs/model.md).

[Unreleased]: https://github.com/dbarretol/course-schedule-optimizer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/dbarretol/course-schedule-optimizer/releases/tag/v0.1.0
