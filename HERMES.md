# Hermes Agent Integration

TaskMD is designed to be consumed by AI agents through a small REST API.
This guide is for users of [Hermes Agent](https://hermes-agent.nousresearch.com/docs)
or any other agent that can call HTTP endpoints.

## Default endpoint

When running locally or via Docker:

```
http://127.0.0.1:8765
```

If you expose the service through Tailscale, replace `127.0.0.1` with the
Tailscale IP of the host.

## Core operations

### Read the current board

```bash
curl http://127.0.0.1:8765/api/todo
```

Response:

```json
{
  "columns": {
    "Backlog": [...],
    "Week": [...],
    "Today": [...],
    "Done": [...]
  }
}
```

### Create a task

```bash
curl -X POST http://127.0.0.1:8765/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Set up backups","column":"Week","tags":"#server"}'
```

Fields:

- `title` (required): task text
- `column` (optional): target column name, default `Backlog`
- `tags` (optional): space-separated tags like `#server #dev`
- `note` (optional): free-form note stored as metadata

### Move a task

```bash
curl -X PATCH http://127.0.0.1:8765/api/tasks/{id} \
  -H "Content-Type: application/json" \
  -d '{"column":"Today"}'
```

When moving to `Today`, the backend sets `state` to `1` and records `started:`
(today's date). The aging badge updates daily.

When moving to `Done`, the backend sets `state` to `x` and records
`completed:`.

### Edit a task

```bash
curl -X PATCH http://127.0.0.1:8765/api/tasks/{id} \
  -H "Content-Type: application/json" \
  -d '{"title":"New title","tags":"#server #urgent"}'
```

### Delete a task

```bash
curl -X DELETE http://127.0.0.1:8765/api/tasks/{id}
```

### Validate the markdown file

```bash
curl http://127.0.0.1:8765/api/validate
```

Returns structural warnings (missing IDs, duplicate IDs, missing columns).

## Fallback read path

If the server is not running, an agent can still read `todo.md` directly
because the format is plain Markdown:

```markdown
# Todo

## Today
- [1] Set up backups `#a1b`
  started: 2026-07-15

## Done
- [x] Buy groceries `#c2d`
  completed: 2026-07-14
```

The backend is the only supported writer. Direct edits are possible but
should be followed by a manual `GET /api/validate` to catch formatting issues.

## Recommended workflow

1. Let the user describe what they want to track.
2. `POST /api/tasks` to add it.
3. `PATCH /api/tasks/{id}` to move tasks across columns as status changes.
4. `GET /api/todo` when the user asks for a status summary.
5. `GET /api/validate` after any manual file edit.

## Notes

- Task IDs are stable. They are written as `` `#abc` `` at the end of the task line.
- Tags use `#tag` syntax and are rendered as badges in the frontend.
- Column names are dynamic: any `## Header` in `todo.md` becomes a column.
