"""
File repository — persistence layer for the TaskBoard.

Handles atomic file I/O and provides a clean interface for
reading/writing the Markdown file to disk.
"""

import os
import tempfile
from pathlib import Path

from server.domain.models import TaskBoard
from server.infrastructure.markdown_parser import parse_todo
from server.infrastructure.markdown_writer import build_markdown

DEFAULT_COLUMNS = ["Backlog", "Week", "Today", "Done"]


class FileRepository:
    """Reads and writes a TaskBoard from/to a Markdown file on disk."""

    def __init__(self, todo_path: Path, archive_dir: Path) -> None:
        self._todo_path = todo_path
        self._archive_dir = archive_dir

    # ── Public API ─────────────────────────────────────────

    def exists(self) -> bool:
        return self._todo_path.exists()

    def load(self) -> TaskBoard:
        """Read todo.md and parse it into a TaskBoard.

        If the file doesn't exist, returns an empty board with default columns.
        """
        if not self._todo_path.exists():
            return self._create_default_board()

        content = self._todo_path.read_text(encoding="utf-8")
        return parse_todo(content)

    def save(self, board: TaskBoard) -> None:
        """Atomically write a TaskBoard to todo.md."""
        content = build_markdown(board)
        self._atomic_write(self._todo_path, content)

    def ensure_archive_dir(self) -> None:
        """Create the archive directory if it doesn't exist."""
        self._archive_dir.mkdir(parents=True, exist_ok=True)

    def ensure_todo_file(self) -> TaskBoard:
        """Create a default todo.md if it doesn't exist, and return it."""
        if not self._todo_path.exists():
            board = self._create_default_board()
            self.save(board)
            return board
        return self.load()

    # ── Internals ──────────────────────────────────────────

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        """Atomically write content to a file using a temporary file + rename.

        This prevents partial writes from being visible to readers.
        Falls back to direct write if the filesystem doesn't support rename
        (e.g., broken Docker volume mounts on Windows).
        """
        tmp_path = path.with_suffix(".md.tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8", newline="") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_path, path)

        except (OSError, PermissionError):
            # Fallback: direct write (e.g., cross-device rename on Docker bind mounts)
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

    @staticmethod
    def _create_default_board() -> TaskBoard:
        """Create a board with the default column structure but no tasks."""
        return TaskBoard(columns={col: [] for col in DEFAULT_COLUMNS})
