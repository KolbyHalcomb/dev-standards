#!/usr/bin/env python3
"""
Converge a repo's issue labels on the shared triage vocabulary.

The triage flow (needs-triage -> needs-info / ready-for-agent / ready-for-human
/ wontfix) only works when every repo spells the labels the same way, and the
`workflow-ci` PR gate refuses issues that lack `ready-for-agent` -- so the
labels have to exist before either is any use. This script creates missing
labels and repairs drifted color/description. It **never deletes**: a repo's
extra labels are its own business.

Usage:
    sync_labels.py [--dry-run]

Configuration (environment):
    $LABELS_FILE         JSON list of {name, color, description}
    $GITHUB_REPOSITORY   owner/repo to sync
    $GITHUB_TOKEN        token with issues:write
    $GITHUB_API_URL      API base (defaults to https://api.github.com)

The decision logic is pure (plan()) so tests never need a network; only the
fetch/apply functions talk to GitHub. An empty labels file is refused loudly --
a sync that syncs nothing passes every run and protects nothing.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request


def _normalize_color(color: str) -> str:
    return (color or "").lstrip("#").lower()


def plan(existing, desired) -> tuple[list[dict], list[dict]]:
    """Return (to_create, to_update). Labels present and matching need nothing.

    `existing` and `desired` are lists of {name, color, description}. Matching
    is by exact name; color compares case-insensitively and ignores a leading
    '#'. Extra existing labels are deliberately left untouched.
    """
    by_name = {label["name"]: label for label in existing}
    to_create: list[dict] = []
    to_update: list[dict] = []

    for label in desired:
        current = by_name.get(label["name"])
        if current is None:
            to_create.append(label)
        elif (_normalize_color(current.get("color", "")) != _normalize_color(label.get("color", ""))
              or (current.get("description") or "") != (label.get("description") or "")):
            to_update.append(label)

    return to_create, to_update


def _request(method: str, url: str, token: str, payload: dict | None = None):
    request = urllib.request.Request(
        url,
        method=method,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def fetch_existing(repo: str, token: str, api_url: str) -> list[dict]:
    labels: list[dict] = []
    page = 1
    while True:
        batch = _request("GET", f"{api_url}/repos/{repo}/labels?per_page=100&page={page}", token)
        labels.extend(batch)
        if len(batch) < 100:
            return labels
        page += 1


def apply(repo: str, token: str, api_url: str, to_create, to_update) -> None:
    for label in to_create:
        _request("POST", f"{api_url}/repos/{repo}/labels", token, {
            "name": label["name"],
            "color": _normalize_color(label.get("color", "ededed")),
            "description": label.get("description", ""),
        })
    for label in to_update:
        encoded = urllib.parse.quote(label["name"], safe="")
        _request("PATCH", f"{api_url}/repos/{repo}/labels/{encoded}", token, {
            "new_name": label["name"],
            "color": _normalize_color(label.get("color", "ededed")),
            "description": label.get("description", ""),
        })


def main(argv) -> int:
    dry_run = "--dry-run" in argv

    labels_file = os.environ.get("LABELS_FILE", "").strip()
    if not labels_file:
        print("ERROR: $LABELS_FILE is not set.")
        return 1
    with open(labels_file, encoding="utf-8") as handle:
        desired = json.load(handle)
    if not desired:
        print(f"ERROR: {labels_file} defines zero labels -- this sync would do "
              "nothing on every run, which is worse than not calling it.")
        return 1

    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "")
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    if not (repo and token):
        print("ERROR: $GITHUB_REPOSITORY and $GITHUB_TOKEN are required.")
        return 1

    to_create, to_update = plan(fetch_existing(repo, token, api_url), desired)

    for label in to_create:
        print(f"create: {label['name']}")
    for label in to_update:
        print(f"update: {label['name']} (color/description drifted)")
    if not to_create and not to_update:
        print(f"OK: all {len(desired)} label(s) already match.")
        return 0

    if dry_run:
        print("Dry run -- nothing applied.")
        return 0

    apply(repo, token, api_url, to_create, to_update)
    print(f"OK: created {len(to_create)}, updated {len(to_update)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
