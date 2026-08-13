"""Guards for the two seams the tri-client plugin layout opens.

One plugin directory serves Claude Code, Cursor, and Codex. That buys a shared
skills/ tree at the cost of two manifests, and it only holds while every
SKILL.md stays on the portable frontmatter subset. Both costs are checked here.
"""

import json

import check_manifests
import check_skills

AGENT_MANIFEST = {
    "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
    "name": "demo",
    "version": "1.0.0",
    "description": "A demo plugin.",
}

CLAUDE_MANIFEST = {
    "name": "demo",
    "version": "1.0.0",
    "description": "A demo plugin.",
    "author": {"name": "Someone"},
}


def make_plugin(tmp_path, agent=None, claude=None, name="demo"):
    plugin = tmp_path / name
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / "plugin.json").write_text(
        json.dumps(agent if agent is not None else AGENT_MANIFEST), encoding="utf-8"
    )
    (plugin / ".claude-plugin" / "plugin.json").write_text(
        json.dumps(claude if claude is not None else CLAUDE_MANIFEST), encoding="utf-8"
    )
    return plugin


class TestManifestAgreement:
    def test_matching_manifests_pass(self, tmp_path):
        assert check_manifests.check_plugin(make_plugin(tmp_path)) == []

    def test_version_drift_is_caught(self, tmp_path):
        claude = {**CLAUDE_MANIFEST, "version": "2.0.0"}

        failures = check_manifests.check_plugin(make_plugin(tmp_path, claude=claude))

        assert len(failures) == 1
        assert "version" in failures[0]

    def test_description_drift_is_caught(self, tmp_path):
        claude = {**CLAUDE_MANIFEST, "description": "Something else."}

        failures = check_manifests.check_plugin(make_plugin(tmp_path, claude=claude))

        assert any("description" in f for f in failures)

    def test_claude_only_fields_are_not_compared(self, tmp_path):
        """author/homepage/license live in one manifest by design."""
        claude = {**CLAUDE_MANIFEST, "license": "MIT", "homepage": "https://example.com"}

        assert check_manifests.check_plugin(make_plugin(tmp_path, claude=claude)) == []

    def test_absent_shared_field_is_caught(self, tmp_path):
        claude = {k: v for k, v in CLAUDE_MANIFEST.items() if k != "version"}

        failures = check_manifests.check_plugin(make_plugin(tmp_path, claude=claude))

        assert any("version" in f for f in failures)

    def test_name_must_match_directory(self, tmp_path):
        """The directory name is the namespace users type as /name:skill."""
        agent = {**AGENT_MANIFEST, "name": "renamed"}
        claude = {**CLAUDE_MANIFEST, "name": "renamed"}

        failures = check_manifests.check_plugin(make_plugin(tmp_path, agent, claude))

        assert any("does not match its directory" in f for f in failures)


def write_skill(tmp_path, frontmatter, name="demo-skill"):
    skill = tmp_path / name
    skill.mkdir(parents=True)
    path = skill / "SKILL.md"
    path.write_text(f"---\n{frontmatter}\n---\n\nBody.\n", encoding="utf-8")
    return path


class TestSkillPortability:
    def test_name_and_description_pass(self, tmp_path):
        path = write_skill(tmp_path, "name: demo-skill\ndescription: Does a thing.")

        assert check_skills.check_skill(path) == []

    def test_client_specific_key_is_rejected(self, tmp_path):
        path = write_skill(
            tmp_path, "name: demo-skill\ndescription: Does a thing.\nallowed-tools: Read"
        )

        failures = check_skills.check_skill(path)

        assert any("allowed-tools" in f and "portability" in f for f in failures)

    def test_unknown_key_is_rejected(self, tmp_path):
        path = write_skill(tmp_path, "name: demo-skill\ndescription: Thing.\nwhatever: 1")

        assert any("whatever" in f for f in check_skills.check_skill(path))

    def test_missing_description_is_caught(self, tmp_path):
        path = write_skill(tmp_path, "name: demo-skill")

        assert any("description" in f for f in check_skills.check_skill(path))

    def test_empty_description_is_caught(self, tmp_path):
        path = write_skill(tmp_path, "name: demo-skill\ndescription:")

        assert any("description" in f for f in check_skills.check_skill(path))

    def test_name_must_match_directory(self, tmp_path):
        path = write_skill(tmp_path, "name: something-else\ndescription: Thing.")

        assert any("does not match its directory" in f for f in check_skills.check_skill(path))

    def test_missing_frontmatter_is_caught(self, tmp_path):
        skill = tmp_path / "demo-skill"
        skill.mkdir()
        path = skill / "SKILL.md"
        path.write_text("# Just a heading\n", encoding="utf-8")

        assert any("frontmatter" in f for f in check_skills.check_skill(path))

    def test_folded_description_continuation_is_joined(self, tmp_path):
        """A wrapped description is one value, not an unknown second key."""
        path = write_skill(
            tmp_path, "name: demo-skill\ndescription: Starts here\n  and continues here."
        )

        assert check_skills.check_skill(path) == []
