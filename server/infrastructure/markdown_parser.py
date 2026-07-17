"""
Markdown parser for todo.md format.

Parses the custom Markdown format into domain models.
See SPEC.md for the full format specification.
"""

import re
from typing import Optional

from server.domain.models import Task, TaskBoard
from server.domain.task_service import ID_PATTERN, TAG_PATTERN


def parse_todo(content: str) -> TaskBoard:
    """Parse a todo.md string into a TaskBoard.

    Format:
    ```
    # Todo

    ## ColumnName
    - [<state>] [#tag ...] <title> `#<id>`
      meta_key: value
    ```
    """
    board = TaskBoard()
    current_column: Optional[str] = None
    last_meta_key: Optional[str] = None

    for line in content.split("\n"):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # New column: "## Name"
        if indent == 0 and line.startswith("## "):
            current_column = stripped[3:].strip()
            board.columns.setdefault(current_column, [])
            last_meta_key = None
            continue

        # New task: "- [<state>] ..."
        if indent == 0 and line.startswith("- [") and current_column is not None:
            task = _parse_task_line(line)
            if task is not None:
                board.columns[current_column].append(task)
            last_meta_key = None
            continue

        # Metadata of the *last* task in the current column
        if indent >= 2 and current_column and board.columns[current_column]:
            key, val = _parse_meta_line(stripped)
            if key is not None:
                board.columns[current_column][-1].meta[key] = val
                last_meta_key = key
            elif last_meta_key is not None:
                # Continuation of previous metadata value (multiline)
                prev = board.columns[current_column][-1].meta[last_meta_key]
                board.columns[current_column][-1].meta[last_meta_key] = prev + "\n" + stripped

    return board


def _parse_task_line(line: str) -> Optional[Task]:
    """Parse a single `- [<state>] …` line into a Task."""
    m = re.match(r"- \[(.)\]\s*(.*)", line)
    if not m:
        return None

    state, rest = m.group(1), m.group(2)

    # Extract trailing ID from the original line (must be at end)
    id_match = ID_PATTERN.search(rest)
    task_id: Optional[str] = id_match.group(1) if id_match else None

    # Remove the ID token from rest
    if id_match:
        rest = rest[: id_match.start()].strip()
    else:
        # Also strip stray backtick+hash patterns
        rest = re.sub(r"`\s*#[0-9a-f]{3,6}\s*`", "", rest).strip()

    # Remove any trailing backtick-wrapped IDs that may remain
    rest = ID_PATTERN.sub("", rest).strip()

    # Extract tags: #word that are NOT backtick-wrapped IDs
    tags = TAG_PATTERN.findall(rest)
    title = rest
    for tag in tags:
        title = title.replace(f"#{tag}", "").strip()

    title = title.strip()
    if not title:
        return None

    aging_days = int(state) if state not in (" ", "x") else 0

    return Task(
        id=task_id or "",
        state=state,
        title=title,
        tags=tags,
        aging_days=aging_days,
        meta={},
    )


def _parse_meta_line(line: str) -> tuple[Optional[str], Optional[str]]:
    """Parse a metadata line like '  key: value'."""
    idx = line.find(":")
    if idx > 0:
        key = line[:idx].strip()
        # Metadata keys are single words without spaces
        if " " not in key:
            return key, line[idx + 1 :].strip()
    return None, None
