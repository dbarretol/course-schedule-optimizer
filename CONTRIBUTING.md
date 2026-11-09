# Contributing

Thanks for your interest in improving course-schedule-optimizer. Bug reports, ideas and pull
requests are welcome.

## Reporting a bug

Open an issue with:

- the command you ran and its full output;
- a minimal input CSV that reproduces the problem (please replace real course names if they are
  private);
- what you expected to happen.

## Development setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/dbarretol/course-schedule-optimizer.git
cd course-schedule-optimizer
uv sync                     # package + dev tools
uv run pre-commit install   # ruff and mypy on every commit
```

## Checks

Every pull request must pass the same checks as CI:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy                 # strict, over src/
uv run pytest --cov         # coverage must stay at or above 90%
```

`uv run python scripts/benchmark.py` times the pipeline on synthetic inputs of 10–50 courses,
the realistic range for this tool.

## Branches and pull requests

- `main` holds released versions only; `dev` is the integration branch.
- Branch off `dev` with a descriptive prefix: `feat/`, `fix/`, `docs/`, `chore/`, `perf/`.
- Open the pull request against `dev`. Keep it focused on one change and describe how you tested it.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
  (`fix(solver): ...`, `docs: ...`).
- Add a line under **Unreleased** in [CHANGELOG.md](CHANGELOG.md) for user-visible changes.

## Code guidelines

- Everything in the repository is written in English: code, comments, messages and docs.
- Keep the pipeline stages separate: `loader` → `sessions` → `conflicts` → `solver` → `report` / `ical`.
- Add a test for every bug fix that fails without the fix.
- New input columns or CLI options need a README update.

## License

By contributing you agree that your contributions are licensed under the [MIT License](LICENSE).
