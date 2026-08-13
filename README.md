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
and from `$HOME/.agents/skills` at user scope. **One junction at user scope covers every repo:**

```
mklink /J "%USERPROFILE%\.agents\skills\kolby-workflow" "<path-to-clone>\plugins\kolby-workflow\skills"
```

Run that from `cmd.exe` — `mklink` is a cmd builtin, not a PowerShell cmdlet. Directory junctions
need no administrator rights and are unaffected by `core.symlinks=false`, which is what makes this
safe on Windows where committed symlinks are not.

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

Consumer repos call these instead of copying scripts. Pin by SHA:

```yaml
jobs:
  docs:
    uses: KolbyHalcomb/dev-standards/.github/workflows/docs-ci.yml@<sha>
```

This repo is public, so no Actions access configuration is needed on consumers.

---

## Development

```bash
claude plugin validate ./plugins/kolby-workflow
```

```bash
claude --plugin-dir ./plugins/kolby-workflow
```

Bump `version` in **both** manifests together, or CI will catch it.
