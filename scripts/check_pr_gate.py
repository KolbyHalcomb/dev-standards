#!/usr/bin/env python3
"""
Ticket-first PR gate.

Fails a PR that does not trace to an agent-ready issue: the body must carry a
closing reference (`Closes #N`, `Fixes #N`, ...) and every issue it references
that way must wear the required readiness label. Optionally also enforces a
branch-name pattern. This is the mechanical backstop for the plugin's
`ticket-first` skill -- the skill says why, this gate is what survives a
hurried Friday.

Configuration (environment; workflow inputs arrive as strings):
    $PR_TITLE                PR title (exemption prefixes match against this)
    $PR_BODY                 PR body (closing references are parsed out of this)
    $PR_HEAD_REF             head branch name (only used with $BRANCH_PATTERN)
    $REQUIRE_LINKED_ISSUE    "true"/"false" -- demand a closing reference
    $REQUIRED_LABEL          label every linked issue must carry ("" disables)
    $EXEMPT_TITLE_PREFIXES   title prefixes exempt from the linked-issue rule,
                             whitespace- or comma-separated (e.g. "chore: docs:")
    $BRANCH_PATTERN          full-match regex for the head branch ("" disables)
    $GITHUB_REPOSITORY       owner/repo (for the label lookup and URL references)
    $GITHUB_TOKEN            token for the label lookup
    $GITHUB_API_URL          API base (defaults to https://api.github.com)

The decision logic is pure (find_linked_issues / evaluate) so tests never need
a network; only fetch_issue_labels talks to GitHub. A configuration under which
no check would ever run is refused loudly -- a gate that checks nothing passes
every PR, which is worse than not calling it.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request

import docfiles

# GitHub's closing keywords. The keyword must sit directly before the
# reference, exactly as GitHub itself links them.
CLOSING_KEYWORDS = (
    "close", "closes", "closed",
    "fix", "fixes", "fixed",
    "resolve", "resolves", "resolved",
)


def _link_pattern(repo: str | None) -> re.Pattern[str]:
    keywords = "|".join(CLOSING_KEYWORDS)
    if repo:
        reference = rf"(?:{re.escape(repo)})?#(\d+)|https://github\.com/{re.escape(repo)}/issues/(\d+)"
    else:
        reference = r"#(\d+)"
    return re.compile(rf"\b(?:{keywords})\b:?\s+(?:{reference})", re.IGNORECASE)


def find_linked_issues(body: str, repo: str | None = None) -> list[int]:
    """Issue numbers the PR body closes, in order of appearance, deduplicated.

    Matches `#N`, `owner/repo#N`, and the full issue URL for this repo. A bare
    `#N` with no closing keyword in front is a mention, not a closing
    reference, and is deliberately not counted -- GitHub would not close it.
    """
    seen: list[int] = []
    for match in _link_pattern(repo).finditer(body or ""):
        number = int(next(group for group in match.groups() if group))
        if number not in seen:
            seen.append(number)
    return seen


def is_exempt(title: str, prefixes) -> bool:
    """A title carrying a declared prefix is exempt from the linked-issue rule.

    Prefixes are the repo's stated "no ticket needed" categories, compared
    case-insensitively against the start of the title.
    """
    lowered = (title or "").lstrip().lower()
    return any(lowered.startswith(prefix.lower()) for prefix in prefixes)


def evaluate(
    *,
    title: str,
    body: str,
    branch: str,
    require_linked_issue: bool,
    required_label: str,
    exempt_prefixes,
    branch_pattern: str,
    fetch_labels,
    repo: str | None = None,
) -> tuple[bool, str]:
    """Return (ok, message). fetch_labels(number) -> set of label names."""
    problems: list[str] = []
    notes: list[str] = []

    if branch_pattern:
        if re.fullmatch(branch_pattern, branch or ""):
            notes.append(f"branch {branch!r} matches {branch_pattern!r}")
        else:
            problems.append(
                f"branch {branch!r} does not match the required pattern {branch_pattern!r}"
            )

    linked = find_linked_issues(body, repo)
    exempt = is_exempt(title, exempt_prefixes)

    if require_linked_issue and not linked:
        if exempt:
            notes.append("no linked issue, but the title carries an exempt prefix")
        else:
            problems.append(
                "no closing reference found in the PR body. Add `Closes #N` for the "
                "agent-ready issue this PR implements (ticket-first), or use an exempt "
                "title prefix"
                + (f" ({', '.join(sorted(exempt_prefixes))})" if exempt_prefixes else "")
                + "."
            )

    if required_label and linked:
        for number in linked:
            labels = fetch_labels(number)
            if labels is None:
                problems.append(f"#{number}: not found, or it is a pull request, not an issue")
            elif required_label not in labels:
                shown = ", ".join(sorted(labels)) or "none"
                problems.append(
                    f"#{number} lacks the {required_label!r} label (has: {shown}). "
                    "Take it through triage before building it."
                )
            else:
                notes.append(f"#{number} is {required_label}")

    if problems:
        lines = ["ERROR: the ticket-first gate failed:"]
        lines += [f"  - {problem}" for problem in problems]
        return False, "\n".join(lines)

    detail = "; ".join(notes) if notes else "nothing to check for this PR"
    return True, f"OK: {detail}."


def fetch_issue_labels(number: int, repo: str, token: str, api_url: str):
    """Label names on issue `number`, or None if it is missing or is a PR."""
    request = urllib.request.Request(
        f"{api_url}/repos/{repo}/issues/{number}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    if "pull_request" in data:
        return None
    return {label["name"] for label in data.get("labels", [])}


def main() -> int:
    require_linked_issue = os.environ.get("REQUIRE_LINKED_ISSUE", "true").strip().lower() == "true"
    required_label = os.environ.get("REQUIRED_LABEL", "").strip()
    branch_pattern = os.environ.get("BRANCH_PATTERN", "").strip()
    exempt_prefixes = sorted(docfiles.env_set("EXEMPT_TITLE_PREFIXES"))

    if not require_linked_issue and not required_label and not branch_pattern:
        print(
            "ERROR: every check is disabled (REQUIRE_LINKED_ISSUE=false, no "
            "REQUIRED_LABEL, no BRANCH_PATTERN). This gate would pass every PR, "
            "which is worse than not calling it."
        )
        return 1

    repo = os.environ.get("GITHUB_REPOSITORY", "").strip() or None
    token = os.environ.get("GITHUB_TOKEN", "")
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")

    if required_label and not (repo and token):
        print("ERROR: REQUIRED_LABEL is set but GITHUB_REPOSITORY/GITHUB_TOKEN are not -- "
              "the label check cannot run.")
        return 1

    ok, message = evaluate(
        title=os.environ.get("PR_TITLE", ""),
        body=os.environ.get("PR_BODY", ""),
        branch=os.environ.get("PR_HEAD_REF", ""),
        require_linked_issue=require_linked_issue,
        required_label=required_label,
        exempt_prefixes=exempt_prefixes,
        branch_pattern=branch_pattern,
        fetch_labels=lambda number: fetch_issue_labels(number, repo, token, api_url),
        repo=repo,
    )
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
