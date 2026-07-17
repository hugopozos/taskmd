"""
TaskMD — Markdown-native Kanban Backend
=======================================
FastAPI server that reads/writes todo.md atomically.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.api.router import router
from server.infrastructure.file_repository import FileRepository
from server.infrastructure.git_service import GitService

# ── Paths ────────────────────────────────────────────────────

PROJECT_DIR = Path(__file__).resolve().parent.parent
TODO_FILE = PROJECT_DIR / "todo.md"
ARCHIVE_DIR = PROJECT_DIR / "archive"
FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"

# ── App factory ──────────────────────────────────────────────

app = FastAPI(title="TaskMD", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8765",
        "http://localhost:8765",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Dependency injection ─────────────────────────────────────

repo = FileRepository(TODO_FILE, ARCHIVE_DIR)
git = GitService(PROJECT_DIR)

# Pass dependencies into the router
router._repo = repo  # type: ignore[attr-defined]
router._git = git  # type: ignore[attr-defined]

app.include_router(router)


# ── Lifecycle ────────────────────────────────────────────────


@app.on_event("startup")
async def startup() -> None:
    """Initialise the application on startup."""
    repo.ensure_archive_dir()

    # Create default todo.md if it doesn't exist
    board = repo.ensure_todo_file()

    # Ensure every task has an ID (migration for hand-edited files)
    from server.domain.task_service import assign_missing_ids

    if assign_missing_ids(board):
        repo.save(board)

    # Crash recovery: commit any uncommitted changes
    git.recover()


# ── Static frontend mount (optional) ─────────────────────────


def mount_frontend() -> None:
    """Mount the frontend static files if the dist directory exists."""
    if FRONTEND_DIST.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(FRONTEND_DIST), html=True),
            name="frontend",
        )


mount_frontend()
