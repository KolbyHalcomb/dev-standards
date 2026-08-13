"""Tests for scripts/check_links.py.

Covers the link-extraction regex, file-existence checking against a synthetic
doc tree, anchor resolution (inline, anchor-only, and into other files, with
fenced-code headings excluded), reference-style `[label]: target` definitions,
and -- in the last section -- main()'s two vacuous-pass guards.

Ported from homelab-docs, where these were written against a module-global
REPO. Root is now a parameter, so the helpers below pass it explicitly.
"""

import pytest

import check_links as links


def run_check(md_file, root):
    """Run check_file against a synthetic tree, isolating the module-global errors list."""
    links.errors.clear()
    links._anchor_cache.clear()
    links.check_file(md_file, root)
    return list(links.errors)


def run_main(root, monkeypatch):
    """Run main() against a synthetic docs root."""
    links.errors.clear()
    links._anchor_cache.clear()
    monkeypatch.setattr("sys.argv", ["check_links.py"])
    monkeypatch.setenv("DOCS_ROOT", str(root))
    monkeypatch.delenv("EXTRA_SKIP_DIRS", raising=False)
    return links.main()


# --------------------------------------------------------------------------
# Link-extraction regex.
# --------------------------------------------------------------------------

def test_link_re_extracts_target():
    assert links.LINK_RE.findall("See [the devices doc](devices.md) for IPs.") == [
        ("the devices doc", "devices.md")
    ]


def test_link_re_finds_multiple_links():
    assert [t for _, t in links.LINK_RE.findall("[a](one.md) and [b](two.md)")] == [
        "one.md",
        "two.md",
    ]


# --------------------------------------------------------------------------
# File-existence checking against a synthetic doc tree.
# --------------------------------------------------------------------------

def test_valid_relative_link_passes(tmp_path):
    (tmp_path / "target.md").write_text("# Target\n")
    src = tmp_path / "src.md"
    src.write_text("Link to [target](target.md).\n")

    assert run_check(src, tmp_path) == []


def test_broken_relative_link_is_reported(tmp_path):
    src = tmp_path / "src.md"
    src.write_text("Link to [ghost](does-not-exist.md).\n")

    errs = run_check(src, tmp_path)

    assert len(errs) == 1
    assert "does-not-exist.md" in errs[0]


def test_external_and_mailto_links_are_skipped(tmp_path):
    src = tmp_path / "src.md"
    src.write_text("[web](https://example.com) [insecure](http://x.io) [mail](mailto:a@b.com)\n")

    assert run_check(src, tmp_path) == []


def test_valid_anchor_only_link_passes(tmp_path):
    src = tmp_path / "src.md"
    src.write_text("## Some Heading\n\nJump to [section](#some-heading).\n")

    assert run_check(src, tmp_path) == []


def test_broken_anchor_only_link_is_reported(tmp_path):
    src = tmp_path / "src.md"
    src.write_text("Jump to [section](#no-such-heading).\n")

    errs = run_check(src, tmp_path)

    assert len(errs) == 1
    assert "no-such-heading" in errs[0]


def test_valid_anchor_in_other_file_passes(tmp_path):
    (tmp_path / "target.md").write_text("# A Heading\n")
    src = tmp_path / "src.md"
    src.write_text("See [heading](target.md#a-heading).\n")

    assert run_check(src, tmp_path) == []


# --------------------------------------------------------------------------
# Anchor validation in an existing target file.
# --------------------------------------------------------------------------

def test_broken_anchor_in_existing_file_is_reported(tmp_path):
    (tmp_path / "target.md").write_text("# Real Heading\n")
    src = tmp_path / "src.md"
    src.write_text("See [bad](target.md#nonexistent-heading).\n")

    errs = run_check(src, tmp_path)

    assert len(errs) == 1
    assert "nonexistent-heading" in errs[0]


def test_anchor_in_fenced_code_is_not_a_valid_target(tmp_path):
    # A `#` line inside a code fence is not a heading and must not satisfy an anchor.
    (tmp_path / "target.md").write_text("```\n# fake heading\n```\n")
    src = tmp_path / "src.md"
    src.write_text("See [bad](target.md#fake-heading).\n")

    assert len(run_check(src, tmp_path)) == 1


# --------------------------------------------------------------------------
# Code is not content: link *examples* inside fenced blocks and inline spans
# must not be resolved as real links. Before this, a repo could not document
# its own linking conventions without failing its own CI.
# --------------------------------------------------------------------------

def test_link_inside_a_fenced_block_is_not_validated(tmp_path):
    src = tmp_path / "src.md"
    src.write_text("```markdown\n[example](nowhere.md)\n```\n")

    assert run_check(src, tmp_path) == []


def test_link_inside_an_inline_code_span_is_not_validated(tmp_path):
    src = tmp_path / "src.md"
    src.write_text("Write links as `[text](path.md)` in prose.\n")

    assert run_check(src, tmp_path) == []


def test_real_link_after_a_fence_is_still_validated(tmp_path):
    # Proves the fence state resets -- otherwise everything after the first code
    # block would silently stop being checked, far worse than the false positive
    # this fixes.
    src = tmp_path / "src.md"
    src.write_text("```\n[ignored](nowhere.md)\n```\n\nReal: [bad](missing.md)\n")

    errors = run_check(src, tmp_path)

    assert len(errors) == 1 and "missing.md" in errors[0]


