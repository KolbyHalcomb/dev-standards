# dev-standards

Cross-repo conventions for Kolby's repositories, in three layers:

1. **`plugins/kolby-workflow/`** — an agent plugin carrying documentation, change-management, and
   multiagent-workflow discipline as skills. Loads in **Claude Code, Cursor, and Codex** from one
   directory.
2. **`.github/workflows/`** — reusable CI workflows that consumer repos call with `uses:`.
3. **`templates/`** — files consumer repos copy in once: the triage labels, issue forms, the PR
   template, the plugin pin. The plugin's `setup-kolby-repo` skill does the copying.

Nothing here is host-specific. No IPs, no credentials, no estate facts — those stay in each repo's
own brain. What lives here is process that is true regardless of which repo or which agent.

---

## One plugin, three clients

[Agent Plugins 1.0.0](https://agent-plugins.org/) is a vendor-neutral packaging standard whose
technical steering committee includes Cursor, OpenAI, Microsoft, Amazon, and Vercel. Claude Code
keeps its own manifest format. **Both read skills from the same path**, so one directory serves all
three with two thin manifests rather than two copies of the content:

```
plugins/kolby-workflow/
├── plugin.json                 # Agent Plugins 1.0  -> Cursor, Codex
├── .claude-plugin/plugin.json  # Claude Code
└── skills/<name>/SKILL.md      # shared by all three
```

Skill frontmatter is deliberately limited to `name` and `description`. No client-specific keys —
those would break portability, which is the whole point.

### Keeping the manifests honest

Two manifests means two places to bump a version, which is exactly the drift this repo exists to
prevent. `scripts/check_manifests.py` fails CI if they disagree on `name`, `version`, or
`description`.

---

## Install

### Claude Code

```bash
claude plugin marketplace add KolbyHalcomb/dev-standards
```

```bash
claude plugin install kolby-workflow@kolby
```

To enable it automatically for a repo, commit this to that repo's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "kolby": { "source": { "source": "github", "repo": "KolbyHalcomb/dev-standards" } }
  },
  "enabledPlugins": { "kolby-workflow@kolby": true }
}
```

Skills are namespaced: `/kolby-workflow:change-workflow`.

### Cursor

Import `KolbyHalcomb/dev-standards` as a workspace or team marketplace under **Customize**. Cursor
detects the Agent Plugins format automatically. Auto-refresh requires the Cursor GitHub App and
reindexes at most once every 10 minutes.

### Codex

Codex reads skills from `.agents/skills` (walking up from the working directory to the repo root)
and from `$HOME/.agents/skills` at user scope. **Wiring user scope once covers every repo:**

```bash
pwsh -File scripts/sync-codex-skills.ps1
```

Codex treats each *subdirectory* of `~/.agents/skills` as one skill containing `SKILL.md`, while the
plugin stores them at `skills/<skill>/SKILL.md`. The two layouts differ by one level, so a single
junction of the whole `skills/` folder puts `SKILL.md` one level too deep and Codex finds **no
skills at all** — silently. The script creates one junction per skill instead, and re-running it
picks up added or removed skills.

Directory junctions rather than git symlinks, deliberately: git stores a symlink correctly as mode
`120000`, but a Windows checkout with `core.symlinks=false` materializes it as a small text file
containing the target path — valid in the index, inert in the working tree. Junctions are created
locally, need no administrator rights, and ignore that setting.

Pass `-WhatIf` to see what it would do. It only ever removes reparse points that point into this
plugin, so a real directory or another tool's skill in `~/.agents/skills` is left alone.

---

## Skills

| Skill | Covers |
| --- | --- |
| `change-workflow` | The loop every confirmed change follows before commit. Brainstorming is not committing. |
| `changelog-entry` | Dated-heading format, the four citation granularities, why entries are never edited after the fact. |
| `shared-brain` | One brain, thin per-tool wrappers. How to split an already-duplicated pair without flattening real asymmetries. |
| `planning-conventions` | Spec first, phase it, binary gates, rollback first, default to durable, land plans into living docs. |
| `safety-rule` | Name the artifact, name the consequence, name the condition for breaking it. |
| `ticket-first` | No implementation without an agent-ready issue; every PR names the issue it closes. |
| `review-before-advance` | Read every comment and review before closing, merging, or deploying; implement or counter in writing. |
| `delegation` | Planner/worker/judge separation, one ticket per fresh context, parallelize by the dependency graph. |
| `setup-kolby-repo` | Scaffold a repo onto all of the above: plugin pin, CI gates, labels, templates, agent-file wrappers. |

The last four encode the multiagent workflow; `workflow-ci.yml` (below) is its mechanical
backstop, so the discipline survives even when nobody re-reads the skill.

---

## Reusable CI workflows

### `docs-ci.yml` — docs discipline

Consumer repos call `docs-ci.yml` instead of copying scripts:

```yaml
jobs:
  docs:
    uses: KolbyHalcomb/dev-standards/.github/workflows/docs-ci.yml@<sha>
    with:
      standards-ref: <same sha>
      tracked-docs: |
        devices.md
        network.md
      changelog-files: CHANGELOG.md
