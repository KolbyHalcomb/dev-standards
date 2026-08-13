"""Tests for scripts/check_tbd.py.

TBD findings are informational (any number of them still exits 0), so most of
these pin the two pieces of real logic: the TBD word-boundary match and the
skip-file set that keeps instructions and changelogs out of a current-state
inventory.

The last section covers the one thing that *is* a failure -- a broken walk.
This checker shared check_links.py's absolute-path skip bug, so from a git
worktree under `.claude/worktrees/` it reported "OK: No TBD placeholders found"
while 25 sat unresolved in the real docs.

Ported from homelab-docs. SKIP_FILES was a module constant there; it is now
DEFAULT_SKIP_FILES with a $TBD_SKIP_FILES override, so the checker can serve
repos that name their ledgers differently.
"""

import pytest

import check_tbd as tbd


def run_main(root, monkeypatch, skip_files=None):
    monkeypatch.setattr("sys.argv", ["check_tbd.py"])
    monkeypatch.setenv("DOCS_ROOT", str(root))
    monkeypatch.delenv("EXTRA_SKIP_DIRS", raising=False)
    if skip_files is None:
        monkeypatch.delenv("TBD_SKIP_FILES", raising=False)
    else:
        monkeypatch.setenv("TBD_SKIP_FILES", skip_files)
    return tbd.main()


@pytest.mark.parametrize("line", ["Model TBD", "Entity in HA | TBD |", "TBD"])
def test_tbd_re_matches_placeholder(line):
    assert tbd.TBD_RE.search(line)


@pytest.mark.parametrize("line", ["standby", "TBDish", "subTBD", "outbid"])
def test_tbd_re_ignores_substrings(line):
    # \bTBD\b must not fire inside other words.
    assert not tbd.TBD_RE.search(line)


def test_default_skip_files_exclude_instructions_and_changelog():
    for name in ("CLAUDE.md", "AGENTS.md", "README.md", "CHANGELOG.md"):
        assert name in tbd.DEFAULT_SKIP_FILES


def test_default_skip_files_do_not_exclude_living_docs():
    # Living-reference docs must stay in the TBD inventory.
    for name in ("devices.md", "vlans.md", "network.md"):
        assert name not in tbd.DEFAULT_SKIP_FILES


# --------------------------------------------------------------------------
# main(): the inventory must not report "no TBDs" without reading anything.
# --------------------------------------------------------------------------

def test_main_finds_tbds_when_root_is_under_a_worktree_path(tmp_path, monkeypatch, capsys):
    root = tmp_path / ".claude" / "worktrees" / "feature-branch"
    root.mkdir(parents=True)
    (root / "devices.md").write_text("| Office printer | TBD |\n")

    assert run_main(root, monkeypatch) == 0

    out = capsys.readouterr().out
    assert "1 unresolved" in out, (
        f"expected the TBD to be found from a .claude/worktrees/ root, got: {out!r}"
    )
    assert "devices.md" in out


def test_main_still_skips_skip_files_and_vendored_dirs(tmp_path, monkeypatch, capsys):
    root = tmp_path / ".claude" / "worktrees" / "feature-branch"
    root.mkdir(parents=True)
    (root / "devices.md").write_text("| Office printer | TBD |\n")
    (root / "CHANGELOG.md").write_text("Historical note about a TBD\n")
    (root / ".agents").mkdir()
    (root / ".agents" / "skill.md").write_text("Vendored TBD\n")

    assert run_main(root, monkeypatch) == 0

    out = capsys.readouterr().out
    assert "1 unresolved" in out
    assert "CHANGELOG.md" not in out
    assert "skill.md" not in out


def test_skip_files_are_configurable(tmp_path, monkeypatch, capsys):
    """A repo whose ledger is named differently can still exclude it."""
    (tmp_path / "devices.md").write_text("| Office printer | TBD |\n")
    (tmp_path / "HISTORY.md").write_text("Historical note about a TBD\n")

    assert run_main(tmp_path, monkeypatch, skip_files="HISTORY.md") == 0

    out = capsys.readouterr().out
    assert "1 unresolved" in out
    assert "HISTORY.md" not in out


def test_main_returns_nonzero_when_no_files_are_found(tmp_path, monkeypatch, capsys):
    # "No TBDs" is a false statement when the inventory looked at nothing.
    assert run_main(tmp_path, monkeypatch) != 0
    assert "no .md files found" in capsys.readouterr().out


def test_main_reports_files_checked_on_a_clean_tree(tmp_path, monkeypatch, capsys):
    # A genuine all-clear must be distinguishable from a vacuous one.
    (tmp_path / "devices.md").write_text("| Office printer | 192.168.0.9 |\n")

    assert run_main(tmp_path, monkeypatch) == 0
    assert "OK: No TBD placeholders found (1 files checked)" in capsys.readouterr().out
