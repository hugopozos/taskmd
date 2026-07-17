# Changelog

## [0.2.0] — 2026-07-16

### Changed

- **Modular architecture**: monolithic `server.py` split into 3 layers
  (API, domain, infrastructure) with clear responsibilities.
- Domain layer uses `dataclasses` instead of raw `dicts` for strict typing.
- `atomic_write` now uses `tmp + os.replace` with Docker fallback.
- `Dockerfile` and `docker-compose.yml` mount `server/` as a volume.

### Added

- **Tests**: 50 unit tests + integration test suite (pytest).
- **Dev config**: `pyproject.toml` with ruff and pytest settings.
- `GitService` class instead of loose helper functions.
### Removed

- Unused `aiofiles` dependency.
- Local cache dirs (`.mypy_cache/`, `.ruff_cache/`) from repo tracking.

## [0.1.0] — 2026-07-15

### Added

- Markdown-native kanban board with 4 temporal columns (Backlog → Week → Today → Done)
- Aging counter `[N]` shows days a task has been in progress
- REST API: create, move, edit, delete tasks
- React frontend with dark theme, column layout, and task management UI
- Task IDs (`#abc`) — stable, short hex hashes with collision resolution
- Docker support (multi-stage build + docker-compose)
- Git auto-commit on every task change
- Crash recovery on server restart
- Dynamic columns — any `## Header` in todo.md becomes a column
- Hermione Agent integration guide (HERMES.md)

