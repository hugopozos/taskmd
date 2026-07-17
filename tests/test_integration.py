"""
Integration tests for the TaskMD API.

Tests the full HTTP lifecycle: create, read, update, delete, validate.
Uses temporary directory to avoid touching the real todo.md.
"""

import json
import os
import shutil
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import uvicorn
from server.main import app


class TestAPI:
    """Integration tests using the real FastAPI server."""

    _server: uvicorn.Server | None = None
    _thread: threading.Thread | None = None
    _tmpdir: str | None = None
    PORT = 8770
    BASE = f"http://127.0.0.1:{PORT}"

    @classmethod
    def setup_class(cls):
        """Start the server using a temp directory for todo.md."""
        cls._tmpdir = tempfile.mkdtemp(prefix="taskmd_test_")

        from server.main import PROJECT_DIR as real_project_dir

        tmp_todo = Path(cls._tmpdir) / "todo.md"
        tmp_archive = Path(cls._tmpdir) / "archive"

        # Monkey-patch dependencies in the router
        import server.api.router as router_mod
        from server.infrastructure.file_repository import FileRepository
        from server.infrastructure.git_service import GitService

        new_repo = FileRepository(tmp_todo, tmp_archive)
        new_git = GitService(real_project_dir)
        router_mod.router._repo = new_repo
        router_mod.router._git = new_git

        # Also patch the main module's references
        import server.main as sm
        sm.repo = new_repo
        sm.git = new_git

        # Start server
        config = uvicorn.Config(
            app, host="127.0.0.1", port=cls.PORT, log_level="error"
        )
        cls._server = uvicorn.Server(config)
        cls._thread = threading.Thread(target=cls._server.run, daemon=True)
        cls._thread.start()
        time.sleep(2)

    @classmethod
    def teardown_class(cls):
        """Stop the server and clean up."""
        if cls._server:
            cls._server.should_exit = True
            if cls._thread:
                cls._thread.join(timeout=3)
        if cls._tmpdir:
            shutil.rmtree(cls._tmpdir, ignore_errors=True)

