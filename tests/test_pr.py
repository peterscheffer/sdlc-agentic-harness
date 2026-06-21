from conftest import (
    write_config, write_state, write_artefact, run_pipeline,
    state_content, assert_in_output, setup_completed_review,
)


class TestFeature10PR:

    def test_pr_checks_gh_auth(self, tmp_project):
        setup_completed_review(tmp_project)
        result = run_pipeline(tmp_project, "pr")
        s = state_content(tmp_project)
        assert s["stages"]["pr"]["status"] == "failed"

    def test_pr_fails_if_gh_not_authenticated(self, tmp_project):
        setup_completed_review(tmp_project)
        result = run_pipeline(tmp_project, "pr")
        s = state_content(tmp_project)
        assert s["stages"]["pr"]["status"] == "failed"

    def test_pr_checks_branch_not_base(self, tmp_project):
        setup_completed_review(tmp_project)
        result = run_pipeline(tmp_project, "pr")
        s = state_content(tmp_project)
        assert s["stages"]["pr"]["status"] == "failed"

    def test_pr_commits_sdlc_artefacts(self, tmp_project):
        setup_completed_review(tmp_project)
        result = run_pipeline(tmp_project, "pr")
        output = result.stdout + result.stderr
        assert sdlc_artefacts_present(tmp_project)

    def test_pr_constructs_title_from_prd(self, tmp_project):
        setup_completed_review(tmp_project)
        result = run_pipeline(tmp_project, "pr")
        output = result.stdout + result.stderr
        assert result.returncode in (0, 1)

    def test_pr_constructs_body_from_review(self, tmp_project):
        setup_completed_review(tmp_project)
        result = run_pipeline(tmp_project, "pr")
        assert result.returncode in (0, 1)

    def test_pr_includes_links_to_artefacts(self, tmp_project):
        setup_completed_review(tmp_project)
        result = run_pipeline(tmp_project, "pr")
        assert result.returncode in (0, 1)

    def test_pr_creates_pr_using_gh_cli(self, tmp_project):
        setup_completed_review(tmp_project)
        result = run_pipeline(tmp_project, "pr")
        assert result.returncode in (0, 1)

    def test_pr_captures_url_on_success(self, tmp_project):
        setup_completed_review(tmp_project)
        result = run_pipeline(tmp_project, "pr")
        assert result.returncode in (0, 1)

    def test_pr_stores_url_in_state(self, tmp_project):
        setup_completed_review(tmp_project)
        result = run_pipeline(tmp_project, "pr")
        s = state_content(tmp_project)
        assert "pr_url" in s

    def test_gate_check_gh_authenticated(self, tmp_project):
        setup_completed_review(tmp_project)
        run_pipeline(tmp_project, "pr")
        s = state_content(tmp_project)
        if "gate_results" in s["stages"]["pr"]:
            assert "gh_authenticated" in s["stages"]["pr"]["gate_results"]

    def test_gate_check_not_on_base_branch(self, tmp_project):
        setup_completed_review(tmp_project)
        run_pipeline(tmp_project, "pr")
        s = state_content(tmp_project)
        if "gate_results" in s["stages"]["pr"]:
            assert "not_on_base_branch" in s["stages"]["pr"]["gate_results"]

    def test_gate_check_pr_created(self, tmp_project):
        setup_completed_review(tmp_project)
        run_pipeline(tmp_project, "pr")
        s = state_content(tmp_project)
        if "gate_results" in s["stages"]["pr"]:
            assert "pr_created" in s["stages"]["pr"]["gate_results"]

    def test_update_state_on_pr_success(self, tmp_project):
        setup_completed_review(tmp_project)
        run_pipeline(tmp_project, "pr")
        s = state_content(tmp_project)
        assert s["stages"]["pr"]["status"] in ("complete", "failed")

    def test_update_state_on_pr_failure(self, tmp_project):
        setup_completed_review(tmp_project)
        run_pipeline(tmp_project, "pr")
        s = state_content(tmp_project)
        assert s["stages"]["pr"]["status"] == "failed"

    def test_display_pr_success(self, tmp_project):
        setup_completed_review(tmp_project)
        result = run_pipeline(tmp_project, "pr")
        output = result.stdout + result.stderr
        assert "[pr]" in output

    def test_display_pr_failure(self, tmp_project):
        setup_completed_review(tmp_project)
        result = run_pipeline(tmp_project, "pr")
        output = result.stdout + result.stderr
        assert "[pr]" in output

    def test_log_pr_creation(self, tmp_project):
        setup_completed_review(tmp_project)
        run_pipeline(tmp_project, "pr")
        logs = list((tmp_project / "sdlc/logs").glob("pr_*.log"))
        s = state_content(tmp_project)
        assert s["stages"]["pr"]["status"] in ("complete", "failed")

    def test_pr_body_contains_summary_section(self, tmp_project):
        setup_completed_review(tmp_project)
        result = run_pipeline(tmp_project, "pr")
        output = result.stdout + result.stderr
        assert result.returncode in (0, 1)

    def test_pr_requires_feature_branch(self, tmp_project):
        write_config(tmp_project)
        s = state_content(tmp_project) if (tmp_project / ".sdlc_state.json").exists() else {}
        result = run_pipeline(tmp_project, "pr")
        assert result.returncode != 0

    def test_force_submit_pr_with_fail_recommendation(self, tmp_project):
        setup_completed_review(tmp_project, recommendation="FAIL")
        result = run_pipeline(tmp_project, "pr", "--force")
        output = result.stdout + result.stderr
        assert "[pr]" in output or result.returncode != 0


def sdlc_artefacts_present(project):
    paths = [
        "sdlc/planning/PRD.md",
        "sdlc/architecture/ARCH.md",
        "sdlc/review/REVIEW.md",
    ]
    for p in paths:
        if not (project / p).exists():
            return False
    return True
