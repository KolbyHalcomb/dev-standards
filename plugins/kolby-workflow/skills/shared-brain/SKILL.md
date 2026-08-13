---
name: shared-brain
description: How to keep one shared project brain with thin per-tool wrappers so CLAUDE.md, AGENTS.md, and other agent entry files never drift apart. Use when adding a fact to a repo's agent instructions, when asked where something belongs, when setting up agent files in a new repo, or when two entry files have diverged.
---

# One brain, thin wrappers

Multiple coding agents read a repo, and each wants its own entry file — `CLAUDE.md`, `AGENTS.md`,
and others. The obvious move is to keep a full copy of the project's instructions in each. **That
fails**, and it fails quietly: the copies drift a fact at a time, and nobody notices until two agents
act on contradictory information.

The fix: **all shared content lives in exactly one file. Every tool entry file is a thin wrapper
that points at it.**

```
docs/PROJECT.md      <- the brain. Everything shared.
CLAUDE.md            <- thin wrapper: pointer + Claude-specific only
AGENTS.md            <- thin wrapper: pointer + Codex-specific only
```

## What goes where

**The brain** holds anything true regardless of which agent is reading: personas, core principles,
safety rules, the host/access matrix, the file index, domain routing, workflows, and current
priorities.

**A wrapper** holds only what is genuinely tool-specific, and nothing else:

- Which credentials that tool can and cannot read
- Which hosts that tool can reach, and as which user
- That tool's git branch prefix
- That tool's resume prompt, naming the correct entry file
- A pointer to the brain, and an instruction not to duplicate into the wrapper

A wrapper should be short — on the order of 50 lines. If it is growing, content is leaking out of
the brain.

## Tool-specific framing is content, not drift

This is the distinction that matters when splitting an already-duplicated pair.

If one file says *"Claude's job is to hold that structure"* and the other says *"Codex's job is to
hold that structure"*, that is the **same** shared instruction with a substituted name — it belongs
in the brain, phrased once without naming a tool ("the agent's job is...").

But if the two tools genuinely have different access, different permissions, or a different role in
the workflow, that asymmetry is real content and **must survive the split**. Do not flatten it in
the name of deduplication.

Read both files side by side before you merge. Every difference is either an asymmetry to preserve
or a drift to resolve — decide which, one at a time, and never by picking whichever file you opened
first.

## Enforce it mechanically

A convention that relies on remembering will drift back. Add a CI check that fails if any
shared-content heading reappears in a wrapper:

```python
FORBIDDEN_WRAPPER_HEADINGS = {
    "Personas", "Core Principles", "Critical Safety Rules",
    "Access Matrix", "File Index", "Domain Routing",
    "Document Update Protocol", "Change Workflow",
    "Planning Conventions", "Git Workflow",
}
```

Fail the build if a wrapper contains any of them as an H2. The check is a few lines and it is the
only reason the split holds.

## Do not bridge files with git symlinks

The tempting shortcut is to symlink one entry file to the other, or to symlink a shared skills
directory into each tool's expected location. On Windows with `core.symlinks=false`, git commits
symlinks as **plain text files containing the target path**. They appear to work on the machine that
created them and are inert everywhere else — a failure that looks like success.

Use a real mechanism instead: a directory junction (`mklink /J`, no admin required), a sync script,
or plugin distribution.

## Adding a fact

1. Ask: is this true for every agent? If yes it goes in the brain — full stop.
2. If it is tool-specific, put it in that tool's wrapper and **nowhere else**.
3. If you catch yourself typing the same sentence into two files, you are creating the drift this
   whole structure exists to prevent. Stop and move it to the brain.
