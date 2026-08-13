---
name: change-workflow
description: The loop every confirmed real-world change follows before it is committed — surgical edits, a dated CHANGELOG entry, review, then commit. Use when recording a change that has actually happened (a device added, a service moved, a value confirmed), when asked to "update the docs", or when deciding whether something is ready to commit.
---

# Change workflow

Every **confirmed real-world change** follows this loop. No exceptions.

```
1. The operator describes the confirmed change in plain English
2. Make surgical edits to all affected docs
3. Write a dated entry at the TOP of the CHANGELOG listing every file and line touched
4. The operator reviews the summary
5. Commit  -> plain-English description of the real-world change
6. Push
```

Steps 5 and 6 belong to the operator. **Commit or push only when asked.**

## Brainstorming is not committing

Planning sessions produce **no** doc changes. Speculation stays in chat. Docs change only when a
real-world thing has changed.

If you are mid-discussion and reach for the editor, stop and ask: *has this actually happened yet?*
If the answer is "we decided we're going to," the answer to "should I edit" is no.

## Surgical edits only

Change only the specific items affected by the confirmed change. A full section rewrite is never the
right move, even when the section looks messy. Tidying is a separate, named change.

## Update immediately on confirmation

When a command confirms a result, or a value lands (an IP, a port, an ID), write it down before
moving to the next step. **Never hold a confirmed value only in conversation** — the context window
is not storage.

## Never guess a value

If a value is unknown, ask. Do not fill in a plausible-looking placeholder and proceed. **Wrong
values in docs are worse than blank ones** — a blank prompts a question, a wrong value gets trusted
and propagated.

## When docs disagree

Trust the freshest source, in this order:

1. Live system state, queried directly
2. The CHANGELOGs
3. Living reference docs

Flag the conflict and fix the stale doc. Never propagate a value that contradicts a fresher source.

## Report what you touched

After any doc update, list every file touched so it can be reviewed before committing. Cite each at
the granularity that actually locates the change — see the `changelog-entry` skill for the four
forms and when each applies.

## Commit style

Plain English describing the real-world change.

- Good: `Added Zigbee device: IKEA bulb in office`
- Good: `Moved Kasa plugs to IoT VLAN`
- Bad: `update docs` / `changes` / `misc`

**Check `git branch --show-current` before committing.** If on the default branch, create a
tool-prefixed branch first and open a PR from it. The git history is the audit trail — every change
gets a commit, even boring ones.
