"""
API endpoints for TaskMD.

Thin layer: receives HTTP requests, delegates to domain services,
returns HTTP responses. No business logic here.
"""

import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException

from server.domain.models import Task, TaskBoard
from server.domain.schemas import (
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskResponse,
    TodoResponse,
    ValidateResponse,
)
from server.domain.task_service import (
    apply_column_move_rules,
    assign_missing_ids,
    collect_ids,
    generate_id,
    parse_tags,
    recalculate_aging,
    validate_board,
)
from server.infrastructure.file_repository import FileRepository
from server.infrastructure.git_service import GitService

# Global write lock (serialises all modifications to todo.md)
_write_lock = asyncio.Lock()

router = APIRouter()


def _setup(repo: FileRepository, git: GitService) -> None:
    """Inject dependencies into the router.

    Called once during application startup.
    """
    router._repo = repo  # type: ignore[attr-defined]
    router._git = git  # type: ignore[attr-defined]


def _task_to_response(task: Task) -> TaskResponse:
    """Convert a domain Task to a response schema."""
    return TaskResponse(
        id=task.id,
        state=task.state,
        title=task.title,
        tags=task.tags,
        aging_days=task.aging_days,
        meta=task.meta,
    )


def _board_to_response(board: TaskBoard) -> TodoResponse:
    """Convert a domain TaskBoard to a response schema."""
    return TodoResponse(
        columns={
            name: [_task_to_response(t) for t in tasks]
            for name, tasks in board.columns.items()
        }
    )


# ── Endpoints ────────────────────────────────────────────────


@router.get("/api/todo", response_model=TodoResponse)
async def get_todo():
    """Return all tasks organised by column, with aging pre-calculated."""
    board = router._repo.load()  # type: ignore[attr-defined]
    recalculate_aging(board)
    return _board_to_response(board)


@router.post("/api/tasks", response_model=dict)
async def create_task(body: TaskCreateRequest):
    """Create a new task."""
    repo: FileRepository = router._repo  # type: ignore[attr-defined]
    git: GitService = router._git  # type: ignore[attr-defined]

    async with _write_lock:
        board = repo.load()

        # Determine target column
        column = body.column if body.column in board.columns else "Backlog"

        # Generate ID
        existing = collect_ids(board)
        new_id = generate_id(body.title, datetime.now().isoformat(), existing)

        # Parse tags
        tags = parse_tags(body.tags)

        # Build task
        task = Task(
            id=new_id,
            state=" ",
            title=body.title,
            tags=tags,
            aging_days=0,
            meta={"created": datetime.now().strftime("%Y-%m-%d")},
        )
        if body.note:
            task.meta["note"] = body.note

        board.columns.setdefault(column, []).append(task)
        repo.save(board)
        git.commit(f"task: add '{body.title[:40]}' to {column}")

        recalculate_aging(board)

        return {
            "ok": True,
            "task": _task_to_response(task).model_dump(),
            "columns": _board_to_response(board).model_dump()["columns"],
        }


@router.patch("/api/tasks/{task_id}", response_model=dict)
async def update_task(task_id: str, body: TaskUpdateRequest):
    """Move, edit, or complete a task."""
    repo: FileRepository = router._repo  # type: ignore[attr-defined]
    git: GitService = router._git  # type: ignore[attr-defined]

    async with _write_lock:
        board = repo.load()

        found = board.find_task(task_id)
        if found is None:
            raise HTTPException(404, f"Task {task_id} not found")

        source_col, task = found

        # Column move
        if body.column is not None and body.column != source_col:
            board.move_task(task_id, body.column)
            apply_column_move_rules(task, source_col, body.column)

        # Field edits
        if body.title is not None:
            task.title = body.title
        if body.tags is not None:
            task.tags = parse_tags(body.tags)
        if body.note is not None:
            task.meta["note"] = body.note

        repo.save(board)
        git.commit(f"task: update '{task.title[:40]}'")

        recalculate_aging(board)

        return {
            "ok": True,
            "task": _task_to_response(task).model_dump(),
            "columns": _board_to_response(board).model_dump()["columns"],
        }


@router.delete("/api/tasks/{task_id}", response_model=dict)
async def delete_task(task_id: str):
    """Delete a task permanently."""
    repo: FileRepository = router._repo  # type: ignore[attr-defined]
    git: GitService = router._git  # type: ignore[attr-defined]

    async with _write_lock:
        board = repo.load()

        task = board.remove_task(task_id)
        if task is None:
            raise HTTPException(404, f"Task {task_id} not found")

        repo.save(board)
        git.commit(f"task: delete '{task.title[:40]}'")

        recalculate_aging(board)

        return {
            "ok": True,
            "columns": _board_to_response(board).model_dump()["columns"],
        }


@router.get("/api/validate", response_model=ValidateResponse)
async def validate():
    """Check the todo.md for structural issues."""
    repo: FileRepository = router._repo  # type: ignore[attr-defined]

    if not repo.exists():
        return ValidateResponse(valid=False, warnings=["todo.md does not exist"])

    board = repo.load()
    warnings = validate_board(board)

    return ValidateResponse(
        valid=len(warnings) == 0,
        columns=board.get_column_names(),
        total_tasks=board.total_tasks,
        warnings=warnings,
    )
