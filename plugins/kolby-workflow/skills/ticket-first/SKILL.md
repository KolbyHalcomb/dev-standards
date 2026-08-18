---
name: ticket-first
description: No implementation starts without an agent-ready issue, and every PR names the issue it closes. Use when starting implementation work, opening a PR, deciding whether a request is ready to build, or when asked to "just quickly" build something with no ticket behind it.
---

# Ticket first

Implementation starts from an **agent-ready issue**, not from a chat message. The issue is where
scope, the done-condition, and blocking edges live; a PR that traces to no issue is work nobody
can review against anything.

## What agent-ready means

An issue is agent-ready when all three hold:

1. **A done-when stated as a binary gate** — objective confirmation in the sense of
   `planning-conventions`: "this command returns this value", "this endpoint responds 403 for
   role X". Not "improve", not "seems to work".
2. **Scope is closed** — the issue says what is *out* as well as what is in, so the implementer
   knows where to stop.
3. **Blocking edges are declared** — the issues that must land first are linked, or the issue says
   it has none.

On trackers using the triage vocabulary, agent-ready is marked with the `ready-for-agent` label.
Work only issues that carry it (or its repo-configured equivalent); an unlabeled issue goes
through triage first, it does not get built on the side.

## Every PR names its issue

The PR body carries a closing reference — `Closes #N` / `Fixes #N` — to the issue it implements.
One PR may close several issues; zero is not an option for feature or fix work.

Exemptions exist for work that genuinely has no ticket (dependency bumps, typo fixes, CI
plumbing). The repo declares them as title prefixes in its `workflow-ci` configuration — e.g.
`chore:` or `docs:` — rather than each PR arguing its own case.

## The mechanical backstop

The reusable `workflow-ci.yml` in dev-standards enforces this on PRs: it fails when the body has
no closing reference (unless the title carries an exempt prefix) and when a linked issue lacks the
required label. This skill is why the gate exists; the gate is what makes the skill survive a
hurried Friday.

## No ticket? Make one first

When asked to build something that has no issue, the move is not to refuse and not to silently
build — it is to write the issue (or run the tracker's ticket flow), get it agent-ready, then
build. That usually takes two minutes and is the difference between a reviewable PR and an
unanchored diff.
