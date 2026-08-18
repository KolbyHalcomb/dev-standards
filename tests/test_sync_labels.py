"""The label sync's convergence logic.

plan() is pure so these never need a network. The one invariant that matters
most: the sync never deletes -- a repo's extra labels are its own business.
"""

import json

import sync_labels

DESIRED = [
    {"name": "needs-triage", "color": "d93f0b", "description": "Arrived raw."},
    {"name": "ready-for-agent", "color": "0e8a16", "description": "Agent-ready brief."},
]


class TestPlan:
    def test_empty_repo_creates_everything(self):
        to_create, to_update = sync_labels.plan([], DESIRED)

        assert [label["name"] for label in to_create] == ["needs-triage", "ready-for-agent"]
        assert to_update == []

    def test_matching_labels_need_nothing(self):
        to_create, to_update = sync_labels.plan(DESIRED, DESIRED)

        assert to_create == []
        assert to_update == []

    def test_drifted_color_is_updated(self):
        existing = [dict(DESIRED[0], color="ffffff"), DESIRED[1]]

        to_create, to_update = sync_labels.plan(existing, DESIRED)

        assert to_create == []
        assert [label["name"] for label in to_update] == ["needs-triage"]

    def test_drifted_description_is_updated(self):
        existing = [DESIRED[0], dict(DESIRED[1], description="")]

        _, to_update = sync_labels.plan(existing, DESIRED)

        assert [label["name"] for label in to_update] == ["ready-for-agent"]

    def test_color_comparison_ignores_case_and_hash(self):
        existing = [dict(DESIRED[0], color="#D93F0B"), DESIRED[1]]

        to_create, to_update = sync_labels.plan(existing, DESIRED)

        assert to_create == []
        assert to_update == []

    def test_extra_existing_labels_are_left_alone(self):
        existing = DESIRED + [{"name": "bug", "color": "d73a4a", "description": ""}]

        to_create, to_update = sync_labels.plan(existing, DESIRED)

        assert to_create == []
        assert to_update == []


class TestMisconfigurationGuards:
    def test_empty_labels_file_exits_nonzero(self, tmp_path, monkeypatch, capsys):
        labels_file = tmp_path / "labels.json"
        labels_file.write_text("[]", encoding="utf-8")
        monkeypatch.setenv("LABELS_FILE", str(labels_file))

        assert sync_labels.main([]) == 1
        assert "zero labels" in capsys.readouterr().out

    def test_missing_labels_file_env_exits_nonzero(self, monkeypatch, capsys):
        monkeypatch.delenv("LABELS_FILE", raising=False)

        assert sync_labels.main([]) == 1
        assert "LABELS_FILE" in capsys.readouterr().out

    def test_missing_credentials_exit_nonzero(self, tmp_path, monkeypatch, capsys):
        labels_file = tmp_path / "labels.json"
        labels_file.write_text(json.dumps(DESIRED), encoding="utf-8")
        monkeypatch.setenv("LABELS_FILE", str(labels_file))
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        assert sync_labels.main([]) == 1
        assert "GITHUB_TOKEN" in capsys.readouterr().out


class TestSharedVocabularyFile:
    """The shipped labels.json is what every consumer converges on -- it must
    stay parseable and carry the five canonical triage roles."""

    def test_templates_labels_json_carries_the_five_roles(self):
        labels_file = sync_labels.__file__.rsplit("/scripts/", 1)[0] + "/templates/labels.json"
        with open(labels_file, encoding="utf-8") as handle:
            desired = json.load(handle)

        names = {label["name"] for label in desired}
        assert {"needs-triage", "needs-info", "ready-for-agent",
                "ready-for-human", "wontfix"} <= names
        for label in desired:
            assert label["color"]
            assert label["description"]
