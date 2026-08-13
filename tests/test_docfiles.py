"""Guards for the shared discovery layer.

Both properties here are regressions, not hypotheticals: the relative-path skip
was wrong in two checkers at once, and it failed by discovering *zero* files --
which every checker then reported as a clean pass.
"""

import docfiles


def write(path, text=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TestFindMdFiles:
    def test_finds_markdown(self, tmp_path):
        write(tmp_path / "a.md")
        write(tmp_path / "nested" / "b.md")
        write(tmp_path / "not-markdown.txt")

        found = docfiles.find_md_files(tmp_path)

        assert [f.name for f in found] == ["a.md", "b.md"]

    def test_skips_vendored_dirs(self, tmp_path):
        write(tmp_path / "real.md")
        write(tmp_path / ".agents" / "skills" / "vendored.md")
        write(tmp_path / "node_modules" / "dep.md")

        found = docfiles.find_md_files(tmp_path)

        assert [f.name for f in found] == ["real.md"]

    def test_skip_dirs_match_relative_not_absolute(self, tmp_path):
        """A checkout living *beneath* a skipped directory name still discovers files.

        This is the worktree bug: with the repo at .claude/worktrees/<name>/, an
        absolute-path check matched '.claude' on every file and found nothing.
        """
        root = tmp_path / ".claude" / "worktrees" / "wt"
        write(root / "doc.md")

        found = docfiles.find_md_files(root)

        assert [f.name for f in found] == ["doc.md"]

    def test_skip_files_matches_bare_name(self, tmp_path):
        write(tmp_path / "keep.md")
        write(tmp_path / "CHANGELOG.md")
        write(tmp_path / "nested" / "CHANGELOG.md")

        found = docfiles.find_md_files(tmp_path, skip_files=frozenset({"CHANGELOG.md"}))

        assert [f.name for f in found] == ["keep.md"]

    def test_empty_tree_returns_empty(self, tmp_path):
        assert docfiles.find_md_files(tmp_path) == []


class TestResolveRoot:
    def test_cli_argument_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DOCS_ROOT", str(tmp_path / "from-env"))

        assert docfiles.resolve_root(str(tmp_path)) == tmp_path.resolve()

    def test_falls_back_to_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DOCS_ROOT", str(tmp_path))

        assert docfiles.resolve_root(None) == tmp_path.resolve()

    def test_falls_back_to_cwd(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DOCS_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)

        assert docfiles.resolve_root(None) == tmp_path.resolve()


class TestEnvSet:
    def test_missing_returns_default(self, monkeypatch):
        monkeypatch.delenv("SOME_LIST", raising=False)

        assert docfiles.env_set("SOME_LIST", frozenset({"a"})) == frozenset({"a"})

    def test_splits_on_whitespace_and_commas(self, monkeypatch):
        # Workflow inputs arrive as a single string; block scalars are newline
        # separated and inline ones are usually space or comma separated.
        monkeypatch.setenv("SOME_LIST", "a.md, b.md\nc.md  d.md")

        assert docfiles.env_set("SOME_LIST") == frozenset({"a.md", "b.md", "c.md", "d.md"})

    def test_empty_string_is_empty_not_default(self, monkeypatch):
        """An explicitly empty input must not silently fall back to the default."""
        monkeypatch.setenv("SOME_LIST", "   ")

        assert docfiles.env_set("SOME_LIST", frozenset({"a"})) == frozenset()


class TestVacuousPassError:
    def test_names_the_root_and_the_likely_causes(self, tmp_path):
        message = docfiles.vacuous_pass_error(tmp_path)

        assert str(tmp_path) in message
        assert "DOCS_ROOT" in message
        assert "SKIP_DIRS" in message
