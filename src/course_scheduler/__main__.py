"""Allow running the CLI with ``python -m course_scheduler``."""

import sys

from course_scheduler.cli import main

sys.exit(main())
