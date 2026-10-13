"""Generate client plugin packages that launch this installation.

Cursor and Antigravity plugins cannot use the repository's root manifests
directly: Antigravity's plugin.json allows only name and description, and
neither client documents a plugin-root variable for the root mcp.json layout.
The exported package instead points at this checkout's interpreter with
absolute paths, exactly like `client-config`.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil

from . import __version__
from .cli import SERVER_KEY, local_launch

PLUGIN_NAME = "ufe3d-mcp"
DESCRIPTION = "UFE reference context for building and debugging game features with a coding agent."
REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _copy_skills(out: Path) -> list[str]:
    if not (SKILLS_DIR / "ufe-docs" / "SKILL.md").is_file():
        return []
    shutil.copytree(SKILLS_DIR, out / "skills")
    return sorted(str(p.relative_to(out)) for p in (out / "skills").rglob("*") if p.is_file())


def export_plugin(client: str, out: Path, cache_dir: Path, *, url: str | None = None) -> list[str]:
    if out.exists():
        raise FileExistsError(f"{out} already exists; choose a new directory.")
    command, args = local_launch(cache_dir)
    out.mkdir(parents=True)
    written: list[str] = []
    if client == "antigravity":
        _write_json(out / "plugin.json", {"name": PLUGIN_NAME, "description": DESCRIPTION})
        entry = {"serverUrl": url} if url else {"command": command, "args": args}
        _write_json(out / "mcp_config.json", {"mcpServers": {SERVER_KEY: entry}})
        written += ["plugin.json", "mcp_config.json"]
    elif client == "cursor":
        _write_json(out / ".cursor-plugin" / "plugin.json", {
            "name": PLUGIN_NAME,
            "description": DESCRIPTION,
            "version": __version__,
            "author": {"name": "Kenneth Brisco"},
            "license": "MIT",
        })
        entry = {"url": url} if url else {"type": "stdio", "command": command, "args": args}
        _write_json(out / "mcp.json", {"mcpServers": {SERVER_KEY: entry}})
        written += [".cursor-plugin/plugin.json", "mcp.json"]
    else:
        raise ValueError(f"Unsupported plugin client: {client}")
    return written + _copy_skills(out)
