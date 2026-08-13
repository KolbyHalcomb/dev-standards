---
name: changelog-entry
description: How to write an entry in an append-only CHANGELOG — the dated-heading format, the four citation granularities (line, range, section, bare path), and the rule that entries are never edited after the fact. Use when adding a CHANGELOG entry, citing changed files, or correcting an entry that turned out wrong.
---

# Writing a CHANGELOG entry

The CHANGELOG is the intake point: write here first, then edit the affected docs. New entries go at
the **top** of the log, under a dated heading.

## Format

```
## YYYY-MM-DD — Brief description

Optional preamble: why this happened, or what CI could not see. Substantial entries carry one;
routine ones go straight to the bullets.

- Live: a real-world change with no file to cite — a cluster formed, a label created, a VM started
- `path/to/file` line X: what changed          <- surgical edit to existing content
- `path/to/file` lines X-Y: what changed       <- a contiguous block
- `path/to/file` Section Name: what changed    <- an addition to a named section
- `path/to/file`: what changed                 <- a new file, or a change spanning the whole file
```

## Cite at the granularity that locates the change

All four forms are current practice. Pick the one that helps a reader find the change:

| Use | When |
| --- | --- |
| `line X` | A surgical edit to existing content. The default. |
| `lines X-Y` | A contiguous block. |
| `Section Name` | An addition to a named section — better than a line number, because the section survives shifting. |
| bare path | A new file, or a change spanning the whole file. |

**Do not manufacture a line number for a change that does not have one.** A precise-looking citation
that points at the wrong place is worse than an honest bare path.

Not just Markdown — scripts, tests, and config are cited the same way. Related files that got the
*same* change may share one bullet rather than repeating it.

## Entries are never edited after the fact

Line numbers in an append-only log go stale as the file below them shifts. **That is expected and
accepted.** The entry records where the change was *when it landed*, not where it lives now.

Correct a wrong entry with a **new dated entry**, not by rewriting history.

This is the rule people most want to break, usually with good intentions — "I'll just fix that stale
line number." Don't. The log's value is that it is a faithful record of what was believed at the
time; a tidied log cannot be trusted as evidence.

## The "Live:" bullet

Not every change has a file. A cluster formed, a label created, a VM started, a physical cable
moved — these are real changes with nothing to cite. Use `- Live:` so the entry still records them
rather than silently omitting the parts that happened in the world.

## Which ledger

A repo may keep more than one CHANGELOG (for example, one for infrastructure and one for changes
made inside a specific application's own UI). Write to the one that owns the surface you changed. If
a change spans both, the entry goes where the *cause* lives, and the other ledger cross-references it.

## Never read a large CHANGELOG in full

These files grow without bound. Grep for the date or keyword first, then read only that range:

```bash
grep -n "2026-05" CHANGELOG.md
```

Then read the specific line range. Context windows are finite — treat them like the constrained
resource they are.
