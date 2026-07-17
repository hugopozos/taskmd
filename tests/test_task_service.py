"""Tests for domain service functions (aging, validation, column rules)."""

from datetime import date
from unittest.mock import patch

from server.domain.models import Task, TaskBoard
from server.domain.task_service import (
    apply_column_move_rules,
    recalculate_aging,
    validate_board,
    parse_tags,
)


class TestRecalculateAging:
    def test_no_change_for_non_today(self):
        board = TaskBoard(
            columns={
                "Backlog": [
                    Task(id="abc", state=" ", title="Task"),
                ],
            }
        )
        recalculate_aging(board)
        assert board.columns["Backlog"][0].aging_days == 0

    def test_no_change_for_completed_in_today(self):
        board = TaskBoard(
            columns={
                "Today": [
                    Task(id="abc", state="x", title="Done", aging_days=5),
                ],
            }
        )
        recalculate_aging(board)
        assert board.columns["Today"][0].aging_days == 5  # Unchanged

    @patch("server.domain.task_service.date")
    def test_calculates_correct_days(self, mock_date):
        mock_date.today.return_value = date(2026, 7, 16)
        board = TaskBoard(
            columns={
                "Today": [
                    Task(
                        id="abc",
                        state="1",
                        title="Active task",
                        meta={"started": "2026-07-14"},
                    ),
                ],
            }
        )
        recalculate_aging(board)
        t = board.columns["Today"][0]
        assert t.aging_days == 2  # July 16 - July 14
        assert t.state == "2"

    @patch("server.domain.task_service.date")
    def test_minimum_zero_days(self, mock_date):
        """If started in the future, should return 0, not negative."""
        mock_date.today.return_value = date(2026, 7, 10)
        board = TaskBoard(
            columns={
                "Today": [
                    Task(
                        id="abc",
                        state="1",
                        title="Future task",
                        meta={"started": "2026-07-14"},
                    ),
                ],
            }
        )
        recalculate_aging(board)
        assert board.columns["Today"][0].aging_days == 0

    def test_invalid_date_format_ignored(self):
        board = TaskBoard(
            columns={
                "Today": [
                    Task(
                        id="abc",
                        state="1",
                        title="Bad date",
                        meta={"started": "not-a-date"},
                    ),
                ],
            }
        )
        recalculate_aging(board)  # Should not raise
        assert board.columns["Today"][0].aging_days == 0

    def test_no_started_meta(self):
        board = TaskBoard(
            columns={
                "Today": [
                    Task(id="abc", state="1", title="No started date"),
                ],
            }
        )
        recalculate_aging(board)
        assert board.columns["Today"][0].aging_days == 0


class TestApplyColumnMoveRules:
    def test_move_to_today(self):
        task = Task(id="abc", state=" ", title="Task")
        apply_column_move_rules(task, "Backlog", "Today")
        assert task.state == "1"
        assert "started" in task.meta

    def test_move_to_done(self):
        task = Task(id="abc", state="3", title="Task", meta={"started": "2026-07-14"})
        apply_column_move_rules(task, "Today", "Done")
        assert task.state == "x"
        assert "completed" in task.meta
        assert "started" not in task.meta

    def test_move_to_week(self):
        task = Task(id="abc", state="3", title="Task", meta={"started": "2026-07-14"})
        apply_column_move_rules(task, "Today", "Week")
        assert task.state == " "
        assert "started" not in task.meta

    def test_move_to_backlog(self):
        task = Task(id="abc", state="3", title="Task", meta={"started": "2026-07-14"})
        apply_column_move_rules(task, "Today", "Backlog")
        assert task.state == " "
        assert "started" not in task.meta

    def test_move_to_custom_column(self):
        """Custom columns (not Today/Done/Week/Backlog) should not change state."""
        task = Task(id="abc", state="3", title="Task", meta={"started": "2026-07-14"})
        apply_column_move_rules(task, "Today", "Custom")
        # No rules for custom columns, so state stays as is
        assert task.state == "3"


class TestValidateBoard:
    def test_valid_board(self):
        board = TaskBoard(
            columns={
                "Backlog": [Task(id="abc", state=" ", title="A")],
                "Done": [Task(id="def", state="x", title="B")],
            }
        )
        warnings = validate_board(board)
        assert warnings == []

    def test_no_columns(self):
        board = TaskBoard()
        warnings = validate_board(board)
        assert "No columns" in warnings[0]

    def test_missing_id(self):
        board = TaskBoard(
            columns={
                "Backlog": [Task(id="", state=" ", title="No ID here")],
            }
        )
        warnings = validate_board(board)
        assert any("missing an ID" in w for w in warnings)

    def test_duplicate_ids(self):
        board = TaskBoard(
            columns={
                "Backlog": [Task(id="abc", state=" ", title="A")],
                "Today": [Task(id="abc", state="1", title="B")],
            }
        )
        warnings = validate_board(board)
        assert any("Duplicate" in w for w in warnings)


class TestParseTags:
    def test_empty_string(self):
        assert parse_tags("") == []

    def test_single_tag(self):
        assert parse_tags("#dev") == ["dev"]

    def test_multiple_tags(self):
        assert parse_tags("#dev #ops #urgent") == ["dev", "ops", "urgent"]

    def test_tags_with_extra_spaces(self):
        assert parse_tags("  #dev  #ops  ") == ["dev", "ops"]

    def test_no_tags(self):
        assert parse_tags("just a string") == []
