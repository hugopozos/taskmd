"""
Git integration service.

Handles automatic commits and crash recovery for the todo.md file.
This is a cross-cutting concern, isolated from business logic.
"""

import subprocess
from pathlib import Path


class GitService:
    """Manages Git operations for the project."""

    def __init__(self, project_dir: Path) -> None:
        self._project_dir = project_dir

    # ── Public API ─────────────────────────────────────────

    def commit(self, message: str) -> None:
        """Stage only todo.md + archive/ and commit."""
        self._run("git", "add", "todo.md", "archive/")
        self._run("git", "commit", "-m", message, "--allow-empty")

    def recover(self) -> None:
        """On startup, commit any uncommitted changes (crash recovery)."""
        result = self._run("git", "status", "--porcelain")
        if result.stdout.strip():
            self._run("git", "add", "todo.md", "archive/")
            self._run(
                "git",
                "commit",
                "-m",
                "recovery: auto-commit after restart",
                "--allow-empty",
            )

    # ── Internals ──────────────────────────────────────────

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            cwd=self._project_dir,
            capture_output=True,
            text=True,
        )

    @property
    def is_available(self) -> bool:
        """Check if git is available and the directory is a git repo."""
        try:
            result = self._run("git", "rev-parse", "--git-dir")
            return result.returncode == 0
        except FileNotFoundError:
            return False
