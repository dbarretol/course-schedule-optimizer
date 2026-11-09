"""CP-SAT model: assign courses to accounts with no clashes inside an account.

Variables: ``x[i, a] = 1`` if course ``i`` goes to account ``a``.
Constraints: each course in at most one account; clashing courses never share an account.
Objective: lexicographic by priority (priority 1 first, then 2, ...). See ``docs/model.md``.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Iterable, Sequence
from enum import StrEnum

from ortools.sat.python import cp_model

from course_scheduler.conflicts import find_conflicts
from course_scheduler.models import ScheduledCourse, SolveResult, SolveStatus

logger = logging.getLogger(__name__)

DEFAULT_ACCOUNTS = 2
DEFAULT_TIMEOUT_SECONDS = 60.0

# Largest objective value solved in one weighted pass; above it, solve level by level.
# Far below CP-SAT's int64 limit, and exact in double precision.
MAX_WEIGHTED_OBJECTIVE = 2**53


class Strategy(StrEnum):
    AUTO = "auto"  # weighted if the weights fit, staged otherwise
    WEIGHTED = "weighted"  # one solve with lexicographic weights
    STAGED = "staged"  # one solve per priority level


def priority_weights(priorities: Iterable[int]) -> dict[int, int]:
    """Smallest integer weights that make the objective exactly lexicographic.

    Walking from the least to the most important level, each weight is one more than
    the total value of every less important course: ``w_p = 1 + sum(w_q * N_q, q > p)``.
    So one course of priority ``p`` outweighs all lower-priority courses combined.
    Only levels that occur get a weight, so sparse priorities (1, 5, 15) cost nothing.
    """
    counts = Counter(priorities)
    weights: dict[int, int] = {}
    lower_total = 0
    for priority in sorted(counts, reverse=True):
        weights[priority] = lower_total + 1
        lower_total += weights[priority] * counts[priority]
    return weights


def max_objective(weights: dict[int, int], priorities: Iterable[int]) -> int:
    return sum(weights[p] for p in priorities)


def _to_status(status: int) -> SolveStatus | None:
    if status == cp_model.OPTIMAL:
        return SolveStatus.OPTIMAL
    if status == cp_model.FEASIBLE:
        return SolveStatus.FEASIBLE
    return None


_Outcome = tuple[cp_model.CpSolver, SolveStatus | None]
_Vars = dict[tuple[int, int], cp_model.IntVar]


def _run(model: cp_model.CpModel, timeout_seconds: float) -> _Outcome:
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    status = solver.solve(model)
    if _to_status(status) is None:
        logger.error("Solver found no solution (status %s)", solver.status_name(status))
    return solver, _to_status(status)


def _solve_weighted(
    model: cp_model.CpModel,
    taken: list[cp_model.LinearExpr],
    priorities: list[int],
    timeout_seconds: float,
) -> _Outcome:
    weights = priority_weights(priorities)
    model.maximize(sum(weights[p] * t for p, t in zip(priorities, taken)))
    return _run(model, timeout_seconds)


def _solve_staged(
    model: cp_model.CpModel,
    taken: list[cp_model.LinearExpr],
    priorities: list[int],
    x: _Vars,
    timeout_seconds: float,
) -> _Outcome:
    """Maximize priority-1 courses, lock that count in, then priority 2, and so on."""
    levels = sorted(set(priorities))
    stage_timeout = timeout_seconds / len(levels)
    overall = SolveStatus.OPTIMAL
    solver = cp_model.CpSolver()
    for level in levels:
        count = sum(t for p, t in zip(priorities, taken) if p == level)
        model.maximize(count)
        solver, status = _run(model, stage_timeout)
        if status is None:
            return solver, None
        if status is SolveStatus.FEASIBLE:
            overall = SolveStatus.FEASIBLE
        best = round(solver.objective_value)
        logger.debug("Priority %d: %d courses", level, best)
        model.add(count >= best)
        model.clear_hints()
        for var in x.values():
            model.add_hint(var, solver.value(var))
    return solver, overall


def solve(
    courses: Sequence[ScheduledCourse],
    num_accounts: int = DEFAULT_ACCOUNTS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    strategy: Strategy | str = Strategy.AUTO,
) -> SolveResult:
    """Choose which courses to take and in which account."""
    if num_accounts < 1:
        raise ValueError("num_accounts must be at least 1")
    strategy = Strategy(strategy)

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

    priorities = [item.course.priority for item in courses]
    taken = [sum(x[i, a] for a in accounts) for i in range(len(courses))]

    if strategy is Strategy.AUTO:
        too_big = max_objective(priority_weights(priorities), priorities) > MAX_WEIGHTED_OBJECTIVE
        strategy = Strategy.STAGED if too_big else Strategy.WEIGHTED
        if too_big:
            logger.info("Objective weights too large; solving one priority level at a time")

    if strategy is Strategy.WEIGHTED:
        solver, status = _solve_weighted(model, taken, priorities, timeout_seconds)
    else:
        solver, status = _solve_staged(model, taken, priorities, x, timeout_seconds)

    if status is None:
        return SolveResult(
            SolveStatus.NO_SOLUTION, ((),) * num_accounts, tuple(courses), conflicts
        )
    if status is SolveStatus.FEASIBLE:
        logger.warning("Time limit reached; the solution may not be optimal")

    assigned: list[list[ScheduledCourse]] = [[] for _ in accounts]
    unassigned: list[ScheduledCourse] = []
    for i, course in enumerate(courses):
        account = next((a for a in accounts if solver.value(x[i, a])), None)
        if account is None:
            unassigned.append(course)
        else:
            assigned[account].append(course)

    return SolveResult(
        status,
        tuple(tuple(account) for account in assigned),
        tuple(unassigned),
        conflicts,
    )
