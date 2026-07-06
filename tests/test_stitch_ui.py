import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".scripts"))

from utils.config import SDLCConfig
from profiles.stitch_ui import StitchUiProfile, DESIGN_PATH, STITCH_DIR_DEFAULT

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOKENS_SCRIPT = PROJECT_ROOT / ".scripts" / "utils" / "design_tokens.py"

STITCH_EXPORT = """<!DOCTYPE html>
<html>
<head>
<script>
tailwind.config = {
  theme: {
    extend: {
      colors: { primary: "#3f51b5", "surface-container-lowest": "#ffffff" },
      spacing: { lg: "24px" },
      fontSize: { "headline-sm": ["24px", { lineHeight: "32px", fontWeight: "600" }] },
      borderRadius: { xl: "12px" },
      fontFamily: { display: ["Manrope"] }
    }
  }
};
</script>
</head>
<body><main class="p-lg text-headline-sm bg-surface-container-lowest"></main></body>
</html>
"""


def make_config(**overrides) -> SDLCConfig:
    base = {"default_model": "m"}
    base.update(overrides)
    return SDLCConfig.model_validate(base)


@pytest.fixture
def in_tmp_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def write_export(root: Path, screen: str = "dashboard"):
    export = root / STITCH_DIR_DEFAULT / screen / "code.html"
    export.parent.mkdir(parents=True, exist_ok=True)
    export.write_text(STITCH_EXPORT)
    return export


def write_design(root: Path):
    design = root / DESIGN_PATH
    design.parent.mkdir(parents=True, exist_ok=True)
    design.write_text("# Design\n\n## Overview\nTest\n\n## Screens\n- Dashboard\n")
    return design


def run_tokens_script(*args, cwd):
    return subprocess.run(
        [sys.executable, str(TOKENS_SCRIPT), *args],
        capture_output=True, text=True, cwd=str(cwd), timeout=30,
    )


class TestRequirementsGate:
    def test_fails_without_design_md(self, in_tmp_dir):
        profile = StitchUiProfile(make_config())
        passed, msg = profile.requirements_gate_checks()[0].run()
        assert not passed
        assert "ui-design" in msg

    def test_fails_without_exports(self, in_tmp_dir):
        write_design(in_tmp_dir)
        profile = StitchUiProfile(make_config())
        passed, msg = profile.requirements_gate_checks()[0].run()
        assert not passed
        assert "code.html" in msg

    def test_passes_with_design_and_tokenful_export(self, in_tmp_dir):
        write_design(in_tmp_dir)
        write_export(in_tmp_dir)
        profile = StitchUiProfile(make_config())
        passed, msg = profile.requirements_gate_checks()[0].run()
        assert passed, msg
        assert "design token" in msg

    def test_fails_when_export_has_no_tokens(self, in_tmp_dir):
        write_design(in_tmp_dir)
        export = in_tmp_dir / STITCH_DIR_DEFAULT / "dashboard" / "code.html"
        export.parent.mkdir(parents=True, exist_ok=True)
        export.write_text("<html><body>no config here</body></html>")
        profile = StitchUiProfile(make_config())
        passed, msg = profile.requirements_gate_checks()[0].run()
        assert not passed
        assert "token" in msg

    def test_cleanup_preserves_ui_design_artifacts(self, in_tmp_dir):
        write_design(in_tmp_dir)
        export = write_export(in_tmp_dir)
        profile = StitchUiProfile(make_config())
        profile.cleanup_artifacts()
        assert export.exists()
        assert (in_tmp_dir / DESIGN_PATH).exists()


