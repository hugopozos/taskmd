"""Tests for markdown parser and writer roundtrip.

The golden rule: parse_todo(build_markdown(board)) should equal board.
"""

from server.domain.models import Task, TaskBoard
from server.infrastructure.markdown_parser import parse_todo
from server.infrastructure.markdown_writer import build_markdown


def _roundtrip(board: TaskBoard) -> TaskBoard:
    """Serialize a board to markdown and parse it back."""
    md = build_markdown(board)
    return parse_todo(md)


def _tasks_equal(a: Task, b: Task) -> bool:
    return (
        a.id == b.id
        and a.state == b.state
        and a.title == b.title
        and a.tags == b.tags
        and a.meta == b.meta
    )


class TestRoundtrip:
    def test_empty_board(self):
        original = TaskBoard(columns={"Backlog": [], "Today": [], "Done": []})
        result = _roundtrip(original)
        assert set(result.columns.keys()) == {"Backlog", "Today", "Done"}
        for name in original.columns:
            assert len(result.columns[name]) == 0

    def test_single_task_no_metadata(self):
        original = TaskBoard(
            columns={
                "Backlog": [
                    Task(id="abc", state=" ", title="Read a book", tags=["dev"]),
                ]
            }
        )
        result = _roundtrip(original)
        assert len(result.columns["Backlog"]) == 1
        t = result.columns["Backlog"][0]
        assert t.id == "abc"
        assert t.state == " "
        assert t.title == "Read a book"
        assert t.tags == ["dev"]

    def test_single_task_with_metadata(self):
        original = TaskBoard(
            columns={
                "Today": [
                    Task(
                        id="def",
                        state="3",
                        title="Fix bug",
                        tags=[],
                        meta={
                            "created": "2026-07-14",
                            "started": "2026-07-14",
                            "note": "Critical issue in parser",
                        },
                    ),
                ]
            }
        )
        result = _roundtrip(original)
        t = result.columns["Today"][0]
        assert t.id == "def"
        assert t.state == "3"
        assert t.meta["created"] == "2026-07-14"
        assert t.meta["note"] == "Critical issue in parser"

    def test_multiple_columns_and_tasks(self):
        original = TaskBoard(
            columns={
                "Backlog": [
                    Task(id="a1b", state=" ", title="Task A", tags=["dev"]),
                    Task(id="a2b", state=" ", title="Task B", tags=[], meta={"due": "2026-08-01"}),
                ],
                "Done": [
                    Task(id="b1c", state="x", title="Task C", tags=["docs"], meta={"completed": "2026-07-10"}),
                ],
            }
        )
        result = _roundtrip(original)
        assert result.total_tasks == 3
        assert len(result.columns["Backlog"]) == 2
        assert len(result.columns["Done"]) == 1

        # Verify data integrity
        t = result.columns["Done"][0]
        assert t.id == "b1c"
        assert t.state == "x"
        assert t.title == "Task C"
        assert t.tags == ["docs"]
        assert t.meta["completed"] == "2026-07-10"

    def test_multiline_note(self):
        original = TaskBoard(
            columns={
                "Backlog": [
                    Task(
                        id="abc",
                        state=" ",
                        title="Multiline test",
                        meta={
                            "note": "Line one\nLine two\n\nParagraph after blank",
                        },
                    ),
                ]
            }
        )
        result = _roundtrip(original)
        t = result.columns["Backlog"][0]
        assert t.meta["note"] == "Line one\nLine two\n\nParagraph after blank"

    def test_task_with_all_fields(self):
        original = TaskBoard(
            columns={
                "Week": [
                    Task(
                        id="fff",
                        state=" ",
                        title="Complete project",
                        tags=["dev", "urgent", "meta"],
                        meta={
                            "created": "2026-07-01",
                            "due": "2026-07-20",
                            "note": "Must finish this week",
                        },
                    ),
                ]
            }
        )
        result = _roundtrip(original)
        t = result.columns["Week"][0]
        assert t.id == "fff"
        assert t.title == "Complete project"
        assert t.tags == ["dev", "urgent", "meta"]
        assert t.meta["created"] == "2026-07-01"
        assert t.meta["due"] == "2026-07-20"
        assert t.meta["note"] == "Must finish this week"

    def test_parse_real_world_example(self):
        """Parse a realistic todo.md content."""
        content = """# Todo

## Backlog
- [ ] #dev Read book `#a1b`
  created: 2026-07-14

## Today
- [3] #dev Fix bug `#c2d`
  created: 2026-07-14
  started: 2026-07-14

## Done
- [x] Buy groceries `#e3f`
  created: 2026-07-13
  completed: 2026-07-14
"""
        board = parse_todo(content)
        assert set(board.columns.keys()) == {"Backlog", "Today", "Done"}
        assert board.total_tasks == 3

        backlog = board.columns["Backlog"][0]
        assert backlog.id == "a1b"
        assert backlog.title == "Read book"
        assert backlog.tags == ["dev"]
        assert backlog.meta["created"] == "2026-07-14"

        today = board.columns["Today"][0]
        assert today.id == "c2d"
        assert today.state == "3"
        assert today.aging_days == 3

        done = board.columns["Done"][0]
        assert done.id == "e3f"
        assert done.state == "x"
        assert done.meta["completed"] == "2026-07-14"

        # Roundtrip
        rebuilt = build_markdown(board)
        reparsed = parse_todo(rebuilt)
        assert reparsed.total_tasks == 3

        # Verify reconstruction of IDs
        assert reparsed.columns["Backlog"][0].id == "a1b"
        assert reparsed.columns["Today"][0].id == "c2d"

    def test_id_in_middle_of_line_is_removed(self):
        """IDs should only be at the end. Mid-line IDs should be stripped."""
        content = """# Todo

## Backlog
- [ ] Task with `#abc` in middle `#def`
"""
        board = parse_todo(content)
        t = board.columns["Backlog"][0]
        # The trailing ID should be 'def'
        assert t.id == "def"
        assert "`#abc`" not in t.title

    def test_no_id_present(self):
        """Tasks without IDs should get empty string as id."""
        content = """# Todo

## Backlog
- [ ] Simple task
"""
        board = parse_todo(content)
        t = board.columns["Backlog"][0]
        assert t.id == ""
        assert t.title == "Simple task"
