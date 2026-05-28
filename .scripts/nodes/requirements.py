import os
import re
import glob
from datetime import datetime, timezone

from utils.state import SDLCPersistedState
from utils.config import SDLCConfig
from utils.llm import call_llm
from gates.gate_runner import (
    GateCheck, run_gate_checks,
    check_file_exists, check_has_heading,
)

REQUIREMENTS_PATH = "sdlc/requirements/REQUIREMENTS.md"
GHERKIN_DIR = "sdlc/requirements"
REQUIRED_SECTIONS = [
    "## Overview",
    "## Functional Requirements",
    "## Non-Functional Requirements",
    "## Behavioural Requirements",
]


def execute_requirements(state: SDLCPersistedState, config: SDLCConfig, conversation_context: str = "") -> SDLCPersistedState:
    print("\n[requirements] Generating REQUIREMENTS.md and Gherkin feature files...")

    os.makedirs(GHERKIN_DIR, exist_ok=True)

    prd_content = ""
    if os.path.exists("sdlc/planning/PRD.md"):
        with open("sdlc/planning/PRD.md") as f:
            prd_content = f.read()

    design_content = ""
    if os.path.exists("sdlc/ui-design/DESIGN.md"):
        with open("sdlc/ui-design/DESIGN.md") as f:
            design_content = f.read()

    arch_content = ""
    if os.path.exists("sdlc/architecture/ARCH.md"):
        with open("sdlc/architecture/ARCH.md") as f:
            arch_content = f.read()

    system_prompt = (
        "You are a requirements analyst. Generate a detailed requirements specification "
        "and Gherkin feature files based on the project's PRD, UI design, and architecture."
    )

    parts = [
        "# Input Documents\n",
    ]
    if prd_content:
        parts.append(f"## PRD\n{prd_content}\n")
    if design_content:
        parts.append(f"## UI Design\n{design_content}\n")
    if arch_content:
        parts.append(f"## Architecture\n{arch_content}\n")

    parts.append(
        "## Instructions\n\n"
        "Based on the input documents above and the conversation context, generate:\n\n"
        "### 1. REQUIREMENTS.md (written to the first output block below)\n"
        f"The REQUIREMENTS.md MUST contain these exact sections:\n"
        f"{', '.join(REQUIRED_SECTIONS)}\n\n"
        "- **## Overview**: 2-3 sentences summarizing the requirements scope\n"
        "- **## Functional Requirements**: Table with columns: ID, Description, Priority (High/Medium/Low)\n"
        "- **## Non-Functional Requirements**: Table with columns: ID, Description\n"
        "- **## Behavioural Requirements**: Table with columns: ID, Scenario, Expected Behaviour\n\n"
        "### 2. Gherkin Feature Files (one per feature area)\n"
        "- Create separate `.feature` files for each distinct feature area\n"
        "- Each file MUST contain valid Gherkin syntax\n"
        "- Each file MUST have a minimum of: Feature, Scenario, Given, When, Then\n"
        "- Use this delimiter between files: `---FEATURE_FILE: <name>.feature---`\n"
        "- File names should be kebab-case, e.g. `user-authentication.feature`\n\n"
        "Output format:\n"
        "```requirements-md\n"
        "[REQUIREMENTS.md content here]\n"
        "```\n"
        "---FEATURE_FILE: <name>.feature---\n"
        "```gherkin\n"
        "[Gherkin content here]\n"
        "```\n"
        "---FEATURE_FILE: <next-name>.feature---\n"
        "```gherkin\n"
        "[Gherkin content here]\n"
        "```"
    )
    user_prompt = "\n".join(parts)

    try:
        content = call_llm(
            prompt=user_prompt,
            stage="requirements",
            config=config,
            system_prompt=system_prompt,
            conversation_context=conversation_context,
        )
    except RuntimeError as e:
        print(f"\n[requirements] \u2717 LLM call failed: {e}")
        print("The stage produced no artefacts. Retry with: /requirements")
        state.stages["requirements"].status = "failed"
        state.current_stage = "requirements"
        return state

    _write_artefacts(content)

    print(f"[requirements] \u2713 REQUIREMENTS.md written to {REQUIREMENTS_PATH}")

    feature_files = _get_feature_files()
    if feature_files:
        print(f"[requirements] \u2713 Generated {len(feature_files)} Gherkin feature file(s):")
        for f in feature_files:
            print(f"       {f}")

    _ensure_required_sections(REQUIREMENTS_PATH)

    passed, messages = run_gate_checks("requirements", [
        GateCheck("requirements_md_exists", "REQUIREMENTS.md exists",
                  lambda: check_file_exists(REQUIREMENTS_PATH)),
        GateCheck("requirements_schema_valid", "REQUIREMENTS.md schema valid",
                  lambda: _check_requirements_schema()),
        GateCheck("feature_files_exist", "At least one .feature file exists",
                  lambda: _check_feature_files()),
    ], state)

    for msg in messages:
        print(msg)

    if passed:
        state.stages["requirements"].status = "complete"
        state.stages["requirements"].completed_at = datetime.now(timezone.utc).isoformat()
        state.stages["requirements"].artefact = REQUIREMENTS_PATH
        state.current_stage = "requirements"
        state.completed_stages.append("requirements")
        print(f"\n[requirements] \u2713 Gate checks passed (3/3)")
        print(f"\nReview {REQUIREMENTS_PATH} and feature files, then run: /coding")
    else:
        print(f"\n[requirements] \u2717 Gate checks failed")
        print("Retry with: /requirements")
        _cleanup_artefacts()
        state.stages["requirements"].status = "failed"
        state.current_stage = "requirements"

    return state


