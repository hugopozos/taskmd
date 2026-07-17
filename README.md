# TaskMD

> Markdown-native kanban with temporal columns and an aging counter.
> Built for AI agents and humans to share a single task file.

## Why

Most todo apps are SaaS, bloated, or designed for either machines or humans.
TaskMD is different:

- **Your tasks live in a Markdown file.** One file. Editable by you, your editor,
  and your AI agent. No database, no API, no vendor lock.
- **Time-based columns, not status-based.** Tasks flow through
  `Backlog` → `Week` → `Today` → `Done`.
  Tasks in `Today` show an **aging badge** (`[3]` = 3 days in progress) so
  you can see what's stuck at a glance.
- **AI-native.** Your agent reads and writes the same file you see in the
  browser. No adapters, no plugins, no SDK.

## Quick start

```bash
git clone https://github.com/<your-username>/taskmd
cd taskmd

# Docker (recommended)
docker compose up -d

# Or run directly
pip install -r requirements.txt
uvicorn server.main:app --host 127.0.0.1 --port 8765 --reload
```

Open **http://localhost:8765** in your browser. Edit `todo.md` with any text editor
or let your AI agent manage it through the REST API.

## Format

See [SPEC.md](SPEC.md) for the complete markdown format specification.

## Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Storage | Markdown (`todo.md`) | One file, git-diffable, AI-readable |
| Backend | Python 3.14 (FastAPI) | Reads/writes markdown, 5 REST endpoints |
| Frontend | React 19 + Vite + Tailwind | Modern, fast, dark-themed |
| Container | Docker + Compose | Portable, reproducible |

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/todo` | List all tasks grouped by column |
| `POST` | `/api/tasks` | Create a task |
| `PATCH` | `/api/tasks/{id}` | Move or edit a task |
| `DELETE` | `/api/tasks/{id}` | Delete a task |
| `GET` | `/api/validate` | Check todo.md for structural issues |

## Consuming from an AI agent

```bash
# Read current state
curl http://localhost:8765/api/todo

# Create a task
curl -X POST http://localhost:8765/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Set up CI/CD","column":"Week","tags":"#devops"}'

# Move to active
curl -X PATCH http://localhost:8765/api/tasks/{id} \
  -H "Content-Type: application/json" \
  -d '{"column":"Today"}'

# Complete
curl -X PATCH http://localhost:8765/api/tasks/{id} \
  -H "Content-Type: application/json" \
  -d '{"column":"Done"}'
```

See [HERMES.md](HERMES.md) for a Hermes Agent integration guide.

## Architecture

```
todo.md ──┬── Backend API ── Frontend (React)
           │   (FastAPI)
           └── Hermes Agent ── read_file / API calls
                    (your AI)
archive/
  └── 2026-07.md     ← completed tasks, sharded by month
```

- The backend serialises writes with `asyncio.Lock`.
- Every write triggers a `git commit` (safety net).
- On restart, uncommitted changes are automatically recovered.
- Task IDs are short hex hashes (`#a1b`) with collision resolution.

## Project structure

```
taskmd/
├── todo.md                    ← the one file that matters
├── server.py                  ← Entry point (delegates to server/)
├── server/                    ← Python backend package
│   ├── main.py                ← FastAPI app factory, lifecycle
│   ├── api/
│   │   └── router.py          ← REST endpoints (thin, delegates to domain)
│   ├── domain/
│   │   ├── models.py          ← Domain data classes (Task, TaskBoard)
│   │   ├── schemas.py         ← Pydantic request/response schemas
│   │   └── task_service.py    ← Business logic (aging, IDs, validation)
│   └── infrastructure/
│       ├── file_repository.py ← Atomic file I/O (todo.md persistence)
│       ├── git_service.py     ← Git auto-commit & crash recovery
│       ├── markdown_parser.py ← todo.md → TaskBoard
│       └── markdown_writer.py ← TaskBoard → todo.md
├── tests/
│   ├── test_domain_models.py
│   ├── test_markdown_roundtrip.py
│   ├── test_id_generation.py
│   └── test_task_service.py
├── frontend/
│   ├── src/App.tsx            ← 4-column board + aging badge
│   └── src/types.ts           ← TypeScript interfaces
├── archive/                   ← historical tasks (auto-archived)
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Security

By default `docker-compose.yml` binds the server to **127.0.0.1:8765** only.
It is not reachable from the local network or the internet.

To access it from another device on your Tailnet or LAN, set the
`TASKMD_BIND` environment variable to `0.0.0.0` before starting the container:

```bash
TASKMD_BIND=0.0.0.0 docker compose up -d
```

Then open `http://<tailscale-ip>:8765` from the remote device.
Do **not** commit `TASKMD_BIND=0.0.0.0` to a public repository.

For a production public deployment, put TaskMD behind a reverse proxy
with HTTPS and authentication instead of exposing `0.0.0.0`.

## License

MIT
