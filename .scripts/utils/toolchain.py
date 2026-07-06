import json
import os

# Detected languages. Java is split by build tool because the verifier
# command differs (mvn vs gradle); JS/TS split because TS runners need
# a transpile hook (ts-node).
LANG_PYTHON = "python"
LANG_JAVA_MAVEN = "java-maven"
LANG_JAVA_GRADLE = "java-gradle"
LANG_JS = "js"
LANG_TS = "ts"

PYTHON_MARKERS = ("pyproject.toml", "requirements.txt", "setup.py", "setup.cfg")


def detect_language(root: str = ".") -> str:
    if os.path.exists(os.path.join(root, "pom.xml")):
        return LANG_JAVA_MAVEN
    if os.path.exists(os.path.join(root, "build.gradle")) or \
       os.path.exists(os.path.join(root, "build.gradle.kts")):
        return LANG_JAVA_GRADLE
    if os.path.exists(os.path.join(root, "package.json")):
        if os.path.exists(os.path.join(root, "tsconfig.json")):
            return LANG_TS
        return LANG_JS
    if any(os.path.exists(os.path.join(root, m)) for m in PYTHON_MARKERS):
        return LANG_PYTHON
    return LANG_PYTHON


def is_java(language: str) -> bool:
    return language in (LANG_JAVA_MAVEN, LANG_JAVA_GRADLE)


def is_js(language: str) -> bool:
    return language in (LANG_JS, LANG_TS)


def java_test_command(language: str) -> str:
    return "mvn -q test" if language == LANG_JAVA_MAVEN else "gradle test"


def _read_package_json(root: str = ".") -> dict:
    path = os.path.join(root, "package.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def detect_js_test_framework(root: str = ".") -> str:
    pkg = _read_package_json(root)
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    if "vitest" in deps:
        return "vitest"
    return "jest"
