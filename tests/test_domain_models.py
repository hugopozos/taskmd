"""Tests for domain models (Task, TaskBoard, TaskColumn)."""

from server.domain.models import Task, TaskBoard


class TestTaskProperties:
    def test_is_completed(self):
        assert Task(id="abc", state="x", title="Done task").is_completed
        assert not Task(id="abc", state=" ", title="Pending").is_completed
        assert not Task(id="abc", state="3", title="Active").is_completed

    def test_is_pending(self):
        assert Task(id="abc", state=" ", title="Pending").is_pending
        assert not Task(id="abc", state="x", title="Done").is_pending
        assert not Task(id="abc", state="3", title="Active").is_pending

    def test_is_active(self):
        assert Task(id="abc", state="3", title="Active").is_active
        assert Task(id="abc", state="1", title="Active").is_active
        assert not Task(id="abc", state=" ", title="Pending").is_active
        assert not Task(id="abc", state="x", title="Done").is_active


class TestTaskBoard:
    def test_empty_board(self):
        board = TaskBoard()
        assert board.total_tasks == 0
        assert board.get_column_names() == []

    def test_find_task(self):
        task = Task(id="a1b", state=" ", title="Test")
        board = TaskBoard(columns={"Backlog": [task]})
        found = board.find_task("a1b")
        assert found is not None
        col, t = found
        assert col == "Backlog"
        assert t is task

    def test_find_task_not_found(self):
        board = TaskBoard()
        assert board.find_task("nonexistent") is None

    def test_remove_task(self):
        task = Task(id="a1b", state=" ", title="Test")
        board = TaskBoard(columns={"Backlog": [task]})
        removed = board.remove_task("a1b")
        assert removed is task
        assert board.total_tasks == 0

    def test_remove_nonexistent(self):
        board = TaskBoard()
        assert board.remove_task("nope") is None

    def test_move_task(self):
        task = Task(id="a1b", state=" ", title="Test")
        board = TaskBoard(columns={"Backlog": [task]})
        moved = board.move_task("a1b", "Today")
        assert moved is True
        assert board.total_tasks == 1
        assert board.find_task("a1b") is not None
        col, _ = board.find_task("a1b")  # type: ignore
        assert col == "Today"
        assert "Backlog" in board.columns
        assert len(board.columns["Backlog"]) == 0

    def test_move_to_same_column(self):
        task = Task(id="a1b", state=" ", title="Test")
        board = TaskBoard(columns={"Backlog": [task]})
        moved = board.move_task("a1b", "Backlog")
        assert moved is True
        assert len(board.columns["Backlog"]) == 1

    def test_move_nonexistent(self):
        board = TaskBoard()
        assert board.move_task("nope", "Today") is False
