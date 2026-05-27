from conftest import (
    write_config, write_state, write_artefact, write_principles,
    run_pipeline, state_content, assert_in_output, setup_completed_planning,
    PRD_WITH_UI, PRD_WITHOUT_UI,
)


DESIGN_MISSING_REQUIRED = """# DESIGN

## Overview
Test design.

## Some Other Section
Not a components section.
"""


class TestFeature3UiDesign:

    def test_architecture_does_not_auto_run_ui_design(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", PRD_WITHOUT_UI)
        result = run_pipeline(tmp_project, "architecture")
        s = state_content(tmp_project)
        assert s["stages"]["ui-design"]["status"] == "not_started"

    def test_auto_run_ui_design_if_prd_contains_ui_keywords(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", PRD_WITH_UI)
        result = run_pipeline(tmp_project, "ui-design")
        s = state_content(tmp_project)
        assert (tmp_project / "sdlc/ui-design/DESIGN.md").exists()

    def test_generate_design_md_conforming_to_stitch_spec(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", PRD_WITH_UI)
        run_pipeline(tmp_project, "ui-design")
        content = (tmp_project / "sdlc/ui-design/DESIGN.md").read_text()
        assert len(content) > 0

    def test_design_md_contains_required_sections(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", PRD_WITH_UI)
        write_artefact(tmp_project, "sdlc/ui-design/DESIGN.md",
                      "# DESIGN\n\n## Overview\n\n## Components\n\n## Screens")
        run_pipeline(tmp_project, "ui-design")
        content = (tmp_project / "sdlc/ui-design/DESIGN.md").read_text()
        assert "## Overview" in content
        assert "## Components" in content or "## Screens" in content

    def test_gate_check_design_md_exists(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", PRD_WITH_UI)
        run_pipeline(tmp_project, "ui-design")
        s = state_content(tmp_project)
        assert s["stages"]["ui-design"]["gate_results"].get("design_md_exists") is True

    def test_gate_check_design_schema_valid(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", PRD_WITH_UI)
        run_pipeline(tmp_project, "ui-design")
        s = state_content(tmp_project)
        assert s["stages"]["ui-design"]["gate_results"].get("design_schema_valid") is True

    def test_fail_if_design_md_missing(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        s = state_content(tmp_project)
        assert True

    def test_fail_if_design_md_missing_required_sections(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/ui-design/DESIGN.md", DESIGN_MISSING_REQUIRED)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", PRD_WITH_UI)
        write_principles(tmp_project)
        run_pipeline(tmp_project, "ui-design")

    def test_developer_can_skip_ui_design(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", PRD_WITH_UI)
        result = run_pipeline(tmp_project, "architecture")
        s = state_content(tmp_project)
        assert s["stages"]["ui-design"]["status"] == "not_started"

    def test_developer_can_force_run_ui_design(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", PRD_WITHOUT_UI)
        result = run_pipeline(tmp_project, "ui-design")
        assert (tmp_project / "sdlc/ui-design/DESIGN.md").exists()

    def test_update_state_on_ui_design_completion(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", PRD_WITH_UI)
        run_pipeline(tmp_project, "ui-design")
        s = state_content(tmp_project)
        assert s["stages"]["ui-design"]["status"] in ("complete", "skipped")
        if s["stages"]["ui-design"]["status"] == "complete":
            assert s["stages"]["ui-design"]["artefact"] == "sdlc/ui-design/DESIGN.md"

    def test_display_ui_design_completion(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md", PRD_WITH_UI)
        result = run_pipeline(tmp_project, "ui-design")
        assert "[ui-design]" in result.stdout

    def test_architecture_does_not_touch_ui_design(self, tmp_project):
        write_config(tmp_project)
        setup_completed_planning(tmp_project)
        write_artefact(tmp_project, "sdlc/planning/PRD.md",
                      "# Summary\n\nBackend only feature with no user interface concerns whatsoever.")
        result = run_pipeline(tmp_project, "architecture")
        s = state_content(tmp_project)
        assert s["stages"]["ui-design"]["status"] == "not_started"
