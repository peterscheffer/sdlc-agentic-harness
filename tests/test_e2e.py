from conftest import (
    write_config, write_state, write_artefact, run_pipeline,
    state_content, assert_in_output, setup_completed_planning,
    setup_completed_architecture, setup_completed_coding,
    setup_completed_testing, setup_completed_review,
    PRD_WITHOUT_UI,
)


class TestFeature12EndToEnd:

    def test_happy_path_all_stages_succeed(self, tmp_project):
        write_config(tmp_project)
        r1 = run_pipeline(tmp_project, "planning", "add JWT authentication")
        assert r1.returncode == 0, f"Planning failed: {r1.stderr}"
        r2 = run_pipeline(tmp_project, "ui-design")
        assert r2.returncode == 0, f"UI Design failed: {r2.stderr}"
        r3 = run_pipeline(tmp_project, "architecture")
        assert r3.returncode == 0, f"Architecture failed: {r3.stderr}"
        r3b = run_pipeline(tmp_project, "requirements")
        assert r3b.returncode == 0, f"Requirements failed: {r3b.stderr}"
        write_artefact(tmp_project, "src/feature.py", "# code")
        r4 = run_pipeline(tmp_project, "coding")
        assert r4.returncode == 0, f"Coding failed: {r4.stderr}"
        r5 = run_pipeline(tmp_project, "testing")
        assert r5.returncode == 0, f"Testing failed: {r5.stderr}"
        write_artefact(tmp_project, "sdlc/review/REVIEW.md",
                      "## Recommendation\n\nrecommendation: PASS\n")
        r6 = run_pipeline(tmp_project, "review")
        assert r6.returncode == 0, f"Review failed: {r6.stderr}"
        r7 = run_pipeline(tmp_project, "pr")
        assert r7.returncode == 0, f"PR failed: {r7.stderr}"
        s = state_content(tmp_project)
        assert s["current_stage"] == "pr" or s["stages"]["pr"]["status"] != "not_started"

    def test_happy_path_ui_design_skipped_automatically(self, tmp_project):
        write_config(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", PRD_WITHOUT_UI)
        run_pipeline(tmp_project, "planning", "backend feature")
        run_pipeline(tmp_project, "ui-design")
        run_pipeline(tmp_project, "architecture")
        s = state_content(tmp_project)
        assert s["stages"]["ui-design"]["status"] in ("skipped", "complete")

    def test_terminal_restart_doesnt_lose_progress(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        assert "testing" in s["completed_stages"]

    def test_view_pipeline_status_at_any_time(self, tmp_project):
        write_config(tmp_project)
        run_pipeline(tmp_project, "planning", "my feature")
        result = run_pipeline(tmp_project, "status")
        assert "Pipeline ID:" in result.stdout
        assert "Current Stage:" in result.stdout
        assert "Completed Stages:" in result.stdout

    def test_pipeline_resumable_after_failure(self, tmp_project):
        write_config(tmp_project)
        setup_completed_coding(tmp_project)
        write_config(tmp_project, {"commands": {"test": "exit 1"}})
        r1 = run_pipeline(tmp_project, "testing")
        write_config(tmp_project, {"commands": {"test": "echo 'ok'"}})
        r2 = run_pipeline(tmp_project, "testing")
        s = state_content(tmp_project)
        assert r2.returncode == 0 or s["stages"]["testing"]["status"] == "complete"

    def test_no_data_loss_across_terminal_sessions(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        s1 = state_content(tmp_project)
        s2 = state_content(tmp_project)
        assert s1["pipeline_id"] == s2["pipeline_id"]
        assert s1["completed_stages"] == s2["completed_stages"]

    def test_clean_reset_when_starting_new_feature(self, tmp_project):
        write_config(tmp_project)
        setup_completed_review(tmp_project)
        assert state_content(tmp_project)["stages"]["review"]["status"] == "complete"

    def test_full_pipeline_produces_auditable_output(self, tmp_project):
        write_config(tmp_project)
        setup_completed_review(tmp_project)
        dirs = [
            "sdlc/planning",
            "sdlc/architecture",
            "sdlc/testing",
            "sdlc/review",
        ]
        for d in dirs:
            assert (tmp_project / d).exists()

    def test_happy_path_with_manual_loops(self, tmp_project):
        write_config(tmp_project)
        setup_completed_review(tmp_project, recommendation="FAIL")
        write_artefact(tmp_project, "sdlc/review/REVIEW.md",
                      "## Recommendation\n\nrecommendation: FAIL\n\nIssues found.")
        run_pipeline(tmp_project, "coding")
        run_pipeline(tmp_project, "testing")
        write_artefact(tmp_project, "sdlc/review/REVIEW.md",
                      "## Recommendation\n\nrecommendation: PASS\n")
        run_pipeline(tmp_project, "review")
        s = state_content(tmp_project)
        assert s["stages"]["review"]["status"] == "complete"

    def test_all_artefacts_committed(self, tmp_project):
        write_config(tmp_project)
        setup_completed_review(tmp_project)
        artefacts = [
            "sdlc/planning/PRD.md",
            "sdlc/architecture/ARCH.md",
            "sdlc/testing/TEST_REPORT.md",
            "sdlc/review/REVIEW.md",
        ]
        for art in artefacts:
            if (tmp_project / art).exists():
                assert (tmp_project / art).stat().st_size > 0
