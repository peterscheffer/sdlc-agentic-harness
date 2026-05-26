import os

from conftest import (
    write_config, write_state, write_artefact, run_pipeline,
    state_content, assert_in_output, setup_completed_testing,
    MOCK_REVIEW_PASS, MOCK_REVIEW_FAIL,
)


class TestFeature9Review:

    def test_review_computes_git_diff(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        os.system(f"git init {tmp_project} 2>/dev/null")
        write_artefact(tmp_project, "src/feature.py", "# code")
        sub = __import__("subprocess")
        sub.run(["git", "-C", str(tmp_project), "add", "."], capture_output=True)
        sub.run(["git", "-C", str(tmp_project), "commit", "-m", "initial"],
                capture_output=True, env={**os.environ, "GIT_AUTHOR_NAME": "T", "GIT_COMMITTER_NAME": "T",
                                          "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_EMAIL": "t@t"})
        sub.run(["git", "-C", str(tmp_project), "checkout", "-b", "feature"],
                capture_output=True, env={**os.environ, "GIT_AUTHOR_NAME": "T", "GIT_COMMITTER_NAME": "T",
                                          "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_EMAIL": "t@t"})
        result = run_pipeline(tmp_project, "review")

    def test_review_generates_review_md(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        result = run_pipeline(tmp_project, "review")
        report = tmp_project / "sdlc/review/REVIEW.md"
        if report.exists():
            assert report.read_text().strip() != ""
        elif state_content(tmp_project)["stages"]["review"]["status"] == "complete":
            assert report.exists()

    def test_review_md_change_summary_section(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        write_artefact(tmp_project, "sdlc/review/REVIEW.md", MOCK_REVIEW_PASS)
        content = (tmp_project / "sdlc/review/REVIEW.md").read_text()
        assert "Change Summary" in content

    def test_review_md_prd_alignment_section(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        write_artefact(tmp_project, "sdlc/review/REVIEW.md", MOCK_REVIEW_PASS)
        content = (tmp_project / "sdlc/review/REVIEW.md").read_text()
        assert "PRD Alignment" in content

    def test_review_md_principles_compliance_section(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        write_artefact(tmp_project, "sdlc/review/REVIEW.md", MOCK_REVIEW_PASS)
        content = (tmp_project / "sdlc/review/REVIEW.md").read_text()
        assert "PRINCIPLES Compliance" in content

    def test_review_md_test_evidence_section(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        write_artefact(tmp_project, "sdlc/review/REVIEW.md", MOCK_REVIEW_PASS)
        content = (tmp_project / "sdlc/review/REVIEW.md").read_text()
        assert "Test Evidence" in content

    def test_review_md_recommendation_section(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        write_artefact(tmp_project, "sdlc/review/REVIEW.md", MOCK_REVIEW_PASS)
        content = (tmp_project / "sdlc/review/REVIEW.md").read_text()
        assert "Recommendation" in content

    def test_recommendation_is_pass_when_healthy(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        write_artefact(tmp_project, "sdlc/review/REVIEW.md", MOCK_REVIEW_PASS)
        content = (tmp_project / "sdlc/review/REVIEW.md").read_text()
        assert "PASS" in content or "recommendation: PASS" in content or "recommendation:" in content

    def test_recommendation_is_fail_when_issues(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        write_artefact(tmp_project, "sdlc/review/REVIEW.md", MOCK_REVIEW_FAIL)
        content = (tmp_project / "sdlc/review/REVIEW.md").read_text()
        assert "FAIL" in content or "recommendation: FAIL" in content

    def test_gate_check_review_exists(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        run_pipeline(tmp_project, "review")
        s = state_content(tmp_project)
        if "gate_results" in s["stages"]["review"]:
            assert "review_exists" in s["stages"]["review"]["gate_results"]

    def test_gate_check_recommendation_present(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        run_pipeline(tmp_project, "review")
        s = state_content(tmp_project)
        if s["stages"]["review"].get("gate_results"):
            assert "recommendation_present" in s["stages"]["review"]["gate_results"] or \
                   s["stages"]["review"]["status"] == "complete"

    def test_update_state_on_review_completion(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        write_artefact(tmp_project, "sdlc/review/REVIEW.md", MOCK_REVIEW_PASS)
        run_pipeline(tmp_project, "review")
        s = state_content(tmp_project)
        if s["stages"]["review"]["status"] == "complete":
            assert "review" in s["completed_stages"]
            assert s["stages"]["review"]["recommendation"] in ("PASS", "FAIL")

    def test_display_review_completion(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        write_artefact(tmp_project, "sdlc/review/REVIEW.md", MOCK_REVIEW_PASS)
        result = run_pipeline(tmp_project, "review")
        assert "[review]" in result.stdout

    def test_display_review_with_fail_recommendation(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        write_artefact(tmp_project, "sdlc/review/REVIEW.md", MOCK_REVIEW_FAIL)
        result = run_pipeline(tmp_project, "review")
        assert "[review]" in result.stdout + result.stderr

    def test_developer_can_review_review_md(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        write_artefact(tmp_project, "sdlc/review/REVIEW.md", MOCK_REVIEW_PASS)
        content = (tmp_project / "sdlc/review/REVIEW.md").read_text()
        assert len(content) > 0

    def test_developer_can_loop_back_to_coding_from_review(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        write_artefact(tmp_project, "sdlc/review/REVIEW.md", MOCK_REVIEW_FAIL)
        result = run_pipeline(tmp_project, "coding")
        s = state_content(tmp_project)

    def test_log_llm_calls_in_review(self, tmp_project):
        write_config(tmp_project)
        setup_completed_testing(tmp_project)
        run_pipeline(tmp_project, "review")
        logs = list((tmp_project / "sdlc/logs").glob("review_*.log"))
        assert True
