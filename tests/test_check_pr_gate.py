"""The ticket-first PR gate's decision logic.

find_linked_issues() and evaluate() are pure so these never need a network or
a real PR -- fetch_labels is injected as a plain function.
"""

import check_pr_gate

REPO = "KolbyHalcomb/example"


def gate(**overrides):
    """evaluate() with a passing baseline; tests override what they exercise."""
    settings = dict(
        title="Add evidence lifecycle",
        body="Closes #12",
        branch="claude/evidence-lifecycle",
        require_linked_issue=True,
        required_label="ready-for-agent",
        exempt_prefixes=(),
        branch_pattern="",
        fetch_labels=lambda number: {"ready-for-agent"},
        repo=REPO,
    )
    settings.update(overrides)
    return check_pr_gate.evaluate(**settings)


class TestFindLinkedIssues:
    def test_finds_closing_reference(self):
        assert check_pr_gate.find_linked_issues("Closes #12") == [12]

    def test_keywords_are_case_insensitive(self):
        assert check_pr_gate.find_linked_issues("fIxEs #3") == [3]

    def test_every_github_keyword_counts(self):
        body = "close #1 closes #2 closed #3 fix #4 fixes #5 fixed #6 resolve #7 resolves #8 resolved #9"
        assert check_pr_gate.find_linked_issues(body) == list(range(1, 10))

    def test_bare_mention_is_not_a_closing_reference(self):
        assert check_pr_gate.find_linked_issues("Related to #12, see #4") == []

    def test_keyword_must_sit_directly_before_the_reference(self):
        assert check_pr_gate.find_linked_issues("Fixes the bug in #12") == []

    def test_full_issue_url_counts_for_this_repo(self):
        body = f"Closes https://github.com/{REPO}/issues/7"
        assert check_pr_gate.find_linked_issues(body, REPO) == [7]

    def test_owner_repo_reference_counts_for_this_repo(self):
        assert check_pr_gate.find_linked_issues(f"Closes {REPO}#7", REPO) == [7]

    def test_duplicates_collapse(self):
        assert check_pr_gate.find_linked_issues("Closes #5. Also fixes #5.") == [5]

    def test_empty_body_finds_nothing(self):
        assert check_pr_gate.find_linked_issues("") == []
        assert check_pr_gate.find_linked_issues(None) == []


class TestLinkedIssueRule:
    def test_linked_and_labelled_passes(self):
        ok, message = gate()

        assert ok
        assert "#12" in message

    def test_no_link_fails(self):
        ok, message = gate(body="Did some work.")

        assert not ok
        assert "Closes #N" in message

    def test_exempt_title_prefix_passes_without_a_link(self):
        ok, message = gate(body="Bump actions/checkout.", title="chore: bump checkout",
                           exempt_prefixes=("chore:", "docs:"))

        assert ok
        assert "exempt" in message

    def test_exempt_prefix_is_case_insensitive(self):
        ok, _ = gate(body="", title="Chore: tidy", exempt_prefixes=("chore:",))

        assert ok

    def test_non_matching_prefix_still_fails(self):
        ok, message = gate(body="", title="feat: new thing", exempt_prefixes=("chore:",))

        assert not ok
        assert "chore:" in message  # the failure names the declared exemptions

    def test_rule_disabled_passes_without_a_link(self):
        ok, _ = gate(body="Did some work.", require_linked_issue=False)

        assert ok


class TestLabelRule:
    def test_linked_issue_without_label_fails(self):
        ok, message = gate(fetch_labels=lambda number: {"needs-triage"})

        assert not ok
        assert "ready-for-agent" in message
        assert "needs-triage" in message

    def test_failure_lists_every_unready_issue(self):
        ok, message = gate(body="Closes #1, closes #2",
                           fetch_labels=lambda number: set())

        assert not ok
        assert "#1" in message
        assert "#2" in message

    def test_missing_issue_fails(self):
        ok, message = gate(fetch_labels=lambda number: None)

        assert not ok
        assert "#12" in message

    def test_empty_required_label_skips_the_label_check(self):
        ok, _ = gate(required_label="",
                     fetch_labels=lambda number: (_ for _ in ()).throw(AssertionError("must not fetch")))

        assert ok

    def test_exempt_pr_that_still_links_an_issue_is_still_label_checked(self):
        ok, _ = gate(title="chore: closes anyway", exempt_prefixes=("chore:",),
                     fetch_labels=lambda number: set())

        assert not ok


class TestBranchRule:
    def test_matching_branch_passes(self):
        ok, _ = gate(branch_pattern=r"(claude|cursor|feat)/.+")

        assert ok

    def test_non_matching_branch_fails(self):
        ok, message = gate(branch="scratch", branch_pattern=r"(claude|cursor|feat)/.+")

        assert not ok
        assert "scratch" in message

    def test_pattern_must_match_the_whole_name(self):
        ok, _ = gate(branch="feat/x-then-junk junk", branch_pattern=r"feat/\S+")

        assert not ok


class TestMisconfigurationGuards:
    """A gate with every check disabled must fail loudly, not pass silently."""

    def test_all_checks_disabled_exits_nonzero(self, monkeypatch, capsys):
        monkeypatch.setenv("REQUIRE_LINKED_ISSUE", "false")
        monkeypatch.setenv("REQUIRED_LABEL", "")
        monkeypatch.setenv("BRANCH_PATTERN", "")

        assert check_pr_gate.main() == 1
        assert "pass every PR" in capsys.readouterr().out

    def test_label_check_without_credentials_exits_nonzero(self, monkeypatch, capsys):
        monkeypatch.setenv("REQUIRE_LINKED_ISSUE", "true")
        monkeypatch.setenv("REQUIRED_LABEL", "ready-for-agent")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

        assert check_pr_gate.main() == 1
        assert "GITHUB_TOKEN" in capsys.readouterr().out
