"""Markdown for the record wiki: escaping data text, frontmatter that reads back as JSON, and the block the builder owns.

A page is frontmatter, the H1 and nav rows (which `wiki update` maintains), `***`, then the generated block between
BEGIN and END. The builder owns its frontmatter keys and the block; `splice` keeps everything else of a page already
on disk line for line (so `wiki update`'s `name`, `sources` and timestamps stand as it wrote them), and `outside_text`
lists what someone wrote there, so the drift check can report it.
"""
from __future__ import annotations

import json
import re

BEGIN = "<!-- BEGIN kaphtor:record -->"
END = "<!-- END kaphtor:record -->"
NAV = re.compile(r"^\[\[[^\]]+\]\](?:\s*·\s*\[\[[^\]]+\]\])*$")


def escape(text) -> str:
    """Data text as Markdown prose or a table cell: `\\`, `*`, `[`, `]`, `` ` `` and `|` escaped, `<` and `>` as
    entities, newlines as spaces. A doubled bracket (Leiden `[[7]]`) becomes entities, since `\\[\\[` is what
    `wiki lint` reads as a wikilink damaged by a formatter."""
    text = str(text).replace("\\", "\\\\").replace("[[", "&#91;&#91;").replace("]]", "&#93;&#93;")
    for ch in "*[]`":
        text = text.replace(ch, "\\" + ch)
    text = text.replace("<", "&lt;").replace(">", "&gt;").replace("|", "\\|")
    return text.replace("\r\n", " ").replace("\n", " ")


def link(path: str, label: str) -> str:
    """A wikilink. Brackets in the (escaped) label become entities, since a `]` would end the link."""
    label = label.replace("\\[", "&#91;").replace("\\]", "&#93;").replace("[", "&#91;").replace("]", "&#93;")
    return f"[[{path}|{label}]]"


WIKILINK_BAR = re.compile(r"(\[\[[^\]|]+)\|([^\]]*\]\])")


def table(head: list[str], rows: list[list[str]]) -> list[str]:
    """A table of cells already escaped; the `|` of a wikilink in a cell is escaped too, or it would end the cell."""
    cells = [[WIKILINK_BAR.sub(r"\1\\|\2", cell) for cell in row] for row in rows]
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(r) + " |" for r in cells]


def _field(key: str, value) -> str:
    return f"{key}: {json.dumps(value, ensure_ascii=False)}"


def frontmatter(fields: dict) -> str:
    """YAML frontmatter whose every value is a JSON scalar or list, so `json.loads` reads each one back."""
    return "\n".join(["---", *(_field(k, v) for k, v in fields.items()), "---"])


def _split(text: str) -> tuple[list[str], list[str]]:
    """(frontmatter lines, the rest), without the `---` fences."""
    lines = text.split("\n")
    if not lines or lines[0] != "---":
        return [], lines
    for i in range(1, len(lines)):
        if lines[i] == "---":
            return lines[1:i], lines[i + 1:]
    raise ValueError("frontmatter has no closing ---")


def parse_frontmatter(text: str) -> dict:
    """The frontmatter of a page. A value that is not JSON (written by another tool) is kept as its text."""
    fields = {}
    for line in _split(text)[0]:
        key, _, value = line.partition(":")
        value = value.strip()
        try:
            fields[key.strip()] = json.loads(value)
        except json.JSONDecodeError:
            fields[key.strip()] = value
    return fields


def page(fields: dict, title: str, nav: list[str], body: list[str]) -> str:
    """A fresh page."""
    return "\n".join([frontmatter(fields), "", f"# {title}", "", *nav, "", "***", "", BEGIN, *body, END, ""])


def _block(rest: list[str]) -> tuple[int, int]:
    try:
        start = rest.index(BEGIN)
        end = rest.index(END, start)
    except ValueError:
        raise ValueError("the page has no kaphtor:record block") from None
    return start, end


def is_generated(text: str) -> bool:
    try:
        _block(_split(text)[1])
        return True
    except ValueError:
        return False


def _merge_frontmatter(old_lines: list[str], new_fields: dict, owned: frozenset) -> list[str]:
    """The frontmatter on disk with the builder's keys rewritten on their own lines. A key it owns but no longer
    writes is dropped, with any continuation lines; a key new to the page goes after the last key it owns. Every
    other line keeps its text and place, so another tool's quoting, order and block lists survive."""
    lines: list[str] = []
    written: set[str] = set()
    after = None   # index after the last owned line written
    dropping = False
    for line in old_lines:
        if line[:1] in (" ", "\t", "-"):  # a continuation of the key above
            if not dropping:
                lines.append(line)
            continue
        key = line.partition(":")[0].strip()
        dropping = key in owned
        if not dropping:
            lines.append(line)
        elif key in new_fields and key not in written:
            lines.append(_field(key, new_fields[key]))
            written.add(key)
            after = len(lines)
    missing = [_field(k, v) for k, v in new_fields.items() if k not in written]
    at = len(lines) if after is None else after
    return lines[:at] + missing + lines[at:]


def set_frontmatter(text: str, fields: dict) -> str:
    """`text` with `fields` written into its frontmatter, each on its own line; every other line is kept."""
    old_lines, rest = _split(text)
    return "\n".join(["---", *_merge_frontmatter(old_lines, fields, frozenset(fields)), "---", *rest])


def splice(existing: str | None, fresh: str, owned: frozenset | None = None) -> str:
    """`fresh` merged into the page already on disk: the fresh frontmatter replaces the keys the builder owns (by
    default the fresh page's keys) on their own lines, other lines are kept verbatim, the block is replaced, and
    every line outside it is kept. ValueError if the page on disk has no block: it is not the builder's to change."""
    if existing is None:
        return fresh
    new_fields = parse_frontmatter(fresh)
    owned = frozenset(new_fields) if owned is None else owned | frozenset(new_fields)
    old_lines, rest = _split(existing)
    start, end = _block(rest)
    _, fresh_rest = _split(fresh)
    fresh_start, fresh_end = _block(fresh_rest)
    lines = rest[:start] + fresh_rest[fresh_start:fresh_end + 1] + rest[end + 1:]
    return "\n".join(["---", *_merge_frontmatter(old_lines, new_fields, owned), "---", *lines])


def outside_text(text: str) -> list[str]:
    """Lines outside the frontmatter and the block that are not the H1, a nav row, `***` or blank."""
    _, rest = _split(text)
    try:
        start, end = _block(rest)
        rest = rest[:start] + rest[end + 1:]
    except ValueError:
        pass
    return [line for line in rest if line.strip() and line.strip() != "***" and not line.startswith("# ")
            and not NAV.match(line.strip())]
