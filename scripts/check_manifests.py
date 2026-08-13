#!/usr/bin/env python3
"""Assert the Agent Plugins and Claude Code manifests agree.

Each plugin carries two manifests so one directory can serve Claude Code, Cursor, and Codex:

    plugins/<name>/plugin.json                 Agent Plugins 1.0  -> Cursor, Codex
    plugins/<name>/.claude-plugin/plugin.json  Claude Code

That is a deliberate duplication of three fields, and duplication is exactly what this repo exists
to prevent elsewhere. This check closes the seam: bump a version in one manifest and CI fails.

Exits non-zero on a mismatch, on a missing manifest, or on a vacuous run that discovered no plugins
at all -- a check that silently inspects nothing passes every time and protects nothing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Fields that must be identical across both manifests. Claude-only fields (author, homepage,
# license, keywords) and Agent-Plugins-only fields ($schema) are deliberately not compared.
SHARED_FIELDS = ("name", "version", "description")

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: missing manifest: {path.relative_to(REPO_ROOT)}")
        raise SystemExit(1)
    except json.JSONDecodeError as exc:
        print(f"ERROR: {path.relative_to(REPO_ROOT)} is not valid JSON: {exc}")
        raise SystemExit(1)


def check_plugin(plugin_dir: Path) -> list[str]:
    """Return a list of human-readable failures for one plugin directory."""
    agent = load(plugin_dir / "plugin.json")
    claude = load(plugin_dir / ".claude-plugin" / "plugin.json")

    failures = []
    for field in SHARED_FIELDS:
        agent_value = agent.get(field)
        claude_value = claude.get(field)

        if agent_value is None or claude_value is None:
            missing = "plugin.json" if agent_value is None else ".claude-plugin/plugin.json"
            failures.append(f"{plugin_dir.name}: {field!r} is absent from {missing}")
        elif agent_value != claude_value:
            failures.append(
                f"{plugin_dir.name}: {field!r} disagrees\n"
                f"    plugin.json                -> {agent_value!r}\n"
                f"    .claude-plugin/plugin.json -> {claude_value!r}"
            )

    # The directory name is the skill namespace users type (/name:skill). A manifest name that
    # disagrees with it silently changes every invocation.
    if agent.get("name") != plugin_dir.name:
        failures.append(
            f"{plugin_dir.name}: manifest name {agent.get('name')!r} does not match its directory"
        )

    return failures


def main() -> int:
    if not PLUGINS_DIR.is_dir():
        print(f"ERROR: no plugins directory at {PLUGINS_DIR.relative_to(REPO_ROOT)}")
        return 1

    plugin_dirs = sorted(p for p in PLUGINS_DIR.iterdir() if p.is_dir())
    if not plugin_dirs:
        print("ERROR: discovered zero plugins -- this check inspected nothing.")
        return 1

    failures = []
    for plugin_dir in plugin_dirs:
        failures.extend(check_plugin(plugin_dir))

    if failures:
        print(f"Manifest mismatch in {len(plugin_dirs)} plugin(s) checked:\n")
        for failure in failures:
            print(f"  - {failure}")
        print("\nBump the shared fields in BOTH manifests together.")
        return 1

    print(f"OK: {len(plugin_dirs)} plugin(s) checked, manifests agree on {', '.join(SHARED_FIELDS)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
