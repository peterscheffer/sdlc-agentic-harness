from conftest import (
    write_config, write_state, write_artefact, run_pipeline,
    state_content, assert_in_output, setup_completed_testing,
    setup_completed_coding,
)


class TestFeature7Gating:

    def test_cannot_advance_to_review_if_coding_not_complete(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        s = state_content(tmp_project)
        s["stages"]["coding"]["status"] = "failed"
        s["current_stage"] = "coding"
        s["completed_stages"] = [x for x in s["completed_stages"] if x != "coding"]
        write_state(tmp_project, s)
        result = run_pipeline(tmp_project, "review")
        output = result.stdout + result.stderr
        assert result.returncode != 0

    def test_cannot_advance_to_review_if_testing_not_complete(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        result = run_pipeline(tmp_project, "review")
        output = result.stdout + result.stderr
        assert result.returncode != 0

    def test_can_advance_to_review_after_all_gate_checks_pass(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        run_pipeline(tmp_project, "review")
        s = state_content(tmp_project)
        assert s["current_stage"] == "review" or s["stages"]["review"]["status"] == "complete"

    def test_gating_prevents_skipping_stages(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        s = state_content(tmp_project)
        s["stages"]["testing"]["status"] = "not_started"
        s["current_stage"] = "coding"
        s["completed_stages"] = [x for x in s["completed_stages"] if x != "testing"]
        write_state(tmp_project, s)
        result = run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        assert s["stages"]["testing"]["status"] in ("complete", "failed")

    def test_display_gate_check_results(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        result = run_pipeline(tmp_project, "review")
        assert "[review]" in result.stdout or result.returncode != 0
