import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".scripts"))

from utils.toolchain import (
    detect_language, detect_js_test_framework, java_test_command,
    is_java, is_js,
    LANG_PYTHON, LANG_JAVA_MAVEN, LANG_JAVA_GRADLE, LANG_JS, LANG_TS,
)


class TestDetectLanguage:
    def test_python_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
        assert detect_language(str(tmp_path)) == LANG_PYTHON

    def test_python_requirements_txt(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask\n")
        assert detect_language(str(tmp_path)) == LANG_PYTHON

    def test_java_maven(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        assert detect_language(str(tmp_path)) == LANG_JAVA_MAVEN

    def test_java_gradle(self, tmp_path):
        (tmp_path / "build.gradle").write_text("")
        assert detect_language(str(tmp_path)) == LANG_JAVA_GRADLE

    def test_java_gradle_kts(self, tmp_path):
        (tmp_path / "build.gradle.kts").write_text("")
        assert detect_language(str(tmp_path)) == LANG_JAVA_GRADLE

    def test_js(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        assert detect_language(str(tmp_path)) == LANG_JS

    def test_ts(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "tsconfig.json").write_text("{}")
        assert detect_language(str(tmp_path)) == LANG_TS

    def test_empty_dir_defaults_to_python(self, tmp_path):
        assert detect_language(str(tmp_path)) == LANG_PYTHON

    def test_maven_beats_package_json(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        (tmp_path / "package.json").write_text("{}")
        assert detect_language(str(tmp_path)) == LANG_JAVA_MAVEN


class TestJsTestFramework:
    def test_vitest_detected(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps(
            {"devDependencies": {"vitest": "^1.0.0"}}))
        assert detect_js_test_framework(str(tmp_path)) == "vitest"

    def test_jest_default(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps(
            {"devDependencies": {"jest": "^29.0.0"}}))
        assert detect_js_test_framework(str(tmp_path)) == "jest"

    def test_no_package_json_defaults_jest(self, tmp_path):
        assert detect_js_test_framework(str(tmp_path)) == "jest"

    def test_malformed_package_json_defaults_jest(self, tmp_path):
        (tmp_path / "package.json").write_text("{not json")
        assert detect_js_test_framework(str(tmp_path)) == "jest"


class TestHelpers:
    def test_java_test_command(self):
        assert java_test_command(LANG_JAVA_MAVEN) == "mvn -q test"
        assert java_test_command(LANG_JAVA_GRADLE) == "gradle test"

    def test_is_java_is_js(self):
        assert is_java(LANG_JAVA_MAVEN) and is_java(LANG_JAVA_GRADLE)
        assert not is_java(LANG_PYTHON)
        assert is_js(LANG_JS) and is_js(LANG_TS)
        assert not is_js(LANG_PYTHON)
