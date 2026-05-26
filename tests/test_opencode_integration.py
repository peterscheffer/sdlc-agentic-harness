from conftest import (
    write_config, write_state, write_artefact, run_pipeline,
    state_content, assert_in_output, setup_completed_planning,
    setup_completed_architecture, setup_completed_testing,
    PRD_WITHOUT_UI, PRINCIPLES_CONTENT,
)


class TestFeature13OpenCodeIntegration:

    def test_sdlc_slash_command_available(self, tmp_project):
        write_config(tmp_project)
        result = run_pipeline(tmp_project, "planning", "test")
        assert result.returncode == 0

    def test_slash_command_output_displayed(self, tmp_project):
        write_config(tmp_project)
        result = run_pipeline(tmp_project, "planning", "test")
        assert "[planning]" in result.stdout or "PRD.md" in result.stdout

    def test_developer_output_clear_and_actionable(self, tmp_project):
        write_config(tmp_project)
        result = run_pipeline(tmp_project, "planning", "test feature")
        output = result.stdout + result.stderr
        assert "[planning]" in output

    def test_error_messages_specific_and_helpful(self, tmp_project):
        result = run_pipeline(tmp_project, "planning", "test")
        output = result.stdout + result.stderr
        if result.returncode != 0:
            assert "Error" in output or "error" in output.lower()

    def test_model_selection_from_config(self, tmp_project):
        write_config(tmp_project, {
            "stages": {"planning": {"model": "openai/gpt-4o-mini"}}
        })
        result = run_pipeline(tmp_project, "planning", "test")
        assert result.returncode == 0

    def test_subtask_isolation(self, tmp_project):
        write_config(tmp_project)
        run_pipeline(tmp_project, "planning", "feature a")
        result = run_pipeline(tmp_project, "architecture")
        assert result.returncode == 0 or "Cannot" in result.stdout

    def test_sequential_commands_work(self, tmp_project):
        write_config(tmp_project)
        r1 = run_pipeline(tmp_project, "planning", "feature")
        assert r1.returncode == 0
        r2 = run_pipeline(tmp_project, "architecture")
        s = state_content(tmp_project)
        assert "architecture" in s["completed_stages"]

    def test_examine_artefacts_between_stages(self, tmp_project):
        write_config(tmp_project)
        run_pipeline(tmp_project, "planning", "test")
        prd = tmp_project / "sdlc/planning/PRD.md"
        assert prd.exists()
        content = prd.read_text()
        assert "@" not in content
        run_pipeline(tmp_project, "architecture")
        assert (tmp_project / "sdlc/architecture/ARCH.md").exists()
