# Changelog

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