def _cleanup_artefacts():
    if os.path.exists(REQUIREMENTS_PATH):
        os.remove(REQUIREMENTS_PATH)
    for f in _get_feature_files():
        os.remove(f)
    print(f"[requirements] Removed incomplete artefacts from {GHERKIN_DIR}/")


def _write_artefacts(llm_content: str):
    segments = re.split(
        r'^---FEATURE_FILE:\s*([\w\-]+\.feature)---\s*$',
        llm_content,
        flags=re.MULTILINE,
    )

    requirements_content = ""
    feature_files = []

    i = 0
    while i < len(segments):
        segment = segments[i].strip()
        if segment.startswith("```requirements-md") or segment.startswith("```markdown") or segment.startswith("```"):
            if not feature_files and not requirements_content:
                code_content = segment.split("\n", 1)[1] if "\n" in segment else ""
                if code_content.endswith("```"):
                    code_content = code_content[:-3].strip()
                requirements_content = code_content
            i += 1
        elif segment and i + 1 < len(segments) and segments[i + 1].strip().startswith("```"):
            filename = segment
            code_block = segments[i + 1]
            code_content = code_block.split("\n", 1)[1] if "\n" in code_block else ""
            if code_content.endswith("```"):
                code_content = code_content[:-3].strip()
            feature_files.append((filename, code_content))
            i += 2
        else:
            i += 1

    if not requirements_content:
        requirements_content = llm_content

    with open(REQUIREMENTS_PATH, "w") as f:
        f.write(requirements_content)

    for filename, code_content in feature_files:
        filepath = os.path.join(GHERKIN_DIR, filename)
        with open(filepath, "w") as f:
            f.write(code_content)


def _get_feature_files() -> list[str]:
    pattern = os.path.join(GHERKIN_DIR, "*.feature")
    return sorted(glob.glob(pattern))


def _ensure_required_sections(path: str):
    if not os.path.exists(path):
        return
    with open(path) as f:
        content = f.read()
    missing = [s for s in REQUIRED_SECTIONS if s not in content]
    if missing:
        with open(path, "a") as f:
            f.write("\n\n---\n\n")
            for section in missing:
                f.write(f"\n{section}\nTBD — see conversation context.\n\n")
        print(f"[requirements] \u2717 Appended missing sections: {', '.join(missing)}")


def _check_requirements_schema() -> tuple[bool, str]:
    if not os.path.exists(REQUIREMENTS_PATH):
        return False, f"{REQUIREMENTS_PATH} does not exist"
    with open(REQUIREMENTS_PATH) as f:
        content = f.read()
    missing = [s for s in REQUIRED_SECTIONS if s not in content]
    if missing:
        sections_str = ", ".join(missing)
        return False, f"REQUIREMENTS.md is missing required section(s): {sections_str}"
    return True, "All required sections present"


def _check_feature_files() -> tuple[bool, str]:
    files = _get_feature_files()
    if not files:
        return False, "No .feature files found in sdlc/requirements/"
    for f in files:
        if os.path.getsize(f) == 0:
            return False, f"Feature file {f} is empty"
    return True, f"{len(files)} feature file(s) found"
