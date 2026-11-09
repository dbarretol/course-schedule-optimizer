"""Command-line interface: ``course-scheduler solve`` and ``course-scheduler export-ics``."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from course_scheduler import __version__
from course_scheduler.ical import write_calendar, write_sessions_csv
from course_scheduler.loader import InputError, load_courses
from course_scheduler.models import ScheduledCourse, SolveStatus
from course_scheduler.report import format_report
from course_scheduler.sessions import schedule_courses
from course_scheduler.solver import DEFAULT_ACCOUNTS, DEFAULT_TIMEOUT_SECONDS, solve

EXIT_OK = 0
EXIT_NO_SOLUTION = 1
EXIT_INPUT_ERROR = 2

logger = logging.getLogger("course_scheduler")


def _positive_int(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def _positive_float(text: str) -> float:
    value = float(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="course-scheduler",
        description="Split courses across accounts without schedule clashes, by priority.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("input", type=Path, help="course CSV file")
    common.add_argument("--delimiter", default=";", help="CSV delimiter (default: ';')")
    common.add_argument("-v", "--verbose", action="store_true", help="more detail")
    common.add_argument("--log-file", type=Path, help="also write logs to this file")

    solver_options = argparse.ArgumentParser(add_help=False)
    solver_options.add_argument(
        "--accounts", type=_positive_int, default=DEFAULT_ACCOUNTS,
        help=f"number of accounts (default: {DEFAULT_ACCOUNTS})",
    )
    solver_options.add_argument(
        "--timeout", type=_positive_float, default=DEFAULT_TIMEOUT_SECONDS,
        help=f"solver time limit in seconds (default: {DEFAULT_TIMEOUT_SECONDS:g})",
    )

    commands = parser.add_subparsers(dest="command", required=True)

    solve_cmd = commands.add_parser(
        "solve", parents=[common, solver_options],
        help="choose courses and assign them to accounts",
    )
    solve_cmd.add_argument("-o", "--output", type=Path, help="also write the report here")

    export_cmd = commands.add_parser(
        "export-ics", parents=[common, solver_options],
        help="export course sessions to an iCalendar file",
    )
    export_cmd.add_argument(
        "-o", "--output", type=Path, default=Path("calendar.ics"),
        help="calendar file (default: calendar.ics)",
    )
    export_cmd.add_argument("--sessions-csv", type=Path, help="also write sessions as CSV")
    export_cmd.add_argument(
        "--assigned-only", action="store_true",
        help="solve first and export only assigned courses, tagged with their account",
    )
    return parser


def _configure_logging(verbose: bool, log_file: Path | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(message)s",
        handlers=handlers,
        force=True,
    )
    logging.getLogger("ortools").setLevel(logging.WARNING)


def _run_solve(args: argparse.Namespace, courses: list[ScheduledCourse]) -> int:
    result = solve(courses, args.accounts, args.timeout)
    report = format_report(result, verbose=args.verbose)
    print(report)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
        logger.info("Report written to %s", args.output)
    return EXIT_NO_SOLUTION if result.status is SolveStatus.NO_SOLUTION else EXIT_OK


def _run_export(args: argparse.Namespace, courses: list[ScheduledCourse]) -> int:
    account_of: dict[str, int] | None = None
    if args.assigned_only:
        result = solve(courses, args.accounts, args.timeout)
        if result.status is SolveStatus.NO_SOLUTION:
            return EXIT_NO_SOLUTION
        account_of = {item.course.course_id: a + 1 for a, item in result.assigned}
        courses = [item for _, item in result.assigned]

    write_calendar(args.output, courses, account_of)
    events = sum(len(item.sessions) for item in courses)
    logger.info("Calendar with %d sessions written to %s", events, args.output)
    if args.sessions_csv:
        rows = write_sessions_csv(args.sessions_csv, courses)
        logger.info("%d sessions written to %s", rows, args.sessions_csv)
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        # Pipes and redirects on Windows default to the ANSI code page; emit UTF-8.
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    _configure_logging(args.verbose, args.log_file)

    try:
        courses = load_courses(args.input, delimiter=args.delimiter)
    except InputError as exc:
        for error in exc.errors:
            logger.error(error)
        return EXIT_INPUT_ERROR
    logger.info("Loaded %d courses from %s", len(courses), args.input)
    scheduled = schedule_courses(courses)

    if args.command == "solve":
        return _run_solve(args, scheduled)
    return _run_export(args, scheduled)
