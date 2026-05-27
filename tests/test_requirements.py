from conftest import (
    write_config, write_state, write_artefact,
    run_pipeline, state_content, assert_in_output,
    setup_completed_planning, setup_completed_architecture,
)

REQUIRED_SECTIONS = [
    "## Overview",
    "## Functional Requirements",
    "## Non-Functional Requirements",
    "## Behavioural Requirements",
]


class TestFeatureRequirements:

    def test_generate_requirements_md(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        result = run_pipeline(tmp_project, "requirements")
        assert (tmp_project / "sdlc/requirements/REQUIREMENTS.md").exists()
        content = (tmp_project / "sdlc/requirements/REQUIREMENTS.md").read_text()
        assert len(content) > 0

    def test_requirements_contains_required_sections(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        run_pipeline(tmp_project, "requirements")
        content = (tmp_project / "sdlc/requirements/REQUIREMENTS.md").read_text()
        for heading in REQUIRED_SECTIONS:
            assert heading in content, f"Missing heading: {heading}"

    def test_generates_at_least_one_feature_file(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        run_pipeline(tmp_project, "requirements")
        feature_files = list((tmp_project / "sdlc/requirements").glob("*.feature"))
        assert len(feature_files) >= 1

    def test_feature_files_have_valid_gherkin(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        run_pipeline(tmp_project, "requirements")
        for ff in (tmp_project / "sdlc/requirements").glob("*.feature"):
            content = ff.read_text()
            assert "Feature:" in content
            assert "Scenario:" in content

    def test_gate_check_requirements_md_exists(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        run_pipeline(tmp_project, "requirements")
        s = state_content(tmp_project)
        assert s["stages"]["requirements"]["gate_results"].get("requirements_md_exists") is True

    def test_gate_check_requirements_schema_valid(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        run_pipeline(tmp_project, "requirements")
        s = state_content(tmp_project)
        assert s["stages"]["requirements"]["gate_results"].get("requirements_schema_valid") is True

    def test_gate_check_feature_files_exist(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        run_pipeline(tmp_project, "requirements")
        s = state_content(tmp_project)
        assert s["stages"]["requirements"]["gate_results"].get("feature_files_exist") is True

    def test_update_state_on_requirements_completion(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        run_pipeline(tmp_project, "requirements")
        s = state_content(tmp_project)
        assert s["stages"]["requirements"]["status"] == "complete"
        assert s["stages"]["requirements"]["artefact"] == "sdlc/requirements/REQUIREMENTS.md"
        assert "requirements" in s["completed_stages"]

    def test_display_requirements_completion(self, tmp_project):
        write_config(tmp_project)
        setup_completed_architecture(tmp_project)
        result = run_pipeline(tmp_project, "requirements")
        assert "[requirements]" in result.stdout
        assert "Gate checks passed" in result.stdout
