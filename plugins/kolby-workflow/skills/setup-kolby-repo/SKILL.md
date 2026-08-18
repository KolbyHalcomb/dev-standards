---
name: setup-kolby-repo
description: Scaffold a repo onto the kolby-workflow conventions — plugin pin, CI gates, triage labels, issue and PR templates, thin agent-file wrappers. Use when setting up a new repository, when asked to "wire up the workflow" or "apply dev-standards" to a repo, or when auditing an existing repo against the conventions.
---

# Set up a repo on the kolby-workflow conventions

Bring one repository onto the shared workflow: plugin enabled for every client, the CI gates
called, the triage labels present, the templates in place, agent entry files split per
`shared-brain`. Prompt-driven: explore, present what you found, confirm, then write.

The canonical sources live in [KolbyHalcomb/dev-standards](https://github.com/KolbyHalcomb/dev-standards).
Get a local copy first:

```bash
git clone --depth 1 https://github.com/KolbyHalcomb/dev-standards /tmp/dev-standards
```

Pin question, asked once up front: which ref of dev-standards should this repo consume? A tag or
SHA is the durable answer; `main` is acceptable for lab repos. Use the same answer everywhere a
ref appears below.

## 1. Explore

Read the target repo before proposing anything:

- `.claude/settings.json` — marketplace pin already present?
- `.cursor/rules/` — existing rules? Full copies of shared content are a `shared-brain` violation
  to flag, not overwrite.
- `.github/workflows/` — CI already calling `docs-ci.yml` / `workflow-ci.yml`?
- `.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md` — existing templates?
- `CLAUDE.md` / `AGENTS.md` — which entry files exist; is there already a brain file?
- Is it a docs repo (living reference + CHANGELOG) or an app repo? This decides whether `docs-ci`
  gets the changelog gate.

Present the findings and the plan below adjusted to them. **Never overwrite an existing file
without showing the diff and getting a yes.**

## 2. Enable the plugin for all three clients

- **Claude Code** — merge into `.claude/settings.json` (template:
  `/tmp/dev-standards/templates/claude-settings.json`): the `kolby` marketplace pin and
  `kolby-workflow@kolby` enabled.
- **Cursor** — copy `/tmp/dev-standards/templates/cursor-rules/kolby-workflow.mdc` to
  `.cursor/rules/`. It is a thin pointer at the plugin's skills, not a copy of them.
- **Codex** — user-scope junctions cover every repo; nothing per-repo. Point the user at
  `scripts/sync-codex-skills.ps1` in dev-standards if they haven't run it.

## 3. Call the CI gates

Add (or extend) a workflow that calls the reusable workflows, pinned to the chosen ref:

```yaml
name: Standards
on:
  pull_request:
    branches: [main]
jobs:
  workflow:
    uses: KolbyHalcomb/dev-standards/.github/workflows/workflow-ci.yml@<ref>
    with:
      standards-ref: <ref>
      exempt-title-prefixes: "chore: docs:"
  docs:
    uses: KolbyHalcomb/dev-standards/.github/workflows/docs-ci.yml@<ref>
    with:
      standards-ref: <ref>
```

Docs repos add `tracked-docs` / `changelog-files` to the docs job; app repos usually skip the
changelog gate. Confirm the exempt prefixes with the user — they are the repo's declared
"no ticket needed" categories (`ticket-first`).

## 4. Sync the triage labels

Add a manually-triggerable caller for the label sync (labels change rarely; a cron is noise):

```yaml
name: Sync labels
on: workflow_dispatch
permissions:
  issues: write
jobs:
  labels:
    uses: KolbyHalcomb/dev-standards/.github/workflows/sync-labels.yml@<ref>
    with:
      standards-ref: <ref>
```

Run it once after merging so `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`,
and `wontfix` exist before the first triage pass.

## 5. Copy the templates

From `/tmp/dev-standards/templates/.github/` into the repo's `.github/`:

- `ISSUE_TEMPLATE/ticket.yml` — auto-applies `ready-for-agent`; its required fields are what make
  that label honest.
- `ISSUE_TEMPLATE/bug-report.yml` — auto-applies `needs-triage`.
- `pull_request_template.md` — the closing reference and the review-before-advance checklist.

Adjust wording to the repo where it helps; keep the fields — the CI gate and the triage flow
depend on them.

## 6. Agent entry files

Apply `shared-brain`: one brain file, thin wrappers. If the repo has repo-specific workflow facts
(who reviews, status vocabulary, deploy targets), they go in the brain, and the wrappers point at
it. If the Matt Pocock engineering skills are installed, run `setup-matt-pocock-skills` now — it
scaffolds `docs/agents/` (issue tracker, triage labels, domain docs) that `triage`, `to-tickets`,
and `implement` read.

## 7. What cannot live in the repo

Branch protection is GitHub settings, not files. Tell the user to require these checks on `main`
once the first PR has run them: the `workflow-ci` PR gate, plus the repo's own test/lint jobs.
Without that, every gate above is advisory.
