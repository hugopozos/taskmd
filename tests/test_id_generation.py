"""Tests for ID generation and collision resolution."""

import hashlib

from server.domain.models import Task, TaskBoard
from server.domain.task_service import (
    assign_missing_ids,
    collect_ids,
    generate_id,
)


class TestGenerateId:
    def test_generates_short_hash(self):
        task_id = generate_id("Buy groceries", "2026-07-14T10:00:00", set())
        assert len(task_id) in (3, 4, 5, 6)
        assert all(c in "0123456789abcdef" for c in task_id)

    def test_deterministic_same_input(self):
        existing: set[str] = set()
        id1 = generate_id("Same title", "2026-07-14T10:00:00", existing)
        existing.add(id1)
        id2 = generate_id("Same title", "2026-07-14T10:00:00", existing - {id1})
        assert id1 == id2

    def test_different_titles_different_ids(self):
        id1 = generate_id("Title A", "2026-07-14T10:00:00", set())
        id2 = generate_id("Title B", "2026-07-14T10:00:00", set())
        assert id1 != id2

    def test_collision_extends(self):
        """If first 3 chars collide, extend to 4, 5, 6."""
        # Force collision by pre-populating with the first 3 chars
        existing: set[str] = {"abc"}

        # We need to find a title whose first 3 hash chars are 'abc'
        # Deterministic approach: compute and check
        base = hashlib.sha256("test|2026-01-01T00:00:00".encode()).hexdigest()
        first_three = base[:3]

        existing2: set[str] = {first_three}
        task_id = generate_id("test", "2026-01-01T00:00:00", existing2)
        # Should be at least 4 chars to avoid collision
        assert len(task_id) >= 4

    def test_fallback_to_random(self):
        """When all hash lengths collide, fall back to random."""
        # Pre-populate with all possible 6-char prefixes for this input
        # (unlikely in practice, but code should handle it)
        base = hashlib.sha256("test|2026-01-01".encode()).hexdigest()
        existing: set[str] = {base[:3], base[:4], base[:5], base[:6]}
        task_id = generate_id("test", "2026-01-01", existing)
        assert len(task_id) == 6  # secrets.token_hex(3) outputs 6 chars


class TestCollectIds:
    def test_collects_all_ids(self):
        board = TaskBoard(
            columns={
                "Backlog": [
                    Task(id="abc", state=" ", title="A"),
                    Task(id="def", state=" ", title="B"),
                ],
                "Done": [
                    Task(id="ghi", state="x", title="C"),
                ],
            }
        )
        ids = collect_ids(board)
        assert ids == {"abc", "def", "ghi"}

    def test_skips_empty_ids(self):
        board = TaskBoard(
            columns={
                "Backlog": [
                    Task(id="", state=" ", title="No ID"),
                    Task(id="abc", state=" ", title="Has ID"),
                ],
            }
        )
        ids = collect_ids(board)
        assert ids == {"abc"}


class TestAssignMissingIds:
    def test_assigns_to_missing(self):
        board = TaskBoard(
            columns={
                "Backlog": [
                    Task(id="", state=" ", title="No ID"),
                    Task(id="abc", state=" ", title="Has ID"),
                ],
            }
        )
        changed = assign_missing_ids(board)
        assert changed
        assert board.columns["Backlog"][0].id != ""
        assert board.columns["Backlog"][0].id != "abc"
        assert board.columns["Backlog"][1].id == "abc"

    def test_no_change_if_all_have_ids(self):
        board = TaskBoard(
            columns={
                "Backlog": [
                    Task(id="abc", state=" ", title="A"),
                    Task(id="def", state=" ", title="B"),
                ],
            }
        )
        changed = assign_missing_ids(board)
        assert not changed

    def test_no_duplicates_assigned(self):
        board = TaskBoard(
            columns={
                "Backlog": [
                    Task(id="", state=" ", title="Task 1"),
                    Task(id="", state=" ", title="Task 2"),
                ],
            }
        )
        changed = assign_missing_ids(board)
        assert changed
        id1 = board.columns["Backlog"][0].id
        id2 = board.columns["Backlog"][1].id
        assert id1 != id2
