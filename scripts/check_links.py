#!/usr/bin/env python3
"""
Internal markdown link checker.

Verifies that relative file links in .md files point to existing files, and that
any #anchor resolves to a real heading in the target file. External URLs
(http/https/mailto) are skipped -- they require network access.

Handles both inline links `[text](target)` and reference definitions
`[label]: target`.

Usage:
    check_links.py [--root PATH]

The docs root defaults to $DOCS_ROOT, then the working directory.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import docfiles

LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
# Reference definition, e.g.  [ref]: devices.md#heading "optional title"
REF_DEF_RE = re.compile(r'^\s{0,3}\[([^\]]+)\]:\s*(\S+)', re.MULTILINE)
HEADING_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*#*$')

# An inline code span: a run of N backticks, content, then a matching run of N.
# Deliberately line-bounded (`[^\n]`, no DOTALL) -- a multi-line match that ran
# away on an unpaired backtick would blank real links and cause *missed* broken
# links, which is a worse failure for a link checker than the false positive
# this is fixing.
INLINE_CODE_RE = re.compile(r'(?<!`)(`+)(?!`)([^\n]+?)(?<!`)\1(?!`)')

errors = []

# Cache of {resolved_path: set(anchor_slugs)} so each file is slugified once.
_anchor_cache = {}


def slugify(heading: str) -> str:
    """Approximate GitHub's heading-to-anchor slug algorithm."""
    s = heading.strip().lower()
    s = re.sub(r'[^\w\s-]', '', s)   # drop punctuation (keep word chars, spaces, hyphens)
    s = re.sub(r'\s+', '-', s)
    return s


def mask_fenced_code(text: str) -> str:
    """Blank fenced code blocks, keeping length and newlines identical.

    Masking rather than stripping is deliberate: `validate_target` derives the
    reported line number from a match offset into the original text, so anything
    that shifts offsets silently misreports where an error is.
    """
    out = []
    in_fence = False
    for line in text.split('\n'):
        if line.strip().startswith(('```', '~~~')):
            in_fence = not in_fence
            out.append(' ' * len(line))
            continue
        out.append(' ' * len(line) if in_fence else line)
    return '\n'.join(out)


def mask_inline_code(text: str) -> str:
    """Blank inline code spans, keeping length and newlines identical."""
    return INLINE_CODE_RE.sub(lambda m: ' ' * len(m.group(0)), text)


def heading_anchors(text: str) -> set:
    """Return the set of anchor slugs for all headings, skipping fenced code.

    Fenced code only -- **not** inline code. GitHub slugifies ``## The `foo` setting``
    to `the-foo-setting`, keeping the span's content and dropping just the
    backticks. Masking inline spans here would yield `the--setting` and break
    every anchor link into a heading that contains code.
    """
    anchors, counts = set(), {}
    for line in mask_fenced_code(text).split('\n'):
        m = HEADING_RE.match(line)
        if not m:
            continue
        slug = slugify(m.group(2))
        # GitHub disambiguates repeated headings with -1, -2, ...
        n = counts.get(slug, -1) + 1
        counts[slug] = n
        anchors.add(slug if n == 0 else f"{slug}-{n}")
    return anchors


def anchors_for(path: Path) -> set:
    if path not in _anchor_cache:
        try:
            _anchor_cache[path] = heading_anchors(path.read_text(encoding="utf-8"))
        except OSError:
            _anchor_cache[path] = set()
    return _anchor_cache[path]


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def validate_target(target: str, md_file: Path, text: str, start: int, label: str, root: Path):
    """Check one link target (file existence + anchor) and record any error."""
    target = target.strip().strip('<>')
    if target.startswith(('http://', 'https://', 'mailto:')):
        return
    path_part, _, anchor = target.partition('#')

    def report(msg):
        line_num = text[:start].count('\n') + 1
        errors.append(f"{rel(md_file, root)}:{line_num}: {msg} '{label}'")

    if not path_part:
        # Anchor-only link like [text](#section) -> resolve against the current file.
        if anchor and anchor not in anchors_for(md_file):
            report(f"broken anchor '#{anchor}' (no such heading) in")
        return

    resolved = (md_file.parent / path_part).resolve()
    if not resolved.exists():
        report("broken link")
        return

    if anchor and resolved.suffix == '.md' and anchor not in anchors_for(resolved):
        report(f"broken anchor '#{anchor}' (no such heading in {path_part}) in")


def check_file(md_file: Path, root: Path):
    text = md_file.read_text(encoding="utf-8")
    # Scan a masked copy so link *examples* inside code are not resolved as real
    # links -- a doc that shows what a good link looks like should not fail CI.
    # Offsets are preserved, so `text` stays the source for line numbers.
    scannable = mask_inline_code(mask_fenced_code(text))

    for m in LINK_RE.finditer(scannable):
        validate_target(m.group(2), md_file, text, m.start(), f"[{m.group(1)}]({m.group(2)})", root)

    for m in REF_DEF_RE.finditer(scannable):
        validate_target(m.group(2), md_file, text, m.start(), f"[{m.group(1)}]: {m.group(2)}", root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', help='docs root (default: $DOCS_ROOT, then cwd)')
    args = parser.parse_args()
    root = docfiles.resolve_root(args.root)

    # Discovery (and the vendored-skill-tree skip) lives in docfiles so the
    # relative-path and empty-walk guards are shared with check_tbd.py.
    skip_dirs = docfiles.SKIP_DIRS | docfiles.env_set('EXTRA_SKIP_DIRS')
    md_files = docfiles.find_md_files(root, skip_dirs=skip_dirs)

    if not md_files:
        print(docfiles.vacuous_pass_error(root))
        return 1

    for f in md_files:
        check_file(f, root)

    if errors:
        print(f"BROKEN LINKS ({len(errors)}):\n")
        for e in errors:
            print(f"  x {e}")
        return 1

    print(f"OK: All links valid ({len(md_files)} files checked)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
