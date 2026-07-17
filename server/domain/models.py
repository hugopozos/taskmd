"""
Domain models for TaskMD.

Pure data classes with no infrastructure dependencies.
These represent the core business concepts of the application.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Task:
    """A single task in the kanban board."""

    id: str
    state: str  # ' ', 'x', or a numeric string like '1', '3', etc.
    title: str
    tags: list[str] = field(default_factory=list)
    aging_days: int = 0
    meta: dict[str, str] = field(default_factory=dict)

    @property
    def is_completed(self) -> bool:
        return self.state == "x"

    @property
    def is_pending(self) -> bool:
        return self.state == " "

    @property
    def is_active(self) -> bool:
        """In progress (numeric state)."""
        return self.state not in (" ", "x")


@dataclass
class TaskColumn:
    """A named column containing tasks."""

    name: str
    tasks: list[Task] = field(default_factory=list)


@dataclass
class TaskBoard:
    """The entire board: a mapping of column names to their tasks."""

    columns: dict[str, list[Task]] = field(default_factory=dict)

    @property
    def total_tasks(self) -> int:
        return sum(len(tasks) for tasks in self.columns.values())

    def get_column_names(self) -> list[str]:
        return list(self.columns.keys())

    def find_task(self, task_id: str) -> Optional[tuple[str, Task]]:
        """Locate a task by ID across all columns.

        Returns (column_name, task) or None.
        """
        for col_name, tasks in self.columns.items():
            for task in tasks:
                if task.id == task_id:
                    return col_name, task
        return None

    def remove_task(self, task_id: str) -> Optional[Task]:
        """Remove a task by ID. Returns the removed task or None."""
        for tasks in self.columns.values():
            for i, task in enumerate(tasks):
                if task.id == task_id:
                    return tasks.pop(i)
        return None

    def move_task(self, task_id: str, target_column: str) -> bool:
        """Move a task from its current column to another.

        Returns True if moved, False if not found.
        """
        found = self.find_task(task_id)
        if found is None:
            return False
        source_col, task = found
        if source_col == target_column:
            return True  # Already there, no-op
        self.columns[source_col].remove(task)
        self.columns.setdefault(target_column, []).append(task)
        return True
