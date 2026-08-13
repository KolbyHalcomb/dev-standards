"""The CHANGELOG gate's decision logic.

evaluate() is pure so these never need a real git diff -- the point of pulling
it out of inline CI Bash, where it could only be exercised by opening a PR.
"""

import check_changelog

TRACKED = frozenset({"devices.md", "network.md"})
CHANGELOGS = frozenset({"CHANGELOG.md", "CHANGELOG-homeassistant.md"})


def evaluate(changed):
    return check_changelog.evaluate(changed, TRACKED, CHANGELOGS)


class TestEvaluate:
    def test_no_tracked_docs_changed_passes(self):
        ok, message = evaluate(["README.md", "scripts/thing.py"])

        assert ok
        assert "not required" in message

    def test_tracked_doc_without_changelog_fails(self):
        ok, message = evaluate(["devices.md"])

        assert not ok
        assert "devices.md" in message

    def test_tracked_doc_with_changelog_passes(self):
        ok, message = evaluate(["devices.md", "CHANGELOG.md"])

        assert ok
        assert "devices.md" in message

    def test_any_configured_changelog_satisfies_the_gate(self):
        ok, _ = evaluate(["devices.md", "CHANGELOG-homeassistant.md"])

        assert ok

    def test_failure_lists_every_offending_doc(self):
        ok, message = evaluate(["devices.md", "network.md"])

        assert not ok
        assert "devices.md" in message
        assert "network.md" in message

    def test_failure_names_what_would_satisfy_the_gate(self):
        _, message = evaluate(["devices.md"])

        assert "CHANGELOG.md" in message

    def test_empty_diff_passes(self):
        ok, _ = evaluate([])

        assert ok


class TestMisconfigurationGuards:
    """An unconfigured gate must fail loudly, not pass silently.

    Both of these would otherwise be the exact vacuous pass this suite exists to
    refuse: nothing tracked means every PR is green regardless of content.
    """

    def test_no_tracked_docs_configured_exits_nonzero(self, monkeypatch, capsys):
        monkeypatch.delenv("TRACKED_DOCS", raising=False)
        monkeypatch.setenv("CHANGELOG_FILES", "CHANGELOG.md")

        assert check_changelog.main(["HEAD", "HEAD"]) == 1
        assert "TRACKED_DOCS" in capsys.readouterr().out

    def test_no_changelog_files_configured_exits_nonzero(self, monkeypatch, capsys):
        monkeypatch.setenv("TRACKED_DOCS", "devices.md")
        monkeypatch.setenv("CHANGELOG_FILES", "")

        assert check_changelog.main(["HEAD", "HEAD"]) == 1
        assert "CHANGELOG_FILES" in capsys.readouterr().out
