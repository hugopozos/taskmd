# TaskMD — SPEC

## Format

Every valid `todo.md` starts with `# Todo` followed by columns (`## Name`) and
tasks (`- [<state>] …`).

## State values

| Token | Meaning |
|-------|---------|
| `[ ]` | Pending (Backlog, Week) |
| `[N]` | In progress (Today) — `N` = days since `started:` |
| `[x]` | Completed (Done) |

## Column structure

```markdown
# Todo

## <ColumnName>
- [<state>] [#tag …] <title> `#<id>`
  created: YYYY-MM-DD        ← required
  started: YYYY-MM-DD        ← set automatically when moving to Today
  completed: YYYY-MM-DD      ← set when completing
  due: YYYY-MM-DD            ← optional deadline (only in Backlog)
  note: <text>               ← optional description
```

## Column meaning

| Column | Purpose |
|--------|---------|
| `Backlog` | Ideas with no priority. Tasks with `due:` float up as date approaches. |
| `Week` | Committed for this week. |
| `Today` | Working on now. `[N]` badge = days since `started:`. Red >7, amber >3. |
| `Done` | Recently done. Older entries are archived automatically. |

Any `## Header` creates a column — the 4 above are defaults, not hardcoded.

## IDs

Every task has a short hex ID at the end of its first line:

```
- [ ] Read book `#a1b`
```

- Generated at creation from `SHA256(title + timestamp)[:3..6]`
- Collision resolution extends up to 6 chars, then falls back to `secrets.token_hex(3)`
- The ID must be the last `` `#…` `` on the line — do not add text after it
- IDs never change, even when the task is edited

## Tags

Format: `#tag` (one per task). Extensible. Common:

- `#dev` — general development
- `#docs` — documentation
- `#ops` — operations / infrastructure
- `#ideas` — loose ideas
- `#meta` — about the task system itself

## Parsing rules

1. A line `## Name` at indent 0 starts a new column.
2. A line `- [<state>]` at indent 0 starts a new task.
3. Any indented line (≥2 spaces) after a task is its metadata.
4. A line starting with `#` inside a task (indent ≥2) is literal text, NOT a heading.
5. The task ID is extracted with the regex `` `#([0-9a-f]{3,6})`\s*$ `` — last backtick-hash on the line.

## Known limitations

- Do NOT add text after the `` `#id` `` token on the task line.
- Manual edits to `todo.md` that break the format can be repaired with `GET /api/validate`.
