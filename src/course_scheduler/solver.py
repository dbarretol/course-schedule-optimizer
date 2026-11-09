"""CP-SAT model: assign courses to accounts with no clashes inside an account.

Variables: ``x[i, a] = 1`` if course ``i`` goes to account ``a``.
Constraints: each course in at most one account; clashing courses never share an account.
Objective: lexicographic by priority (priority 1 first, then 2, ...). See ``docs/model.md``.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from ortools.sat.python import cp_model

from course_scheduler.conflicts import find_conflicts
from course_scheduler.models import ScheduledCourse, SolveResult, SolveStatus

logger = logging.getLogger(__name__)

DEFAULT_ACCOUNTS = 2
DEFAULT_TIMEOUT_SECONDS = 60.0

_LEXICOGRAPHIC_BASE = 100
_MAX_BASE_100_LEVELS = 9


def priority_weights(priorities: Sequence[int], num_courses: int) -> dict[int, int]:
    """Objective weight per priority level (higher for more important levels)."""
    if not priorities:
        return {}
    lowest = max(priorities)
    if lowest > _MAX_BASE_100_LEVELS:
        logger.warning(
            "%d priority levels detected; using base %d to limit weight size",
            lowest, num_courses + 1,
        )
        base = max(2, num_courses + 1)
    else:
        base = _LEXICOGRAPHIC_BASE
    return {priority: base ** (lowest - priority) for priority in set(priorities)}


def solve(
    courses: Sequence[ScheduledCourse],
    num_accounts: int = DEFAULT_ACCOUNTS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> SolveResult:
    """Choose which courses to take and in which account."""
    if num_accounts < 1:
        raise ValueError("num_accounts must be at least 1")

    conflict_pairs = find_conflicts(courses)
    conflicts = tuple((courses[i], courses[j]) for i, j in conflict_pairs)
    logger.info("%d courses, %d clashing pairs", len(courses), len(conflict_pairs))

    if not courses:
        return SolveResult(SolveStatus.OPTIMAL, ((),) * num_accounts, (), conflicts)

    model = cp_model.CpModel()
    accounts = range(num_accounts)
    x = {
        (i, a): model.new_bool_var(f"x_{i}_{a}")
        for i in range(len(courses))
        for a in accounts
    }
    for i in range(len(courses)):
        model.add_at_most_one([x[i, a] for a in accounts])
    for i, j in conflict_pairs:
        for a in accounts:
            model.add_at_most_one([x[i, a], x[j, a]])

    weights = priority_weights([c.course.priority for c in courses], len(courses))
    model.maximize(
        sum(
            weights[course.course.priority] * x[i, a]
            for i, course in enumerate(courses)
            for a in accounts
        )
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    status = solver.solve(model)

    if status == cp_model.OPTIMAL:
        result_status = SolveStatus.OPTIMAL
    elif status == cp_model.FEASIBLE:
        result_status = SolveStatus.FEASIBLE
        logger.warning("Time limit reached; the solution may not be optimal")
    else:
        logger.error("Solver found no solution (status %s)", solver.status_name(status))
        return SolveResult(
            SolveStatus.NO_SOLUTION, ((),) * num_accounts, tuple(courses), conflicts
        )

    assigned: list[list[ScheduledCourse]] = [[] for _ in accounts]
    unassigned: list[ScheduledCourse] = []
    for i, course in enumerate(courses):
        account = next((a for a in accounts if solver.value(x[i, a])), None)
        if account is None:
            unassigned.append(course)
        else:
            assigned[account].append(course)

    return SolveResult(
        result_status,
        tuple(tuple(account) for account in assigned),
        tuple(unassigned),
        conflicts,
    )
