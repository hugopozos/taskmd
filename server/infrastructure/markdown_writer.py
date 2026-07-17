"""
Markdown writer — serialises a TaskBoard back to Markdown.

Must be the inverse of the parser to guarantee roundtrip fidelity.
"""

from server.domain.models import TaskBoard


def build_markdown(board: TaskBoard) -> str:
    """Serialize a TaskBoard back into the todo.md format.

    Guarantees that parse_todo(build_markdown(board)) == board.
    """
    # Sort columns by insertion order (Python 3.7+ preserves dict order)
    lines: list[str] = []
    lines.append("# Todo")
    lines.append("")

    for name, tasks in board.columns.items():
        lines.append(f"## {name}")
        for t in tasks:
            # Tags
            tags_str = ""
            if t.tags:
                tags_str = " ".join(f"#{tag}" for tag in t.tags) + " "

            # ID
            id_str = f" `#{t.id}`" if t.id else ""

            # Task line
            lines.append(f"- [{t.state}] {tags_str}{t.title}{id_str}")

            # Metadata
            for k, v in t.meta.items():
                if "\n" in v:
                    first, *rest_lines = v.split("\n")
                    lines.append(f"  {k}: {first}")
                    for continuation in rest_lines:
                        lines.append(f"    {continuation}")
                else:
                    lines.append(f"  {k}: {v}")

        lines.append("")

    return "\n".join(lines)
