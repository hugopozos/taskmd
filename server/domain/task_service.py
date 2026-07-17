"""
Task domain service — pure business logic, no I/O.

This service contains all the rules for managing tasks,
columns, aging, and validation. It is fully testable without
any filesystem, network, or git dependencies.
"""

import hashlib
import re
import secrets
from datetime import date, datetime
from typing import Optional

from server.domain.models import Task, TaskBoard

# Matches `#abc` or `#abcd` or `#abcde` or `#abcdef` at END of line only
ID_PATTERN = re.compile(r'`#([0-9a-f]{3,6})`\s*$')

DEFAULT_COLUMNS = ["Backlog", "Week", "Today", "Done"]


# ── ID generation ────────────────────────────────────────────


def generate_id(title: str, timestamp: str, existing: set[str]) -> str:
    """Deterministic short hash, extends on collision."""
    base = hashlib.sha256(f"{title}|{timestamp}".encode()).hexdigest()
    for length in range(3, 7):
        candidate = base[:length]
        if candidate not in existing:
            return candidate
    # Practically unreachable with sane task counts
    while True:
        candidate = secrets.token_hex(3)
        if candidate not in existing:
            return candidate


def collect_ids(board: TaskBoard) -> set[str]:
    """Collect all task IDs from the board."""
    ids: set[str] = set()
    for tasks in board.columns.values():
        for t in tasks:
            if t.id:
                ids.add(t.id)
    return ids


def assign_missing_ids(board: TaskBoard) -> bool:
    """Assign IDs to tasks that lack one. Returns True if anything changed."""
    existing = collect_ids(board)
    changed = False
    for tasks in board.columns.values():
        for t in tasks:
            if not t.id:
                t.id = generate_id(t.title, datetime.now().isoformat(), existing)
                existing.add(t.id)
                changed = True
    return changed


# ── Aging ────────────────────────────────────────────────────


def recalculate_aging(board: TaskBoard) -> None:
    """Update aging_days for tasks in the Today column."""
    today = date.today()
    for name, tasks in board.columns.items():
        if name != "Today":
            continue
        for t in tasks:
            if t.is_completed:
                continue
            started = t.meta.get("started", "")
            if not started:
                continue
            try:
                start = datetime.strptime(started, "%Y-%m-%d").date()
                t.aging_days = max(0, (today - start).days)
                t.state = str(t.aging_days)
            except ValueError:
                pass


# ── Column move business rules ───────────────────────────────


def apply_column_move_rules(task: Task, source_column: str, target_column: str) -> None:
    """Apply state and metadata changes when a task moves between columns.

    This encapsulates the column transition business logic.
    """
    now = datetime.now().strftime("%Y-%m-%d")

    if target_column == "Today":
        task.state = "1"
        task.meta["started"] = now
    elif target_column == "Done":
        task.state = "x"
        task.meta["completed"] = now
        task.meta.pop("started", None)
    elif target_column in ("Week", "Backlog"):
        task.state = " "
        task.meta.pop("started", None)


# ── Validation ──────────────────────────────────────────────


def validate_board(board: TaskBoard) -> list[str]:
    """Check the board for structural issues. Returns a list of warnings."""
    warnings: list[str] = []

    if not board.columns:
        warnings.append("No columns (## headings) found")

    ids: list[str] = []
    for tasks in board.columns.values():
        for t in tasks:
            if t.id:
                ids.append(t.id)
            else:
                preview = t.title[:30]
                warnings.append(f"Task '{preview}…' is missing an ID")

    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        warnings.append(f"Duplicate IDs: {dupes}")

    return warnings


# ── Tag parsing ──────────────────────────────────────────────


TAG_PATTERN = re.compile(r"#(\S+)")


def parse_tags(tags_input: str) -> list[str]:
    """Extract tags from a space-separated string like '#dev #ops'."""
    return TAG_PATTERN.findall(tags_input) if tags_input else []
