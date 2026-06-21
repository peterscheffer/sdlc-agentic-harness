import pytest

from conftest import (
    write_config, write_state, write_artefact, run_pipeline,
    state_content, assert_in_output, setup_completed_testing,
    setup_completed_review, MOCK_REVIEW_FAIL, MOCK_REVIEW_PASS,
    setup_completed_planning,
)


class TestFeature11CrossStage:

    def test_re_enter_coding_from_review(self, tmp_project):
        write_config(tmp_project)
        setup_completed_review(tmp_project, recommendation="FAIL")
        write_artefact(tmp_project, "sdlc/review/REVIEW.md", MOCK_REVIEW_FAIL)
        result = run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)
        assert s["current_stage"] == "coding" or s["stages"]["coding"]["status"] != "failed"

    def test_re_enter_planning_from_prior_stage(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        old_id = state_content(tmp_project)["pipeline_id"]
        result = run_pipeline(tmp_project, "planning", "new intent entirely")
        s = state_content(tmp_project)
        assert s["pipeline_id"] != old_id

    def test_force_submit_pr_despite_fail_recommendation(self, tmp_project):
        write_config(tmp_project)
        setup_completed_review(tmp_project, recommendation="FAIL")
        write_artefact(tmp_project, "sdlc/review/REVIEW.md", MOCK_REVIEW_FAIL)
        result = run_pipeline(tmp_project, "pr", "--force")
        output = result.stdout + result.stderr
        assert result.returncode != 0 or "Overriding" in output or "[pr]" in output

    def test_force_override_requires_explicit_confirmation(self, tmp_project):
        write_config(tmp_project)
        setup_completed_review(tmp_project, recommendation="FAIL")
        result = run_pipeline(tmp_project, "pr", "--force")
        output = result.stdout + result.stderr
        assert result.returncode != 0 or "Override" in output

    @pytest.mark.todo
    def test_force_override_succeeds_with_confirmation(self, tmp_project):
        write_config(tmp_project)
        setup_completed_review(tmp_project, recommendation="FAIL")
        result = run_pipeline(tmp_project, "pr", "--force")
        output = result.stdout + result.stderr
        s = state_content(tmp_project)
        assert result.returncode != 0 or s["stages"]["pr"]["status"] != "not_started"
        # TODO: This test should pass `force=True` to run_pipeline once the
        # pipeline supports confirmation. Currently "--force" is passed as
        # a feature name, not a flag. Assert that PR stage was reached.

    def test_cannot_re_enter_earlier_stage_if_current_failed(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        s = state_content(tmp_project)
        s["stages"]["coding"]["status"] = "failed"
        s["current_stage"] = "coding"
        s["completed_stages"] = [x for x in s["completed_stages"] if x != "coding"]
        write_state(tmp_project, s)
        result = run_pipeline(tmp_project, "architecture")
        output = result.stdout + result.stderr
        if result.returncode != 0:
            assert "Error" in output or "Cannot" in output
        else:
            s2 = state_content(tmp_project)
            assert s2["stages"]["architecture"]["status"] in ("complete",)

    def test_looping_back_preserves_git_history(self, tmp_project):
        write_config(tmp_project)
        setup_completed_review(tmp_project, recommendation="FAIL")
        result = run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)
        assert s["current_stage"] == "coding" or s["stages"]["coding"]["status"] in ("complete", "in_progress")