def test_line_numbers_survive_masking(tmp_path):
    # Masking preserves length and newlines precisely so reported line numbers
    # stay truthful; stripping code would shift every offset after it.
    src = tmp_path / "src.md"
    src.write_text(
        "# Title\n\n```\n[a](x.md)\n[b](y.md)\n```\n\nInline `[c](z.md)` here.\n\n[real](gone.md)\n"
    )

    errors = run_check(src, tmp_path)

    assert len(errors) == 1
    assert errors[0].startswith("src.md:10:"), errors[0]


def test_masking_preserves_length_and_newlines():
    text = "a\n```\n[x](y.md)\n```\nb `[c](d.md)` e\n"

    for masked in (links.mask_fenced_code(text), links.mask_inline_code(text)):
        assert len(masked) == len(text)
        assert masked.count("\n") == text.count("\n")


def test_fence_masking_is_shared_with_heading_anchors():
    # One implementation, two callers. A heading inside a fence is not a heading.
    assert links.heading_anchors("# Real Heading\n\n```\n# Fake Heading\n```\n") == {"real-heading"}


def test_heading_with_inline_code_keeps_its_slug():
    # heading_anchors deliberately masks fences but NOT inline spans: GitHub
    # slugifies "## The `foo` setting" to "the-foo-setting", keeping the span's
    # content. Masking inline code here would yield "the--setting" and break
    # every anchor into a heading that mentions code.
    assert "the-foo-setting" in links.heading_anchors("## The `foo` setting\n")


def test_reference_definition_inside_a_fence_is_not_validated(tmp_path):
    # REF_DEF_RE had the same exposure as LINK_RE and gets the same masked input.
    src = tmp_path / "src.md"
    src.write_text("```markdown\n[label]: nowhere.md\n```\n")

    assert run_check(src, tmp_path) == []


def test_unpaired_backtick_does_not_swallow_later_links(tmp_path):
    # The inline regex is line-bounded on purpose. A runaway match would blank
    # real links and cause *missed* broken links -- worse than a false positive.
    src = tmp_path / "src.md"
    src.write_text("A stray ` backtick here.\n\nAnd a [bad](missing.md) link.\n")

    errors = run_check(src, tmp_path)

    assert len(errors) == 1 and "missing.md" in errors[0]


# --------------------------------------------------------------------------
# Reference-style links: [label]: target definitions are validated too.
# --------------------------------------------------------------------------

def test_reference_definition_broken_target_is_reported(tmp_path):
    src = tmp_path / "src.md"
    src.write_text("See [the doc][ref].\n\n[ref]: does-not-exist.md\n")

    errs = run_check(src, tmp_path)

    assert len(errs) == 1
    assert "does-not-exist.md" in errs[0]


def test_reference_definition_valid_target_passes(tmp_path):
    (tmp_path / "target.md").write_text("# Heading\n")
    src = tmp_path / "src.md"
    src.write_text("See [the doc][ref].\n\n[ref]: target.md#heading\n")

    assert run_check(src, tmp_path) == []


def test_reference_definition_external_url_is_skipped(tmp_path):
    src = tmp_path / "src.md"
    src.write_text("See [site][ref].\n\n[ref]: https://example.com\n")

    assert run_check(src, tmp_path) == []


# --------------------------------------------------------------------------
# main(): the checker must never report success without checking anything.
#
# Two ways it used to: a skip rule matched against absolute path parts (so a
# run from a git worktree under .claude/worktrees/ skipped every file), and no
# guard on an empty file list. Together they printed
# "OK: All links valid (0 files checked)" and exited 0.
# --------------------------------------------------------------------------

def test_main_checks_files_when_root_is_under_a_worktree_path(tmp_path, monkeypatch, capsys):
    root = tmp_path / ".claude" / "worktrees" / "feature-branch"
    root.mkdir(parents=True)
    (root / "target.md").write_text("# A Heading\n")
    (root / "src.md").write_text("See [target](target.md#a-heading).\n")

    assert run_main(root, monkeypatch) == 0

    out = capsys.readouterr().out
    assert "2 files checked" in out, (
        f"expected 2 files checked from a .claude/worktrees/ root, got: {out!r}"
    )


def test_main_catches_broken_link_from_a_worktree_path(tmp_path, monkeypatch, capsys):
    # The real point of the fix: not just a non-zero count, but actual checking.
    root = tmp_path / ".claude" / "worktrees" / "feature-branch"
    root.mkdir(parents=True)
    (root / "src.md").write_text("Link to [ghost](does-not-exist.md).\n")

    assert run_main(root, monkeypatch) == 1
    assert "does-not-exist.md" in capsys.readouterr().out


def test_main_returns_nonzero_when_no_files_are_found(tmp_path, monkeypatch, capsys):
    # An empty walk is a broken checker, not a clean bill of health.
    assert run_main(tmp_path, monkeypatch) != 0
    assert "no .md files found" in capsys.readouterr().out


def test_main_returns_nonzero_when_skip_rule_matches_everything(tmp_path, monkeypatch, capsys):
    # Belt and braces: if discovery ever blanks the tree again for some new
    # reason, the guard still turns it into a visible failure.
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents" / "vendored.md").write_text("# Vendored\n")

    assert run_main(tmp_path, monkeypatch) != 0
    assert "no .md files found" in capsys.readouterr().out


def test_main_passes_on_a_clean_tree(tmp_path, monkeypatch, capsys):
    (tmp_path / "target.md").write_text("# Heading\n")
    (tmp_path / "src.md").write_text("See [target](target.md).\n")

    assert run_main(tmp_path, monkeypatch) == 0
    assert "OK: All links valid (2 files checked)" in capsys.readouterr().out
