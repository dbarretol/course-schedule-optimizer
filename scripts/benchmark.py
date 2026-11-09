"""Benchmark the pipeline on synthetic inputs.

Realistic inputs have 10-50 courses. Usage:

    uv run python scripts/benchmark.py [--sizes 10 20 30 50] [--accounts 2] [--seed 0]
"""

from __future__ import annotations

import argparse
import random
import time
from datetime import date, timedelta
from datetime import time as clock

from course_scheduler.conflicts import find_conflicts
from course_scheduler.models import Course, TimeSlot
from course_scheduler.sessions import schedule_courses
from course_scheduler.solver import solve


def synthetic_courses(count: int, seed: int) -> list[Course]:
    """Courses spread over ~2 months, 1-3 weekly blocks of 2-4 hours, priorities 1-4."""
    rng = random.Random(seed)
    courses = []
    for n in range(count):
        slots = []
        for _ in range(rng.randint(1, 3)):
            start = rng.randint(8, 19)
            slots.append(
                TimeSlot(
                    frozenset(rng.sample(range(7), rng.randint(1, 2))),
                    clock(start),
                    clock(min(start + rng.randint(2, 4), 23)),
                )
            )
        courses.append(
            Course(
                course_id=str(n),
                name=f"Course {n}",
                priority=rng.randint(1, 4),
                start_date=date(2026, 3, 2) + timedelta(days=rng.randint(0, 60)),
                total_hours=rng.choice([8, 12, 16, 24]),
                slots=tuple(slots),
            )
        )
    return courses


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", type=int, nargs="+", default=[10, 20, 30, 50])
    parser.add_argument("--accounts", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    print(
        f"{'courses':>8} {'sessions':>9} {'clashes':>8} {'sessions s':>11} "
        f"{'graph s':>8} {'solve s':>8} {'assigned':>9} status"
    )
    for size in args.sizes:
        courses = synthetic_courses(size, args.seed)
        t0 = time.perf_counter()
        scheduled = schedule_courses(courses)
        t1 = time.perf_counter()
        pairs = find_conflicts(scheduled)
        t2 = time.perf_counter()
        result = solve(scheduled, args.accounts, args.timeout)
        t3 = time.perf_counter()
        sessions = sum(len(item.sessions) for item in scheduled)
        print(
            f"{size:>8} {sessions:>9} {len(pairs):>8} {t1 - t0:>11.3f} "
            f"{t2 - t1:>8.3f} {t3 - t2:>8.3f} {len(result.assigned):>9} {result.status}"
        )


if __name__ == "__main__":
    main()
