"""
Pydantic schemas for API request/response validation.

Separated from domain models to keep a clean boundary between
the internal representation (dataclasses) and the wire format.
"""

from typing import Optional

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    """Request body for creating a new task."""

    title: str = Field(..., min_length=1, max_length=500)
    column: str = "Backlog"
    tags: str = ""  # Space-separated, e.g. "#dev #ops"
    note: str = ""


class TaskUpdateRequest(BaseModel):
    """Request body for updating an existing task."""

    column: Optional[str] = None
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    tags: Optional[str] = None
    note: Optional[str] = None


class TaskResponse(BaseModel):
    """Task as returned to the client."""

    id: str
    state: str
    title: str
    tags: list[str]
    aging_days: int
    meta: dict[str, str]


class TodoResponse(BaseModel):
    """Full board response."""

    columns: dict[str, list[TaskResponse]]


class ValidateResponse(BaseModel):
    """Validation result."""

    valid: bool
    columns: list[str] = []
    total_tasks: int = 0
    warnings: list[str] = []
