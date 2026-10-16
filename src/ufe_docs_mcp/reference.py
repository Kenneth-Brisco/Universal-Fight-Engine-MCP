"""Supplementary field reference: serialized UFE names mapped to manual pages.

The official manual names settings by their Inspector labels ("Frame Links").
Agents usually see serialized C# field names instead (``frameLinks`` in a move
``.asset`` file or in engine code). This module maps those names to the label
and the manual page that documents it, lists stored enum values, and carries a
few clarification notes where the code's behavior is narrower or different
from the manual's wording.

All of this is maintained by the UFE3D-MCP project and is never mixed into
official passages. Every response that uses it carries ``NOTICE`` and each
entry's engine version and source file references.
"""
from __future__ import annotations

from functools import lru_cache
import json
from importlib import resources
import re

NOTICE = (
    "field_matches and clarifications are a UFE3D-MCP supplement, not official manual text. "
    "They are derived from the engine source of the UFE version named in each entry; verify "
    "them against the UFE version in your project."
)
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_PAGE_BASE = "https://www.ufe3d.com/ufe2/docs/#/"


@lru_cache(maxsize=1)
def _data() -> dict:
    text = resources.files(__package__).joinpath("data/field_reference.json").read_text(encoding="utf-8")
    data = json.loads(text)
    fields: dict[str, list[dict]] = {}
    for field in data["fields"]:
        fields.setdefault(_key(field["field"]), []).append(field)
    data["_by_key"] = fields
    return data


def _key(name: str) -> str:
    return name.lstrip("_").casefold()


def _identifier_like(token: str) -> bool:
    """Code-shaped names (leading or inner underscore, inner capitals) trigger a field lookup."""
    return token.startswith("_") or any(char.isupper() for char in token[1:]) or "_" in token.strip("_")


def _enum(name: str | None) -> dict | None:
    if not name:
        return None
    entry = _data()["enums"].get(name)
    if entry is None:
        return None
    return {"name": name, "values": entry["values"], "source_ref": entry.get("source_ref")}


def match_fields(query: str) -> list[dict]:
    """Return field entries named in ``query``, at most five."""
    data = _data()
    matches: list[dict] = []
    seen: set[int] = set()
    for token in _IDENTIFIER.findall(query):
        candidates = data["_by_key"].get(_key(token), [])
        if not candidates:
            continue
        # A lowercase multiword name ("framelinks") is still unambiguous.
        # A leading underscore alone does not make "_gravity" multiword, so
        # the plain word "gravity" never triggers a lookup.
        multiword = any(_identifier_like(field["field"].lstrip("_")) for field in candidates)
        if not (_identifier_like(token) or multiword):
            continue
        for field in candidates:
            if id(field) in seen:
                continue
            seen.add(id(field))
            match = {
                "field": field["field"],
                "owner": field.get("owner"),
                "type": field.get("type"),
                "label": field["label"],
                "doc_id": field.get("doc_id"),
                "url": _PAGE_BASE + field["doc_id"].replace(".", ":") if field.get("doc_id") else None,
                "ufe_version": field.get("ufe_version", data["ufe_version"]),
                "source_ref": field.get("source_ref"),
                "query_words": [_key(token)],
            }
            if field.get("label_in_manual") is False:
                match["label_in_manual"] = False
            if field.get("notes"):
                match["notes"] = field["notes"]
            enum = _enum(field.get("enum"))
            if enum:
                match["enum"] = enum
            notes = [note for note in data["clarifications"] if note["field"] == field["field"]]
            if notes:
                match["clarifications"] = notes
            matches.append(match)
            if len(matches) >= 5:
                return matches
    return matches


_BRIEF_KEYS = ("field", "label", "status", "ufe_version", "summary")


def clarifications_for(doc_id: str, passage: str | None = None, *, brief: bool = False,
                       exclude: frozenset[str] = frozenset()) -> list[dict]:
    """Notes for a page, limited to labels present in ``passage`` when given.

    A note matches on its ``anchor`` text when it has one (for a setting the
    manual omits entirely), otherwise on its label. ``brief`` keeps one-sentence summaries for search passages; the full note,
    with code behavior and source references, is in ``ufe_get_doc`` and in a
    field match for that field. ``exclude`` skips fields already reported."""
    folded = passage.casefold() if passage is not None else None
    notes = [
        note for note in _data()["clarifications"]
        if note["doc_id"] == doc_id and note["field"] not in exclude
        and (folded is None or note.get("anchor", note["label"]).casefold() in folded)
    ]
    if brief:
        return [{key: note[key] for key in _BRIEF_KEYS} for note in notes]
    return notes
