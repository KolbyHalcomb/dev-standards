---
name: delegation
description: How to split work across agents — the planner/worker/judge separation, one ticket per fresh context, parallel agents for independent tickets, subagents for sub-parts of one ticket. Use when deciding whether to parallelize, spinning up multiple agents, delegating a ticket, or when one session is trying to plan and implement at once.
---

# Delegation

Multi-agent work fails in two boring ways: one context window trying to hold planning and
implementation at once, and two agents editing the same files at the same time. Both are
prevented by structure, not by care.

## Three roles, never merged

- **Planner** — grills the idea, writes the spec, cuts the tickets. **The planner never
  implements.** The moment it starts editing source files, its context is polluted with
  implementation detail and its remaining plan degrades.
- **Worker** — implements exactly one ticket, starting from a **fresh context** whose input is the
  ticket (and the docs it links), not the planning conversation. One ticket, one branch, one PR.
- **Judge** — decides whether the work advances. The judge is mechanical first (CI: tests, lint,
  the `workflow-ci` PR gate) and human/agent second (`review-before-advance` on the PR). A worker
  never judges its own PR as the sole reviewer.

## Parallelize by the dependency graph, not by enthusiasm

Tickets declare blocking edges (`ticket-first`). Read the graph:

- **Independent tickets** (no path between them, no shared files) → separate agents in parallel,
  each in its own worktree or cloud environment, each on its own branch and PR. Merge in any
  order.
- **Sub-parts of one ticket** (implementation + test scaffolding, migration + docs) → subagents
  inside the one worker session. They share the ticket's branch; the worker integrates.
- **Tickets on a chain** → serial, blockers first. Running a blocked ticket in parallel "to save
  time" produces a PR that must be rebased onto decisions that hadn't been made when it was
  written.

Two tickets that touch the same files are not independent, whatever the graph says. Reassign the
boundary or run them serially.

## Capacity is a budget, not a dare

Every parallel agent is a PR someone must judge. Run only as many workers as the judge lane
(CI plus your own review attention) can drain; a wall of stale green PRs that conflict with each
other is slower than three merged serially.

## The handoff is the ticket

A worker gets everything it needs from the ticket: the done-when gate, the scope boundary, links
to spec and domain docs. If delegating requires pasting planning-chat context into the worker,
the ticket was not agent-ready — fix the ticket, then delegate.