class TestCodingStage:
    def test_css_is_scaffold_target_when_exports_exist(self, in_tmp_dir):
        write_export(in_tmp_dir)
        profile = StitchUiProfile(make_config())
        assert profile.coding_scaffold_targets([]) == [profile.css_path()]

    def test_no_scaffold_targets_without_exports(self, in_tmp_dir):
        profile = StitchUiProfile(make_config())
        assert profile.coding_scaffold_targets([]) == []

    def test_coding_context_includes_theme_block_and_export_paths(self, in_tmp_dir):
        write_design(in_tmp_dir)
        write_export(in_tmp_dir)
        profile = StitchUiProfile(make_config())
        context = profile.coding_context()
        assert "@theme {" in context
        assert "--color-primary: #3f51b5;" in context
        assert "--spacing-lg: 24px;" in context
        assert f"{STITCH_DIR_DEFAULT}/dashboard/code.html" in context

    def test_css_path_config_override(self, in_tmp_dir):
        config = make_config(profiles={"stitch-ui": {"css_path": "web/styles/main.css"}})
        profile = StitchUiProfile(config)
        assert profile.css_path() == "web/styles/main.css"
        assert "web/styles/main.css" in profile.resolve_command()

    def test_css_path_detects_existing_stylesheet(self, in_tmp_dir):
        css = in_tmp_dir / "app" / "globals.css"
        css.parent.mkdir(parents=True)
        css.write_text('@import "tailwindcss";\n')
        profile = StitchUiProfile(make_config())
        assert profile.css_path() == "app/globals.css"


class TestVerification:
    def test_preflight_fails_without_exports(self, in_tmp_dir):
        profile = StitchUiProfile(make_config())
        ok, msg = profile.preflight()
        assert not ok
        assert "stitch-ui" in msg

    def test_coding_gate_ports_then_check_passes(self, in_tmp_dir, monkeypatch):
        # design_tokens.py is invoked as `python3 .scripts/...` relative to
        # cwd, so make the script reachable from the tmp project.
        scripts_dir = in_tmp_dir / ".scripts" / "utils"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "design_tokens.py").write_text(TOKENS_SCRIPT.read_text())
        write_export(in_tmp_dir)
        css = in_tmp_dir / "src" / "app" / "globals.css"
        css.parent.mkdir(parents=True)
        css.write_text('@import "tailwindcss";\n')

        profile = StitchUiProfile(make_config())
        checks = profile.coding_verification_gate_checks()
        assert [c.name for c in checks] == ["stitch_tokens_ported", "profile_stitch_ui_verified"]
        for check in checks:
            passed, msg = check.run()
            assert passed, f"{check.name}: {msg}"
        assert "--color-primary: #3f51b5;" in css.read_text()

    def test_testing_verifier_fails_on_missing_tokens(self, in_tmp_dir):
        scripts_dir = in_tmp_dir / ".scripts" / "utils"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "design_tokens.py").write_text(TOKENS_SCRIPT.read_text())
        write_export(in_tmp_dir)
        css = in_tmp_dir / "src" / "app" / "globals.css"
        css.parent.mkdir(parents=True)
        css.write_text('@import "tailwindcss";\n')  # tokens never ported

        profile = StitchUiProfile(make_config())
        result = profile.run_verifier()
        assert result["exit_code"] != 0
        assert "--color-primary" in result["output"]


class TestValidateMode:
    def test_validate_passes_on_tokenful_export(self, in_tmp_dir):
        write_export(in_tmp_dir)
        result = run_tokens_script("validate", STITCH_DIR_DEFAULT, cwd=in_tmp_dir)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "design token(s) extractable" in result.stdout

    def test_validate_fails_on_tokenless_export(self, in_tmp_dir):
        export = in_tmp_dir / STITCH_DIR_DEFAULT / "dashboard" / "code.html"
        export.parent.mkdir(parents=True, exist_ok=True)
        export.write_text("<html><body>nothing</body></html>")
        result = run_tokens_script("validate", STITCH_DIR_DEFAULT, cwd=in_tmp_dir)
        assert result.returncode != 0

    def test_validate_fails_on_missing_dir(self, in_tmp_dir):
        result = run_tokens_script("validate", STITCH_DIR_DEFAULT, cwd=in_tmp_dir)
        assert result.returncode != 0

    def test_check_still_requires_css_flag(self, in_tmp_dir):
        write_export(in_tmp_dir)
        result = run_tokens_script("check", STITCH_DIR_DEFAULT, cwd=in_tmp_dir)
        assert result.returncode != 0
        assert "--css" in result.stderr
