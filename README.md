# dev-standards

Cross-repo conventions for Kolby's repositories, in two layers:

1. **`plugins/kolby-workflow/`** — an agent plugin carrying documentation and change-management
   discipline as skills. Loads in **Claude Code, Cursor, and Codex** from one directory.
2. **`.github/workflows/`** — reusable CI workflows that consumer repos call with `uses:`.

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

---

## Reusable CI workflows

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

### Every check refuses to pass vacuously

A doc checker that discovers zero files reports success while inspecting nothing — the failure mode
that produced `docfiles.py`. Discovery skips directories by path **relative to the docs root**, so a
checkout living beneath a skipped name (a git worktree under `.claude/`) is unaffected, and an empty
walk exits non-zero rather than green. The changelog gate applies the same rule to its own config:
an empty `tracked-docs` fails loudly instead of passing every PR.

---

## Development

```bash
claude plugin validate ./plugins/kolby-workflow
```

```bash
claude --plugin-dir ./plugins/kolby-workflow
```

Bump `version` in **both** manifests together, or CI will catch it.
