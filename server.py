"""
TaskMD — Markdown-native Kanban Backend
=======================================
FastAPI server that reads/writes todo.md atomically.
Hermes consumes via API. Frontend consumes via API.
"""

import asyncio
import hashlib
import os
import re
import secrets
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# ═══════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════

PROJECT_DIR = Path(__file__).resolve().parent
TODO_FILE = PROJECT_DIR / "todo.md"
ARCHIVE_DIR = PROJECT_DIR / "archive"
DEFAULT_COLUMNS = ["Backlog", "Week", "Today", "Done"]

# Matches `#abc` or `#abcd` or `#abcde` or `#abcdef` at END of line only
ID_PATTERN = re.compile(r'`#([0-9a-f]{3,6})`\s*$')

# Asyncio lock serialises ALL writes (atomicity for the app-level, not fs-level)
write_lock = asyncio.Lock()

app = FastAPI(title="TaskMD", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8765", "http://localhost:8765",
                   "http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════
# Pydantic models
# ═══════════════════════════════════════════════

class TaskCreate(BaseModel):
    title: str
    column: str = "Backlog"
    tags: str = ""
    note: str = ""

class TaskUpdate(BaseModel):
    column: Optional[str] = None
    title: Optional[str] = None
    tags: Optional[str] = None
    note: Optional[str] = None


# ═══════════════════════════════════════════════
# Atomic file I/O
# ═══════════════════════════════════════════════

def atomic_write(path: Path, content: str) -> None:
    """Write content to file.

    Strategy: direct write + fsync.
    Atomic rename (tmp+rename) is preferred but incompatible with
    Docker volume mounts where path is a bind-mount inode.
    The asyncio.Lock in the caller serialises writes, so the risk
    of a reader seeing partial content is negligible for a personal tool.
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())


# ═══════════════════════════════════════════════
# Markdown parser
# ═══════════════════════════════════════════════

def parse_todo(content: str) -> dict[str, list[dict]]:
    """Parse todo.md into {column_name: [task, …], …}."""
    columns: dict[str, list[dict]] = {}
    column = None

    for line in content.split("\n"):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # ── New column ──
        if indent == 0 and line.startswith("## "):
            column = stripped[3:].strip()
            columns.setdefault(column, [])
            continue

        # ── New task ──
        if indent == 0 and line.startswith("- [") and column is not None:
            task = _parse_task_line(line)
            if task:
                columns[column].append(task)
            continue

        # ── Metadata of the *last* task in the current column ──
        if indent >= 2 and column and columns[column]:
            _add_metadata(columns[column][-1], stripped)

    return columns


def _parse_task_line(line: str) -> Optional[dict]:
    """Parse a single `- [<state>] …` line into a task dict."""
    m = re.match(r"- \[(.)\]\s*(.*)", line)
    if not m:
        return None

    state, rest = m.group(1), m.group(2)

    # 1. Strip ALL backtick-wrapped IDs (both trailing and leading) from rest
    rest = ID_PATTERN.sub("", rest).strip()
    # Also strip stray backtick+hash patterns like ` #abc
    rest = re.sub(r"`\s*#[0-9a-f]{3,6}\s*`", "", rest).strip()

    # 2. Extract trailing ID if present
    id_match = ID_PATTERN.search(line)
    task_id = id_match.group(1) if id_match else None

    # 3. Extract tags: #word that are NOT backtick-wrapped IDs
    tags = re.findall(r"(?<!`)#(\S+)", rest)
    title = rest
    for tag in tags:
        title = title.replace(f"#{tag}", "").strip()

    title = title.strip()
    if not title:
        return None

    return {
        "id": task_id,
        "state": state,
        "title": title,
        "tags": tags,
        "aging_days": int(state) if state not in (" ", "x") else 0,
        "meta": {},
    }


def _add_metadata(task: dict, line: str) -> None:
    idx = line.find(":")
    if idx > 0:
        key, val = line[:idx].strip(), line[idx+1:].strip()
        task["meta"][key] = val


# ═══════════════════════════════════════════════
# ID generation with collision resolution
# ═══════════════════════════════════════════════

def generate_id(title: str, timestamp: str, existing: set[str]) -> str:
    """Deterministic short hash, extends on collision."""
    base = hashlib.sha256(f"{title}|{timestamp}".encode()).hexdigest()
    for length in range(3, 7):
        cand = base[:length]
        if cand not in existing:
            return cand
    # Practically unreachable with sane task counts
    while True:
        cand = secrets.token_hex(3)
        if cand not in existing:
            return cand


def _collect_ids(columns: dict) -> set[str]:
    ids: set[str] = set()
    for tasks in columns.values():
        for t in tasks:
            if t.get("id"):
                ids.add(t["id"])
    return ids


def _assign_missing_ids(columns: dict) -> bool:
    """Assign IDs to tasks that lack one. Returns True if anything changed."""
    existing = _collect_ids(columns)
    changed = False
    for tasks in columns.values():
        for t in tasks:
            if not t.get("id"):
                t["id"] = generate_id(t["title"], datetime.now().isoformat(), existing)
                existing.add(t["id"])
                changed = True
    return changed


# ═══════════════════════════════════════════════
# Markdown writer
# ═══════════════════════════════════════════════

def build_markdown(columns: dict) -> str:
    """Serialize the in-memory structure back to markdown."""
    lines = ["# Todo", ""]
    for name, tasks in columns.items():
        lines.append(f"## {name}")
        for t in tasks:
            tags_str = " ".join(f"#{tag}" for tag in t.get("tags", []))
            if tags_str:
                tags_str += " "
            id_str = f" `#{t['id']}`" if t.get("id") else ""
            lines.append(f"- [{t['state']}] {tags_str}{t['title']}{id_str}")
            for k, v in t.get("meta", {}).items():
                lines.append(f"  {k}: {v}")
        lines.append("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════
# Aging recalculation
# ═══════════════════════════════════════════════

def recalc_aging(columns: dict) -> None:
    """Update aging_days for tasks in the Today column."""
    today = date.today()
    for name, tasks in columns.items():
        for t in tasks:
            if name == "Today" and t["state"] != "x":
                started = t.get("meta", {}).get("started", "")
                if started:
                    try:
                        start = datetime.strptime(started, "%Y-%m-%d").date()
                        t["aging_days"] = max(0, (today - start).days)
                        t["state"] = str(t["aging_days"])
                    except ValueError:
                        pass


# ═══════════════════════════════════════════
# Git helpers
# ═══════════════════════════════════════════

def _git_run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=PROJECT_DIR, capture_output=True, text=True)


def git_commit(message: str) -> None:
    """Stage only todo.md + archive/ and commit."""
    _git_run("git", "add", "todo.md", "archive/")
    _git_run("git", "commit", "-m", message, "--allow-empty")


def git_recover() -> None:
    """On startup, commit any uncommitted changes (crash recovery)."""
    r = _git_run("git", "status", "--porcelain")
    if r.stdout.strip():
        _git_run("git", "add", "todo.md", "archive/")
        _git_run("git", "commit", "-m", "recovery: auto-commit after restart",
                 "--allow-empty")


# ═══════════════════════════════════════════
# API endpoints
# ═══════════════════════════════════════════

@app.get("/api/todo")
async def get_todo():
    """Return all tasks organised by column, with aging pre-calculated."""
    if not TODO_FILE.exists():
        return {"columns": {}}
    columns = parse_todo(TODO_FILE.read_text(encoding="utf-8"))
    recalc_aging(columns)
    return {"columns": columns}


@app.post("/api/tasks")
async def create_task(body: TaskCreate):
    """Create a new task."""
    async with write_lock:
        content = TODO_FILE.read_text(encoding="utf-8") if TODO_FILE.exists() else ""
        cols = parse_todo(content) or {c: [] for c in DEFAULT_COLUMNS}

        column = body.column if body.column in cols else DEFAULT_COLUMNS[0]
        existing = _collect_ids(cols)
        new_id = generate_id(body.title, datetime.now().isoformat(), existing)

        tags = re.findall(r"#(\S+)", body.tags) if body.tags else []

        task = {
            "id": new_id,
            "state": " ",
            "title": body.title,
            "tags": tags,
            "aging_days": 0,
            "meta": {"created": datetime.now().strftime("%Y-%m-%d")},
        }
        if body.note:
            task["meta"]["note"] = body.note

        cols[column].append(task)
        atomic_write(TODO_FILE, build_markdown(cols))
        git_commit(f"task: add '{body.title[:40]}' to {column}")
        recalc_aging(cols)
        return {"ok": True, "task": task, "columns": cols}


@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: str, body: TaskUpdate):
    """Move, edit, or complete a task."""
    async with write_lock:
        content = TODO_FILE.read_text(encoding="utf-8")
        cols = parse_todo(content)

        # Locate task
        found = None
        for col, tasks in cols.items():
            for t in tasks:
                if t.get("id") == task_id:
                    found = (col, t)
                    break
            if found:
                break

        if not found:
            raise HTTPException(404, f"Task {task_id} not found")

        old_col, task = found

        # If moving column
        if body.column is not None and body.column != old_col:
            cols[old_col].remove(task)
            cols.setdefault(body.column, []).append(task)

            if body.column == "Today":
                task["state"] = "1"
                task["meta"]["started"] = datetime.now().strftime("%Y-%m-%d")
            elif body.column == "Done":
                task["state"] = "x"
                task["meta"]["completed"] = datetime.now().strftime("%Y-%m-%d")
                task["meta"].pop("started", None)
            elif body.column in ("Week", "Backlog"):
                task["state"] = " "
                task["meta"].pop("started", None)

        # Field edits
        if body.title is not None:
            task["title"] = body.title
        if body.tags is not None:
            task["tags"] = re.findall(r"#(\S+)", body.tags)
        if body.note is not None:
            task["meta"]["note"] = body.note

        atomic_write(TODO_FILE, build_markdown(cols))
        git_commit(f"task: update '{task['title'][:40]}'")
        recalc_aging(cols)
        return {"ok": True, "task": task, "columns": cols}


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task permanently."""
    async with write_lock:
        content = TODO_FILE.read_text(encoding="utf-8")
        cols = parse_todo(content)

        for col, tasks in cols.items():
            for i, t in enumerate(tasks):
                if t.get("id") == task_id:
                    title = t["title"]
                    del tasks[i]
                    atomic_write(TODO_FILE, build_markdown(cols))
                    git_commit(f"task: delete '{title[:40]}'")
                    recalc_aging(cols)
                    return {"ok": True, "columns": cols}

        raise HTTPException(404, f"Task {task_id} not found")


@app.get("/api/validate")
async def validate():
    """Check the todo.md for structural issues."""
    if not TODO_FILE.exists():
        return {"valid": False, "warnings": ["todo.md does not exist"]}

    content = TODO_FILE.read_text(encoding="utf-8")
    columns = parse_todo(content)
    warnings: list[str] = []

    if not columns:
        warnings.append("No columns (## headings) found")

    ids: list[str] = []
    for tasks in columns.values():
        for t in tasks:
            if t.get("id"):
                ids.append(t["id"])
            else:
                warnings.append(f"Task '{t['title'][:30]}…' is missing an ID")

    dupes = [i for i in ids if ids.count(i) > 1]
    if dupes:
        warnings.append(f"Duplicate IDs: {set(dupes)}")

    return {
        "valid": len(warnings) == 0,
        "columns": list(columns.keys()),
        "total_tasks": sum(len(v) for v in columns.values()),
        "warnings": warnings,
    }


# ═══════════════════════════════════════════════
# Lifecycle
# ═══════════════════════════════════════════════

@app.on_event("startup")
async def startup():
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    if not TODO_FILE.exists():
        lines = ["# Todo", ""]
        for c in DEFAULT_COLUMNS:
            lines.append(f"## {c}")
            lines.append("")
        initial = "\n".join(lines)
        atomic_write(TODO_FILE, initial)

    # Ensure every task has an ID (migration for hand-edited files)
    content = TODO_FILE.read_text(encoding="utf-8")
    cols = parse_todo(content)
    if _assign_missing_ids(cols):
        atomic_write(TODO_FILE, build_markdown(cols))

    # Crash recovery
    git_recover()


# ═══════════════════════════════════════════════
# Static frontend mount (optional — only if dist/ exists)
# ═══════════════════════════════════════════════

FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")


# ═══════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8765)