```

`uses:` pins the workflow; `standards-ref` pins the scripts it runs. Pass the same SHA to both, or a
workflow and its scripts can come from different commits.

This repo is public, so no Actions access configuration is needed on consumers.

| Job | Behavior |
| --- | --- |
| `lint` | markdownlint-cli2 over `markdownlint-globs`. |
| `links` | Relative links and `#anchor` targets resolve. Fails the build. |
| `tbd` | Inventories `TBD` placeholders. Informational — `continue-on-error`. |
| `changelog` | PR-only. Fails if a `tracked-docs` file changed without a `changelog-files` entry. Skipped entirely when `tracked-docs` is empty. |

Each job is individually disableable (`run-lint`, `run-links`, `run-tbd`) so a code repo can take
only what applies.

### `workflow-ci.yml` — the ticket-first gate

Enforces the `ticket-first` skill on every PR: the body must carry a closing reference
(`Closes #N`), and every issue it closes must wear the readiness label — so nothing gets built
before triage says it is agent-ready.

```yaml
on:
  pull_request:
    branches: [main]

jobs:
  workflow:
    uses: KolbyHalcomb/dev-standards/.github/workflows/workflow-ci.yml@<sha>
    with:
      standards-ref: <same sha>
      exempt-title-prefixes: "chore: docs:"
```

| Input | Behavior |
| --- | --- |
| `require-linked-issue` | Demand a closing reference in the PR body (default `true`). |
| `required-label` | Label every linked issue must carry (default `ready-for-agent`; empty disables). |
| `exempt-title-prefixes` | The repo's declared "no ticket needed" categories, matched against the PR title. |
| `branch-pattern` | Optional full-match regex for the head branch. |

The gate only bites once branch protection on the consumer repo **requires** the
`Ticket-first gate` check on `main` — that half lives in GitHub settings, not in a file, so it has
to be clicked once per repo.

### `sync-labels.yml` — one triage vocabulary everywhere

Creates the five triage labels (`needs-triage`, `needs-info`, `ready-for-agent`,
`ready-for-human`, `wontfix` — canonical copies in [`templates/labels.json`](templates/labels.json))
and repairs drifted color/description. It **never deletes** — a repo's extra labels are its own
business. Call it on `workflow_dispatch` with `permissions: issues: write` and run it once after
wiring a repo up.

### Every check refuses to pass vacuously

A doc checker that discovers zero files reports success while inspecting nothing — the failure mode
that produced `docfiles.py`. Discovery skips directories by path **relative to the docs root**, so a
checkout living beneath a skipped name (a git worktree under `.claude/`) is unaffected, and an empty
walk exits non-zero rather than green. The changelog gate applies the same rule to its own config:
an empty `tracked-docs` fails loudly instead of passing every PR. So do the newer gates: the
ticket-first gate errors when every one of its checks is disabled, and the label sync errors on an
empty labels file.

---

## Templates

Files a consumer repo copies in once — the `setup-kolby-repo` skill walks through all of them:

| File | Purpose |
| --- | --- |
| [`templates/labels.json`](templates/labels.json) | The five triage labels; the source `sync-labels.yml` converges every repo on. |
| [`templates/.github/ISSUE_TEMPLATE/ticket.yml`](templates/.github/ISSUE_TEMPLATE/ticket.yml) | Agent-ready ticket form — done-when gate, out-of-scope, blocking edges. Auto-applies `ready-for-agent`. |
| [`templates/.github/ISSUE_TEMPLATE/bug-report.yml`](templates/.github/ISSUE_TEMPLATE/bug-report.yml) | Raw intake form. Auto-applies `needs-triage`. |
| [`templates/.github/pull_request_template.md`](templates/.github/pull_request_template.md) | The closing reference and the review-before-advance checklist. |
| [`templates/claude-settings.json`](templates/claude-settings.json) | Marketplace pin + plugin enable for `.claude/settings.json`. |
| [`templates/cursor-rules/kolby-workflow.mdc`](templates/cursor-rules/kolby-workflow.mdc) | Thin Cursor rule pointing at the plugin's skills — a `shared-brain` wrapper, not a copy. |

---

## Development

```bash
claude plugin validate ./plugins/kolby-workflow
```

```bash
claude --plugin-dir ./plugins/kolby-workflow
```

Bump `version` in **both** manifests together, or CI will catch it.
