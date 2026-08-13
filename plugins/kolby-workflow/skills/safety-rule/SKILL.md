---
name: safety-rule
description: The pattern for writing an operational safety rule that an agent will actually follow — name the artifact, name the consequence, name the condition for breaking it. Use when adding a rule to a project's safety list, when something just went wrong and the lesson needs recording, or when an existing rule is being ignored or worked around.
---

# Writing a safety rule that gets followed

Safety rules are operational footguns written down. A rule that says "be careful with the network"
gets ignored, because it gives an agent nothing to check against. A rule that names a specific
artifact and a specific consequence gets followed.

## The three required parts

**1. Name the artifact.** The exact file, host, port, command, or tag. Not a category —
`configuration.yaml`, not "config files." `Port 25 (SFP) on the SG2428P`, not "uplink ports." If
the reader has to work out what you meant, the rule does not fire when it should.

**2. Name the consequence.** What actually breaks, and whether it breaks *loudly*. The most
dangerous footguns are the silent ones, and saying so is the load-bearing part of the warning:

> Removing the IoT-side vNIC does not throw an error — it just silently stops the host from seeing
> IoT devices.

**3. Name the condition for breaking it.** Every rule has one. If you do not state it, the rule gets
broken on judgment under pressure instead of on the stated exception — and once a rule has been
broken once without consequence, it stops being a rule.

> Break condition: the guest is tagged `lab` **and not** `stateful`.

Be specific about what does *not* qualify. "The command errored" is almost never a valid reason to
skip a safety step, and saying so explicitly closes the most common workaround.

## Write it the day it happens

The best time to write a rule is the day the thing it forbids actually happened, while the
consequence is still concrete. Include the date and what broke:

> On 2026-07-08 this overwrote `configuration.yaml`.

A rule with a date and a casualty carries weight that a hypothetical does not. It also tells a
future reader that this is a real scar, not a theoretical concern someone imagined.

Rules written *before* being burned are worth having too — just mark them as such, so it is clear
which are speculative and which are paid for.

## Two axes, not one

When a rule protects against two different kinds of loss, say so explicitly. A guest can matter
because **other people depend on it** (`production`) or because **its data cannot be regenerated**
(`stateful`). Those are independent, and a rule that collapses them into one word will under-protect
one of the cases. Write `production` **or** `stateful`, and mean the *or*.

## Give a fallback for when the happy path refuses

A rule that cannot be followed will be skipped. If the prescribed step sometimes fails for a
legitimate reason, name the fallback in the rule itself:

> Where `pct snapshot` refuses because of bind mounts, fall back to `zfs snapshot`.

Without the fallback clause, the first person to hit that error concludes the rule does not apply to
them.

## Cross-reference, never restate

Rules live in **one** place — the shared brain. Other documents point back by number:

```markdown
See Critical Safety Rule 8 in `docs/PROJECT.md`.
```

Never copy the rule text into a second file. A restated rule is a rule that will drift, and a rule
that exists in two versions is worse than a rule that exists in one place people have to look up.

## The template

```markdown
N. **<Imperative statement of what not to do.>**
   <What the artifact is, named exactly.>
   <What breaks, and whether it breaks silently.>
   <When this was learned, if it was learned the hard way.>
   <The condition under which breaking this rule is correct — and what does not qualify.>
```
