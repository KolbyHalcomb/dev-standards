---
name: review-before-advance
description: Read every comment and review on an issue or PR before closing, merging, or deploying it — then implement each item or counter it in writing. Use when about to close an issue, merge a PR, mark work done, deploy, or start the next slice while the current one has open feedback.
---

# Review before advancing

Do not close an issue, merge a PR, or deploy until **every comment and review** on that issue/PR
has been read in this session. Not the latest comment — all of them. Feedback that was never read
is feedback that was silently overruled, and nobody decided to overrule it.

## The loop

1. Fetch the issue/PR **body and all comments and reviews**, not just the most recent page.
2. Extract action items, required behavior, evidence lists, and any status vocabulary the
   repo uses.
3. For each item, do exactly one of:
   - **Implement it**, or
   - **Counter it in writing** on the issue/PR, with the reason. Never silently skip.
4. Post the evidence or the counter on the issue/PR **before** advancing.
5. Only then close, merge, or deploy.

## Automation PASS is not review

A green CI run, a bot approval, or an agent's own "done" summary is confirmation that the *checks*
passed, not that the *feedback* was addressed. Steps 1–4 still run.

## What the repo wrapper adds

This skill states the generic rule. Each consumer repo's own agent instructions (per
`shared-brain`, the thin wrapper or the brain file it points at) name the specifics:

- **Whose** comments are binding review (named maintainers, a founder, a client contact).
- **Which status vocabulary** gates closing (e.g. an issue may only be GitHub-closed when its
  recorded status allows it).
- **Which artifacts** count as evidence.

If the repo names people or statuses, those are load-bearing — follow the wrapper. If it names
none, every human comment is binding until implemented or countered.

## Do not

- Close, merge, or map a change from a commit SHA alone.
- Treat "done when: PR is open" as authorization to merge.
- Start the next slice while the current slice has open review items neither implemented nor
  countered.
