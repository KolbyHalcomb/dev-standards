---
name: planning-conventions
description: How to plan a multi-step change — spec first, phase it, objective binary gates, rollback defined before starting, default to the durable solution, and land every plan into living docs. Use when planning infrastructure work, anything over ~3 commands, anything touching networking, or when choosing between a quick patch and a scalable fix.
---

# Planning conventions

For any multi-step change — more than roughly three commands, or anything that touches networking.

## 1. Spec first, execute second

Write the plan in plain English before any command runs.

## 2. Phase it

One phase = one session = one validation gate. Do not start Phase 2 until Phase 1's gate passes.

## 3. A gate is objective confirmation

"This command returns this value." "This service responds on this port." Binary pass/fail.

**Not** "seems to be working." If you cannot state the gate as something that is either true or
false when you run it, it is not a gate yet.

## 4. Rollback path defined before starting

Know how to undo before you do. Write it down as part of the spec, not after the fact.

## 5. Default to the durable solution

For any change that will be repeated, extended, or lived with by other people, **lead with the
version that scales** — not the fastest patch. This is a standing instruction, not a per-task
preference.

- **Name the maintenance cost.** If a proposal means "hand-edit this every time something is added,"
  say so out loud and propose the self-maintaining alternative alongside it.
- **Prefer self-maintaining over hand-curated.** Lean on native constructs that update themselves
  over manual lists that drift out of date.
- **Reuse the groundwork already laid.** If an investment already exists, the default design should
  leverage it, not bypass it.
- **Surface the fork, don't pre-decide it.** When short-term and long-term genuinely diverge,
  present both with the trade-off named and give a recommendation. Let the operator choose, but make
  the durable path the default.
- **When unsure of scope, ask "is this a one-off or a pattern?"** before picking the approach.

## 6. Land every plan into living docs

**A plan must never be the only record.** A plan captures *intent*; once executed it has to flow
into the docs that stay current, or it rots into fiction.

- **Each phase names where its result lands.** Before a phase gate counts as passed, its as-built
  result must be reflected in the living **reference** doc (what the current config is) and/or the
  living **runbook** (how to operate it). "Gate passed" means the truth lives in a living doc — not
  just in the plan.
- **Living docs are the source of truth; the plan is the construction record.** When all phases
  land, stamp the plan **Complete** and move it to an archive directory. Never operate off a plan —
  operate off the living docs.
- **Plans live in `docs/plans/<slug>/`** (clean slug, no date prefix) with a `README.md` spec plus
  per-phase files. Operating guides and runbooks stay as top-level living docs, not buried inside a
  plan folder.

## The failure this prevents

The common ending for an unplanned multi-step change is a half-migrated system where nobody can say
which phase actually completed, because the only record of intent was a conversation and the only
record of outcome was "it seemed fine." Phases with binary gates and a named landing place make that
state impossible to reach by accident.
